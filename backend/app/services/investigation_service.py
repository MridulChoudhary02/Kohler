"""
backend/app/services/investigation_service.py — AI Incident Investigator Service.

Implements autonomous LLM-driven root cause and impact investigation for anomaly tickets:
1. Assembles a deterministic, strictly bounded evidence object:
   - ticket, detection_event, fixture, zone, baseline_profile, and the last ~20 telemetry readings.
2. Invokes LLM (Groq / litellm) under strict constraints:
   - Must not invent any numeric sensor value not present in the evidence object.
   - Must not alter or dispute the dispatched detection outcome.
   - Validates response strictly against Pydantic schema with retry on invalid JSON/free text.
   - Preserves read-only integrity: tickets and database state are never modified.
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Dict, List, Tuple
import litellm
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.core.config import settings
from app.models.models import Ticket, DetectionEvent, Fixture, Zone, BaselineProfile, Sensor, TelemetryReading
from detection.sensor_health import SensorHealthTracker

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Pydantic Schemas for Strict Validation
# ─────────────────────────────────────────────────────────────

class InvestigationReport(BaseModel):
    summary: str = Field(..., description="Concise plain-English incident synthesis for facility operations")
    likely_cause: str = Field(..., description="Mechanical, hydraulic, or operational root cause")
    evidence: List[str] = Field(..., description="List of factual bullet points citing specific measurements from evidence")
    recommended_actions: List[str] = Field(..., description="Actionable maintenance steps for technicians")
    impact: str = Field(..., description="Operational, financial, water loss, or clinical infection impact")
    risk_note: str = Field(..., description="Safety or compliance risk alert")


class InvestigationResponse(BaseModel):
    ticket_id: str
    evidence: Dict[str, Any]
    investigation: Optional[InvestigationReport] = None
    error: Optional[str] = None


def resolve_detection_rule_name(event_type: str, sub_type: Optional[str] = None) -> str:
    """Map event type and sub_type to human-readable rule label."""
    if sub_type in ("gradual_leak", "gradual_leak_trend"):
        return "Trend regression (gradual leak)"
    if sub_type == "stuck_valve":
        return "Post-flush persistence (stuck valve)"
    if sub_type == "sudden_leak":
        return "EWMA/UCL sustained breach"
    if sub_type == "sensor_flatline":
        return "Sensor diagnostic flatline"
    if sub_type == "sensor_dropout":
        return "Sensor telemetry packet dropout"
    if event_type == "leak":
        return "EWMA/UCL sustained breach"
    if event_type == "hygiene":
        return "Predictive hygiene stagnation threshold"
    if event_type == "sensor_fault":
        return "Sensor reliability index breach"
    return "Statistical threshold breach"


# ─────────────────────────────────────────────────────────────
# Step 1: Assemble Deterministic Evidence Object
# ─────────────────────────────────────────────────────────────

async def assemble_ticket_evidence(ticket_id: str, db: AsyncSession) -> Dict[str, Any]:
    """
    Query database for ticket, event, fixture, zone, baseline, and ~20 telemetry readings.
    Returns a deterministic, serializable evidence dictionary.
    """
    # 1. Fetch Ticket
    stmt = select(Ticket).where(Ticket.ticket_id == ticket_id)
    res = await db.execute(stmt)
    ticket = res.scalars().first()
    if not ticket:
        raise ValueError(f"Ticket '{ticket_id}' not found")

    # 2. Fetch DetectionEvent
    ev_stmt = select(DetectionEvent).where(DetectionEvent.event_id == ticket.event_id)
    ev_res = await db.execute(ev_stmt)
    event = ev_res.scalars().first()
    if not event:
        raise ValueError(f"Detection event for ticket '{ticket_id}' not found")

    now_utc = datetime.now(timezone.utc)
    ev_dt = event.detected_at if event.detected_at.tzinfo else event.detected_at.replace(tzinfo=timezone.utc)
    end_dt = ticket.resolved_at or now_utc
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)
    dur_s = round(max(0.0, (end_dt - ev_dt).total_seconds()), 1)
    detection_rule = resolve_detection_rule_name(event.event_type, event.sub_type)

    # 3. Fetch Fixture & Zone
    fz_stmt = (
        select(Fixture, Zone)
        .join(Zone, Fixture.zone_id == Zone.zone_id)
        .where(Fixture.fixture_id == event.fixture_id)
    )
    fz_res = await db.execute(fz_stmt)
    fz_row = fz_res.first()
    fixture, zone = fz_row if fz_row else (None, None)

    tier = zone.criticality_tier if zone else "Tier 1"
    window_min = settings.confirmation_windows.get(tier, 5)
    confirmation_window_seconds = int(window_min * 60)

    # 4. Fetch BaselineProfile
    bp_stmt = select(BaselineProfile).where(BaselineProfile.fixture_id == event.fixture_id)
    bp_res = await db.execute(bp_stmt)
    bp = bp_res.scalars().first()

    mean_off_flow = round(float(bp.mean_off_flow), 4) if bp else 0.008
    std_off_flow = round(float(bp.std_off_flow), 4) if bp else 0.012
    ucl = round(mean_off_flow + 3.0 * std_off_flow, 4)

    # 5. Sensor & Health Score
    sensor_stmt = select(Sensor.sensor_id).where(Sensor.fixture_id == event.fixture_id)
    sensor_res = await db.execute(sensor_stmt)
    sensor_id = sensor_res.scalar_one_or_none()

    sensor_health_score = 1.0
    if sensor_id:
        tracker = SensorHealthTracker(sensor_id=sensor_id, fixture_id=event.fixture_id, zone_tier=tier)
        readings_stmt = (
            select(
                TelemetryReading.timestamp,
                TelemetryReading.flow_rate_lpm,
                TelemetryReading.occupancy_state,
                TelemetryReading.diagnostic_status,
            )
            .where(TelemetryReading.sensor_id == sensor_id)
            .order_by(TelemetryReading.timestamp.desc())
            .limit(120)
        )
        recent_health_readings = (await db.execute(readings_stmt)).fetchall()
        for r in reversed(recent_health_readings):
            sensor_health_score, _ = tracker.process_reading({
                "timestamp": r[0],
                "flow_rate_lpm": r[1],
                "occupancy_state": r[2],
                "diagnostic_status": r[3],
            })
        sensor_health_score = round(sensor_health_score, 4)

    # 6. Last flush timestamp before detected_at
    last_flush_at = None
    if sensor_id:
        flush_stmt = (
            select(func.max(TelemetryReading.timestamp))
            .where(
                TelemetryReading.sensor_id == sensor_id,
                TelemetryReading.flush_event == 1,
                TelemetryReading.timestamp <= ev_dt,
            )
        )
        last_flush_at_val = (await db.execute(flush_stmt)).scalar()
        if last_flush_at_val:
            last_flush_at = last_flush_at_val.isoformat()

    # 7. Cost estimation per day (INR)
    ev_val = float(event.evidence_value or 0.0)
    estimated_cost_inr_per_day = round(ev_val * 24.0 * settings.WATER_COST_INR_PER_LITRE, 2)

    # 8. Fetch last ~20 telemetry readings around detected_at
    telemetry_list = []
    if sensor_id:
        t_stmt = (
            select(TelemetryReading)
            .where(
                TelemetryReading.sensor_id == sensor_id,
                TelemetryReading.timestamp >= ev_dt - timedelta(minutes=15),
                TelemetryReading.timestamp <= ev_dt + timedelta(minutes=5),
            )
            .order_by(TelemetryReading.timestamp.asc())
            .limit(25)
        )
        t_rows = (await db.execute(t_stmt)).scalars().all()
        if len(t_rows) < 5:
            # Fallback to nearest 20 readings around detected_at
            t_fallback_stmt = (
                select(TelemetryReading)
                .where(TelemetryReading.sensor_id == sensor_id)
                .order_by(func.abs(func.extract("epoch", TelemetryReading.timestamp) - ev_dt.timestamp()))
                .limit(20)
            )
            t_rows = sorted((await db.execute(t_fallback_stmt)).scalars().all(), key=lambda r: r.timestamp)

        for tr in t_rows[:20]:
            telemetry_list.append({
                "timestamp": tr.timestamp.isoformat() if tr.timestamp else None,
                "flow_rate_lpm": round(float(tr.flow_rate_lpm), 4),
                "occupancy_state": int(tr.occupancy_state),
                "flush_event": int(tr.flush_event),
                "sensor_id": str(tr.sensor_id),
            })

    evidence_object: Dict[str, Any] = {
        "ticket": {
            "ticket_id": ticket.ticket_id,
            "status": ticket.status,
            "priority_score": round(float(ticket.priority_score), 2),
            "created_at": ev_dt.isoformat(),
            "started_at": ticket.started_at.isoformat() if ticket.started_at else None,
            "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
            "is_escalated": bool(ticket.is_escalated),
            "anomaly_duration_seconds": dur_s,
        },
        "detection_event": {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "sub_type": event.sub_type,
            "detection_rule": detection_rule,
            "confidence_score": round(float(event.confidence_score), 4),
            "evidence_value": round(ev_val, 4),
            "detected_at": ev_dt.isoformat(),
            "status": event.status,
            "anomaly_duration_seconds": dur_s,
        },
        "fixture": {
            "fixture_id": fixture.fixture_id if fixture else event.fixture_id,
            "fixture_type": fixture.fixture_type if fixture else "unknown",
            "zone_id": fixture.zone_id if fixture else (zone.zone_id if zone else "unknown"),
        },
        "zone": {
            "zone_id": zone.zone_id if zone else "unknown",
            "name": zone.name if zone else "Unknown Zone",
            "criticality_tier": tier,
        },
        "baseline_profile": {
            "mean_off_flow": mean_off_flow,
            "std_off_flow": std_off_flow,
            "ucl": ucl,
            "mean_flush_volume": round(float(bp.mean_flush_volume), 2) if bp else 6.0,
            "mean_flush_duration_s": round(float(bp.mean_flush_duration_s), 2) if bp else 10.0,
            "warmup_complete": bool(bp.warmup_complete) if bp else False,
            "sensor_health_score": sensor_health_score,
            "confirmation_window_seconds": confirmation_window_seconds,
            "last_flush_at": last_flush_at,
            "estimated_cost_inr_per_day": estimated_cost_inr_per_day,
        },
        "telemetry_readings": telemetry_list,
    }

    return evidence_object


# ─────────────────────────────────────────────────────────────
# Step 2: Strict LLM Investigation Call with Validation & Retry
# ─────────────────────────────────────────────────────────────

INVESTIGATOR_SYSTEM_PROMPT = """You are an expert hospital facilities diagnostic assistant and water anomaly investigator.
You are investigating a water fixture anomaly detection ticket.

