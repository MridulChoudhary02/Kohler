"""
backend/app/services/llm_service.py — LLM Incident Summarization & Chat-over-data Service.

Implements PRD Section 12a (Incident Summarization) and Section 12b (Chat-over-data Query Interface):
  - Accepts deterministic fields from Ticket, DetectionEvent, Fixture, and Zone for summarization.
  - Answers natural language facility queries grounded in actual stored database statistics.
  - Calls litellm using LLM_PROVIDER/LLM_MODEL from config.
  - Handles missing API keys or service failures gracefully by returning fallback strings.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional
import litellm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models.models import Ticket, DetectionEvent, Fixture, Zone

logger = logging.getLogger(__name__)

FALLBACK_SUMMARY = "[LLM Summary Unavailable - API Key Missing or Service Error]"


def summarize_incident(
    ticket: Any,
    event: Any,
    fixture: Any,
    zone: Any,
) -> str:
    """
    Generate a 1-paragraph plain English incident summary for a facility manager.

    Parameters:
      ticket: Ticket model instance or dict containing priority_score
      event: DetectionEvent model instance or dict containing event_type, confidence_score, evidence_value, detected_at
      fixture: Fixture model instance or dict containing fixture_type
      zone: Zone model instance or dict containing name, criticality_tier

    Returns:
      A single paragraph plain English string, or FALLBACK_SUMMARY on failure.
    """
    # Check for active API key based on provider
    api_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
    if not api_key and settings.LLM_PROVIDER == "openai":
        api_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")

    if not api_key:
        logger.warning("No LLM API key provided; returning fallback summary.")
        return FALLBACK_SUMMARY

    # Ensure environment variables match config for litellm
    if settings.GROQ_API_KEY:
        os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY

    # Safely extract attributes from objects or dicts
    def get_attr(obj: Any, key: str, default: Any = "N/A") -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    fixture_type = get_attr(fixture, "fixture_type", "Fixture")
    zone_name = get_attr(zone, "name", "Facility Zone")
    criticality_tier = get_attr(zone, "criticality_tier", "Tier 4")
    event_type = get_attr(event, "event_type", "anomaly")
    confidence_score = get_attr(event, "confidence_score", 0.0)
    evidence_value = get_attr(event, "evidence_value", 0.0)
    detected_at = get_attr(event, "detected_at", "recently")
    priority_score = get_attr(ticket, "priority_score", 0.0)

    # Format model name string for litellm
    if settings.LLM_PROVIDER and not settings.LLM_MODEL.startswith(f"{settings.LLM_PROVIDER}/"):
        model_name = f"{settings.LLM_PROVIDER}/{settings.LLM_MODEL}"
    else:
        model_name = settings.LLM_MODEL

    prompt = (
        f"System Context:\n"
        f"You are a facility operations assistant summarizing water anomaly detections for hospital maintenance teams.\n\n"
        f"Incident Data:\n"
        f"- Fixture Type: {fixture_type}\n"
        f"- Location Zone: {zone_name} ({criticality_tier})\n"
        f"- Event Type: {event_type}\n"
        f"- Detection Time: {detected_at}\n"
        f"- Detection Confidence: {confidence_score:.2f}\n"
        f"- Measured Evidence Value (e.g. flow rate / health score): {evidence_value}\n"
        f"- Priority Score: {priority_score:.1f}\n\n"
        f"Instructions:\n"
        f"Write a single concise paragraph in plain English tailored for a hospital facility manager. "
        f"Describe the anomaly, estimated operational impact (e.g. water waste or hygiene risk), and priority level based strictly on the data above. "
        f"Do not invent facts or mention data science technical terms like EWMA or UCL."
    )

    try:
        response = litellm.completion(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=350,
        )
        content = response.choices[0].message.content
        if content:
            return content.strip()
        return FALLBACK_SUMMARY
    except Exception as exc:
        logger.error(f"Error invoking LLM ({model_name}): {exc}")
        return FALLBACK_SUMMARY


async def answer_facility_query(query: str, db: AsyncSession) -> str:
    """
    Implements PRD Section 12b (Chat-over-data):
    Translates natural-language query into database lookups and returns a grounded answer.
    """
    # Fetch real state from DB
    tickets_res = await db.execute(select(Ticket))
    tickets = tickets_res.scalars().all()

    events_res = await db.execute(select(DetectionEvent))
    events = events_res.scalars().all()

    zones_res = await db.execute(select(Zone))
    zones = zones_res.scalars().all()

    fixtures_res = await db.execute(select(Fixture))
    fixtures = fixtures_res.scalars().all()

    # Aggregate key grounded metrics
    open_tickets = [t for t in tickets if t.status in ("open", "acknowledged", "in_progress")]
    resolved_tickets = [t for t in tickets if t.status == "resolved"]
    escalated_tickets = [t for t in tickets if t.is_escalated]

    active_leaks = [e for e in events if e.event_type == "leak" and e.status == "dispatched"]
    active_faults = [e for e in events if e.event_type == "sensor_fault"]
    active_hygiene = [e for e in events if e.event_type in ("hygiene", "predictive_hygiene")]

    total_leak_waste_rate = sum(e.evidence_value or 0.0 for e in active_leaks)

    # Per-zone active leak waste breakdown
    fixture_zone_map = {f.fixture_id: f.zone_id for f in fixtures}
    zone_name_map = {z.zone_id: f"{z.name} ({z.criticality_tier})" for z in zones}

    zone_waste_totals: dict[str, float] = {}
    for leak in active_leaks:
        zid = fixture_zone_map.get(leak.fixture_id, "unknown-zone")
        zname = zone_name_map.get(zid, zid)
        zone_waste_totals[zname] = zone_waste_totals.get(zname, 0.0) + (leak.evidence_value or 0.0)

    zone_waste_ranking = [
        f"{zname}: {waste:.2f} L/hr"
        for zname, waste in sorted(zone_waste_totals.items(), key=lambda x: x[1], reverse=True)
    ]

    top_tickets = sorted(open_tickets, key=lambda t: t.priority_score, reverse=True)[:5]
    top_tickets_summary = [
        f"Ticket #{t.ticket_id[:8]} (Zone: {t.zone_id}, Status: {t.status}, Priority Score: {t.priority_score}, Escalated: {t.is_escalated})"
        for t in top_tickets
    ]

    grounding_data = (
        f"Grounded Hospital Facility Statistics:\n"
        f"- Total Zones Monitored: {len(zones)}\n"
        f"- Total Fixtures Monitored: {len(fixtures)}\n"
        f"- Open/Active Maintenance Tickets: {len(open_tickets)}\n"
        f"- Escalated Overdue Tickets: {len(escalated_tickets)}\n"
        f"- Resolved Tickets: {len(resolved_tickets)}\n"
        f"- Active Leak Events: {len(active_leaks)} events, currently wasting {total_leak_waste_rate:.2f} L/hr continuous flow\n"
        f"- Per-Zone Estimated Water Waste Breakdown (Active Leaks): {'; '.join(zone_waste_ranking) if zone_waste_ranking else 'No active leaks'}\n"
        f"- Sensor Health Fault Events: {len(active_faults)}\n"
        f"- Hygiene Prediction Events: {len(active_hygiene)}\n"
        f"- Top Open Priority Tickets: {'; '.join(top_tickets_summary) if top_tickets_summary else 'None'}\n"
    )

    api_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
    if not api_key and settings.LLM_PROVIDER == "openai":
        api_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")

    if not api_key:
        return f"[Grounded Query Answer (Key Missing)]\n{grounding_data}"

    if settings.GROQ_API_KEY:
        os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY

    if settings.LLM_PROVIDER and not settings.LLM_MODEL.startswith(f"{settings.LLM_PROVIDER}/"):
        model_name = f"{settings.LLM_PROVIDER}/{settings.LLM_MODEL}"
    else:
        model_name = settings.LLM_MODEL

    prompt = (
        f"You are a hospital facility query assistant. Answer the user's question using strictly the grounded facility data below.\n\n"
        f"{grounding_data}\n"
        f"User Query: {query}\n\n"
        f"Instructions:\n"
        f"Provide a helpful, precise, plain English answer to the query based ONLY on the grounded data above. "
        f"Do not hallucinate facts or invent fixtures/zones not listed above."
    )

    try:
        response = litellm.completion(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300,
        )
        content = response.choices[0].message.content
        if content:
            return content.strip()
        return f"[Grounded Answer]\n{grounding_data}"
    except Exception as exc:
        logger.error(f"Error querying LLM ({model_name}): {exc}")
        return f"[Grounded Answer (Fallback)]\n{grounding_data}"
