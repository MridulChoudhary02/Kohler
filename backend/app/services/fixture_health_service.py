"""
backend/app/services/fixture_health_service.py — Predictive Fixture Health Service.

Calculates live transparent health and failure-risk scores per fixture:
    risk = (frequency_score * 0.30)
         + (recurrence_score * 0.20)
         + (flow_drift_score * 0.20)
         + (slow_leak_score * 0.15)
         + (sensor_health_risk * 0.10)
         + (unresolved_score * 0.05)

    health_score = max(0.0, min(100.0, 100.0 - risk))

Grounding & Denominators:
- frequency_score denominator: 12.0 (based on observed active fixture mean=6.47, median=4.00, chronic outliers > 12)
- recurrence_score denominator: 8.0 (based on observed inter-event spacing <=24h: mean=5.06, median=3.00)
- flow_drift_score: Evaluates idle flow readings (last 24h) against the active segment baseline:
    - On context-adaptive fixtures (fix-ot-001/002/003, fix-lab-001), compared against time-appropriate Day/Night mean.
    - On standard fixtures, compared against combined mean_idle_flow.
- slow_leak_score: Penalizes gradual_leak / gradual_leak_warning sub_types (50 pts each).
- sensor_health_risk: Penalizes sensor_fault events (sensor_flatline, sensor_dropout, sensor_maintenance) (50 pts each).
- unresolved_score: Penalizes active open / acknowledged / in_progress tickets (50 pts each).
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models.models import (
    Fixture,
    Zone,
    DetectionEvent,
    Ticket,
    Sensor,
    TelemetryReading,
)
from detection.baseline import BaselineProfile, load_baselines

# Frequency and recurrence denominators grounded in real telemetry distribution (clean single-pass telemetry)
FREQ_DENOMINATOR = 8.0
REC_DENOMINATOR = 6.0
FLOW_DRIFT_MAX_LPM = 0.30

# Path to canonical prewarm baseline profiles
BASELINES_PATH = Path(__file__).resolve().parents[2] / "simulator" / "output" / "prewarm" / "baseline_profiles.json"
_cached_profiles: Optional[Dict[str, BaselineProfile]] = None


def get_baseline_profiles() -> Dict[str, BaselineProfile]:
    global _cached_profiles
    if _cached_profiles is None:
        if BASELINES_PATH.exists():
            _cached_profiles = load_baselines(BASELINES_PATH)
        else:
            _cached_profiles = {}
    return _cached_profiles


def generate_recommendation(
    status_lbl: str,
    active_tickets: int,
    slow_leak_score: float,
    has_stuck_valve: bool,
    sensor_fault_count: int,
    drift_score: float,
) -> str:
    """Generate deterministic, plain-English operational guidance tiered by health_status."""
    # 1. High Risk fixtures: immediate priority action
    if status_lbl == "high_risk":
        if active_tickets > 0 and slow_leak_score > 0:
            return "Priority inspection required — gradual leak trend detected with active unaddressed ticket."
        if has_stuck_valve:
            return "Priority inspection required — inspect flush valve return spring/piston (stuck valve persistence detected)."
        if active_tickets > 0:
            return "Priority maintenance required — resolve active open leak incident."
        if drift_score >= 50.0:
            return "Priority maintenance required — inspect internal diaphragm seal (severe idle flow drift)."
        return "Priority maintenance required — chronic failure pattern detected."

    # 2. Degrading fixtures: urgent investigation before further degradation
    if status_lbl == "degrading":
        if slow_leak_score > 0:
            return "Priority inspection required — gradual leak trend detected."
        if has_stuck_valve:
            return "Priority inspection required — inspect flush valve mechanism."
        if active_tickets > 0:
            return "Priority maintenance required — open incident requires investigation before further degradation."
        if sensor_fault_count > 0:
            return "Priority sensor inspection — sensor diagnostic faults logged."
        if drift_score >= 50.0:
            return "Priority maintenance required — elevated idle flow drift detected."
        return "Schedule preventive inspection during next maintenance round."

    # 3. Watch fixtures: proactive monitoring and routine check
    if status_lbl == "watch":
        if sensor_fault_count > 0:
            return "Sensor health maintenance recommended — inspect sensor wiring and calibration."
        if active_tickets > 0:
            plural = "s" if active_tickets != 1 else ""
            return f"Monitor fixture closely — {active_tickets} ticket{plural} pending review during next routine round."
        if drift_score >= 20.0:
            return "Monitor flow trend — minor drift detected, check during next maintenance round."
        return "Schedule preventive inspection during next maintenance round."

    # 4. Healthy fixtures: standard operations, never alarm language
    if active_tickets > 0:
        plural = "s" if active_tickets != 1 else ""
        return f"Operating normally — {active_tickets} minor ticket{plural} pending closure."
    if sensor_fault_count > 0:
        return "Operating normally — minor sensor diagnostic check recommended during standard servicing."
    return "Normal operational status — maintain standard maintenance cycle."


async def compute_all_fixture_health(
    db: AsyncSession,
    zone_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    sort_by: str = "risk_desc",
) -> Dict[str, Any]:
    """Compute live health and risk scores for all fixtures."""
    profiles = get_baseline_profiles()

    # Determine reference max timestamp in telemetry/events
    res_t = await db.execute(select(func.max(DetectionEvent.detected_at)))
    max_dt = res_t.scalar() or datetime.now(timezone.utc)
    if max_dt.tzinfo is None:
        max_dt = max_dt.replace(tzinfo=timezone.utc)

    t_24h = max_dt - timedelta(hours=24)
    t_72h = max_dt - timedelta(hours=72)

    # Fetch fixtures with zone info
    f_stmt = (
        select(Fixture.fixture_id, Fixture.fixture_type, Zone.zone_id, Zone.criticality_tier)
        .join(Zone, Fixture.zone_id == Zone.zone_id)
    )
    if zone_id:
        f_stmt = f_stmt.where(Zone.zone_id == zone_id)

    fixtures = (await db.execute(f_stmt)).fetchall()

    items = []
    high_risk_count = 0
    degrading_count = 0
    watch_count = 0
    healthy_count = 0

    for fid, ftype, zid, tier in fixtures:
        # 1. Fetch all detection events for this fixture
        ev_stmt = (
            select(
                DetectionEvent.event_id,
                DetectionEvent.event_type,
                DetectionEvent.sub_type,
                DetectionEvent.detected_at,
                DetectionEvent.status,
            )
            .where(DetectionEvent.fixture_id == fid)
            .order_by(DetectionEvent.detected_at.asc())
        )
        evs = (await db.execute(ev_stmt)).fetchall()
        dispatched_evs = [e for e in evs if e[4] == "dispatched"]

        n_dispatched = len(dispatched_evs)
        freq_score = min(100.0, (n_dispatched / FREQ_DENOMINATOR) * 100.0)

        # 2. Recurrence: dispatched events within <= 24h of prior dispatched event
        recs = 0
        for i in range(1, len(dispatched_evs)):
            diff_h = (dispatched_evs[i][3] - dispatched_evs[i - 1][3]).total_seconds() / 3600.0
            if diff_h <= 24.0:
                recs += 1
        rec_score = min(100.0, (recs / REC_DENOMINATOR) * 100.0)

        # 3. Specific anomaly category counts
        gradual_cnt = sum(
            1 for e in evs if e[2] in ("gradual_leak", "gradual_leak_warning") or e[1] == "gradual_leak_warning"
        )
        slow_leak_score = min(100.0, gradual_cnt * 50.0)

        sensor_fault_cnt = sum(1 for e in evs if e[1] == "sensor_fault")
        sensor_score = min(100.0, sensor_fault_cnt * 50.0)

        has_stuck_valve = any(e[2] == "stuck_valve" for e in evs)
        leak_cnt = sum(1 for e in evs if e[1] in ("leak", "gradual_leak_warning"))
        hygiene_cnt = sum(1 for e in evs if e[1] == "hygiene")

        # 4. Unresolved tickets
        tkt_stmt = (
            select(func.count(Ticket.ticket_id))
            .join(DetectionEvent, Ticket.event_id == DetectionEvent.event_id)
            .where(DetectionEvent.fixture_id == fid, Ticket.status.in_(["open", "acknowledged", "in_progress"]))
        )
        open_cnt = (await db.execute(tkt_stmt)).scalar() or 0
        unresolved_score = min(100.0, open_cnt * 50.0)

        # 5. Flow drift: evaluate non-flush idle readings in the last 24h against active segment baseline
        drift_score = 0.0
        bp = profiles.get(fid)
        s_stmt = select(Sensor.sensor_id).where(Sensor.fixture_id == fid)
        sid = (await db.execute(s_stmt)).scalar()
        if sid and bp:
            r_stmt = (
                select(TelemetryReading.flow_rate_lpm, TelemetryReading.timestamp)
                .where(
                    TelemetryReading.sensor_id == sid,
                    TelemetryReading.occupancy_state == 0,
                    TelemetryReading.flush_event == 0,
                    TelemetryReading.timestamp >= t_24h,
                )
            )
            readings = (await db.execute(r_stmt)).fetchall()
            if readings:
                diffs = []
                for flow, ts in readings:
                    exp_mean, _, _, _, _ = bp.get_active_baseline(ts)
                    diffs.append(flow - exp_mean)
                avg_drift = max(0.0, sum(diffs) / len(diffs))
                drift_score = min(100.0, (avg_drift / FLOW_DRIFT_MAX_LPM) * 100.0)

        # 6. Weighted Risk & Health Calculation
        risk = (
            freq_score * 0.30
            + rec_score * 0.20
            + drift_score * 0.20
            + slow_leak_score * 0.15
            + sensor_score * 0.10
            + unresolved_score * 0.05
        )
        health = max(0.0, min(100.0, 100.0 - risk))

        # Status categorization
        if health < 40.0:
            status_lbl = "high_risk"
            high_risk_count += 1
        elif health < 60.0:
            status_lbl = "degrading"
            degrading_count += 1
        elif health < 80.0:
            status_lbl = "watch"
            watch_count += 1
        else:
            status_lbl = "healthy"
            healthy_count += 1

        # 7. Trend: Recent 24h vs. older 48h (normalized to per-24h rate)
        recent_evs = sum(1 for e in dispatched_evs if e[3] >= t_24h)
        older_evs = sum(1 for e in dispatched_evs if t_72h <= e[3] < t_24h)
        older_rate = older_evs / 2.0
        trend = "stable"
        if recent_evs >= older_rate + 1.0:
            trend = "deteriorating"
        elif recent_evs <= older_rate - 1.0 and open_cnt == 0:
            trend = "improving"

        # Timestamps
        last_incident = max([e[3] for e in evs]) if evs else None
        res_stmt = (
            select(func.max(Ticket.resolved_at))
            .join(DetectionEvent, Ticket.event_id == DetectionEvent.event_id)
            .where(DetectionEvent.fixture_id == fid)
        )
        last_resolved = (await db.execute(res_stmt)).scalar()

        rec_text = generate_recommendation(
            status_lbl=status_lbl,
            active_tickets=open_cnt,
            slow_leak_score=slow_leak_score,
            has_stuck_valve=has_stuck_valve,
            sensor_fault_count=sensor_fault_cnt,
            drift_score=drift_score,
        )

        item = {
            "fixture_id": fid,
            "fixture_type": ftype,
            "zone_id": zid,
            "zone_tier": tier,
            "health_score": round(health, 1),
            "risk_score": round(risk, 1),
            "health_status": status_lbl,
            "trend": trend,
            "total_incidents": len(evs),
            "active_tickets_count": open_cnt,
            "leak_incidents_count": leak_cnt,
            "sensor_faults_count": sensor_fault_cnt,
            "hygiene_incidents_count": hygiene_cnt,
            "sub_scores": {
                "frequency_score": round(freq_score, 1),
                "recurrence_score": round(rec_score, 1),
                "flow_drift_score": round(drift_score, 1),
                "slow_leak_score": round(slow_leak_score, 1),
                "sensor_health_score": round(sensor_score, 1),
                "unresolved_score": round(unresolved_score, 1),
            },
            "last_incident_at": last_incident,
            "last_resolved_at": last_resolved,
            "recommendation": rec_text,
        }
        items.append(item)

    # Filter by status if requested
    if status_filter:
        items = [it for it in items if it["health_status"] == status_filter]

    # Sorting
    if sort_by == "health_asc":
        items.sort(key=lambda x: x["health_score"])
    elif sort_by == "health_desc":
        items.sort(key=lambda x: x["health_score"], reverse=True)
    elif sort_by == "incidents_desc":
        items.sort(key=lambda x: x["total_incidents"], reverse=True)
    else:  # default: risk_desc
        items.sort(key=lambda x: x["risk_score"], reverse=True)

    avg_health = round(sum(it["health_score"] for it in items) / len(items), 1) if items else 100.0

    return {
        "facility_health_score": avg_health,
        "high_risk_count": high_risk_count,
        "degrading_count": degrading_count,
        "watch_count": watch_count,
        "healthy_count": healthy_count,
        "fixtures": items,
    }


async def get_fixture_health_detail(db: AsyncSession, fixture_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve detailed health diagnostic breakdown + recent incident history for a single fixture."""
    summary_resp = await compute_all_fixture_health(db)
    target_item = next((it for it in summary_resp["fixtures"] if it["fixture_id"] == fixture_id), None)
    if not target_item:
        return None

    # Fetch chronological incident history with ticket info
    hist_stmt = (
        select(
            DetectionEvent.event_id,
            DetectionEvent.event_type,
            DetectionEvent.sub_type,
            DetectionEvent.detected_at,
            DetectionEvent.confidence_score,
            DetectionEvent.evidence_value,
            Ticket.ticket_id,
            Ticket.status,
            Ticket.priority_score,
        )
        .outerjoin(Ticket, Ticket.event_id == DetectionEvent.event_id)
        .where(DetectionEvent.fixture_id == fixture_id)
        .order_by(DetectionEvent.detected_at.desc())
        .limit(20)
    )
    rows = (await db.execute(hist_stmt)).fetchall()

    from app.api.events import resolve_detection_rule

    incidents = []
    for eid, etype, stype, det_at, conf, ev_val, tid, tstatus, prio in rows:
        rule_name = resolve_detection_rule(etype, stype)
        incidents.append({
            "event_id": eid,
            "event_type": etype,
            "sub_type": stype,
            "rule_label": rule_name,
            "detected_at": det_at,
            "confidence_score": round(conf, 4),
            "evidence_value": round(ev_val, 2) if ev_val is not None else None,
            "ticket_id": tid,
            "ticket_status": tstatus,
            "priority_score": round(prio, 2) if prio is not None else None,
        })

    target_item["recent_incidents"] = incidents
    return target_item