CRITICAL CONSTRAINTS:
1. Ground truth constraint: The only context available to you is the provided Evidence Object. You MUST NOT invent, assume, or hallucinate any numeric sensor value, flow rate, timestamp, health score, cost, or threshold not present in the Evidence Object.
2. Outcome constraint: You MUST NOT suggest, dispute, or imply a different detection outcome, status, or severity than what has already been dispatched by the detection engine. Accept the dispatched detection event and rule as confirmed facts.
3. Numeric fidelity in evidence: Every number you cite in the 'evidence' array MUST match an exact number present in the Evidence Object (such as flow rates, UCL, evidence value, confidence score, duration, confirmation window, cost). Do NOT approximate, extrapolate, or fabricate numbers.
4. Output format: You MUST return a single valid JSON object with EXACTLY the following keys:
   - "summary": string (concise plain-English incident synthesis for facility operations)
   - "likely_cause": string (mechanical, hydraulic, or operational reason, e.g. diaphragm tear, debris under seal, stuck solenoid, gradual valve seat wear)
   - "evidence": array of strings (e.g. ["Evidence value: 46.37 L/hr", "UCL threshold: 0.07 LPM", "Confidence score: 0.95", "Priority score: 92.71"]). It MUST be a flat list of strings, NOT an object.
   - "recommended_actions": array of strings (actionable steps for maintenance technicians)
   - "impact": string (operational, water loss, financial, or clinical infection control impact)
   - "risk_note": string (safety or compliance warning, e.g. cross-contamination, scald risk, clinical zone priority)

Respond with ONLY the raw JSON object. Do not wrap in markdown code fences or backticks.
"""


def clean_json_string(raw: str) -> str:
    """Strip markdown fences or stray whitespace."""
    s = raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s)
    if match:
        return match.group(1).strip()
    return s


def parse_and_validate_investigation(raw_text: str) -> InvestigationReport:
    """Parse JSON and validate against InvestigationReport schema."""
    cleaned = clean_json_string(raw_text)
    parsed = json.loads(cleaned)

    # Defensively normalize evidence or recommended_actions if model nested them
    if isinstance(parsed.get("evidence"), dict):
        flattened = []
        for k, v in parsed["evidence"].items():
            if isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    flattened.append(f"{sub_k}: {sub_v}")
            else:
                flattened.append(f"{k}: {v}")
        parsed["evidence"] = flattened

    if isinstance(parsed.get("recommended_actions"), str):
        parsed["recommended_actions"] = [parsed["recommended_actions"]]

    return InvestigationReport(**parsed)


async def run_incident_investigation(evidence: Dict[str, Any]) -> Tuple[Optional[InvestigationReport], Optional[str]]:
    """
    Run LLM investigation with litellm using the deterministic evidence object as the ONLY input.
    Validates schema server-side; retries once on error; fails gracefully with a structured error.
    """
    api_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
    if not api_key and settings.LLM_PROVIDER == "openai":
        api_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")

    if not api_key:
        return None, "LLM API key not configured"

    if settings.GROQ_API_KEY:
        os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY

    model_name = settings.LLM_MODEL
    if settings.LLM_PROVIDER and not model_name.startswith(f"{settings.LLM_PROVIDER}/"):
        model_name = f"{settings.LLM_PROVIDER}/{settings.LLM_MODEL}"

    user_prompt = f"Evidence Object:\n{json.dumps(evidence, indent=2)}\n\nInvestigate this ticket based strictly on the Evidence Object."

    messages = [
        {"role": "system", "content": INVESTIGATOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    # First attempt
    try:
        resp = litellm.completion(
            model=model_name,
            messages=messages,
            temperature=0.1,
            max_tokens=1500,
        )
        content = resp.choices[0].message.content or ""
        report = parse_and_validate_investigation(content)
        return report, None
    except Exception as first_err:
        logger.warning(f"First LLM investigation attempt failed ({first_err}); retrying once...")
        # Attempt 2: retry with explicit error guidance
        try:
            retry_messages = messages + [
                {"role": "assistant", "content": content if "content" in locals() else ""},
                {
                    "role": "user",
                    "content": (
                        f"The previous output was invalid: {first_err}. "
                        f"Please output ONLY a raw JSON object with keys: summary, likely_cause, evidence (list of strings), "
                        f"recommended_actions (list of strings), impact, risk_note. Do not use code blocks."
                    ),
                },
            ]
            retry_resp = litellm.completion(
                model=model_name,
                messages=retry_messages,
                temperature=0.1,
                max_tokens=1500,
            )
            retry_content = retry_resp.choices[0].message.content or ""
            report = parse_and_validate_investigation(retry_content)
            return report, None
        except Exception as retry_err:
            logger.error(f"Second LLM investigation attempt failed: {retry_err}")
            return None, f"Investigation validation failed: {retry_err}"
