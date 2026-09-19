"""
backend/app/services/ticket_service.py — Ticket Priority Scoring & Dispatch Service.

Implements PRD Section 10 (Ticket Priority & Dispatch):
  priority_score = (zone_criticality_weight * 0.4)
                 + (confidence_score * 0.3)
                 + (normalized_estimated_waste * 0.2)
                 + (SLA_urgency_factor * 0.1)

Normalization & Urgency definitions:
- normalized_estimated_waste:
    - leak: min(1.0, max(0.0, evidence_value / 60.0)) (60 L/hr = 1.0 max waste rate)
    - predictive_hygiene: 1.0 - (evidence_value / 30.0) if <= 30 else 0.0 (0 mins = 1.0 max urgency)
    - sensor_fault: 1.0 - min(1.0, max(0.0, evidence_value)) (health_score 0.0 = 1.0 max fault)
- SLA_urgency_factor:
    - 1.0 - (response_minutes / 120.0) (15 min SLA = 0.875, 120 min SLA = 0.0)
- priority_score scale:
    - 0 to 100 integer/float (round(weighted_sum * 100.0, 2))
- Auto-escalation boost:
    - min(100.0, priority_score + 25.0) for overdue open tickets past sla_due
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.models import Ticket, DetectionEvent, Fixture, Zone, SLAPolicy

ZONE_CRITICALITY_WEIGHTS = {
    "Tier 1": 1.00,
    "Tier 2": 0.75,
    "Tier 3": 0.50,
    "Tier 4": 0.25,
}

ZONE_SLA_MINUTES = {
    "Tier 1": 15,
    "Tier 2": 30,
    "Tier 3": 60,
    "Tier 4": 120,
}

ZONE_TEAMS = {
    "Tier 1": "Critical Care Maintenance",
    "Tier 2": "Patient Care Support",
    "Tier 3": "Clinical Plumbing",
    "Tier 4": "General Facilities",
}


def normalize_estimated_waste(event_type: str, evidence_value: Optional[float]) -> float:
    """Map evidence_value across event types to a 0.0–1.0 urgency scale."""
    val = evidence_value if evidence_value is not None else 0.0

    if event_type == "leak":
        # 60 L/hr continuous flow represents max waste scale (1.0)
        return min(1.0, max(0.0, val / 60.0))
    elif event_type in ("hygiene", "predictive_hygiene"):
        # val is minutes_to_breach. 0 mins = 1.0 max urgency, 30 mins = 0.0
        if val <= 0:
            return 1.0
        return max(0.0, 1.0 - (val / 30.0))
    elif event_type == "sensor_fault":
        # val is sensor_health_score (or fault severity). 0.0 health = 1.0 max fault urgency
        return max(0.0, 1.0 - min(1.0, max(0.0, val)))
    else:
        return 0.5


def compute_sla_urgency_factor(response_minutes: int) -> float:
    """Measure operational tightness of zone SLA response window (15m=0.875, 120m=0.0)."""
    return max(0.0, 1.0 - (response_minutes / 120.0))


def compute_priority_score(
    zone_tier: str,
    confidence_score: float,
    evidence_value: Optional[float],
    event_type: str,
    response_minutes: int,
) -> float:
    """Compute priority score (0–100 scale) per PRD Section 10 formula."""
    w_crit = ZONE_CRITICALITY_WEIGHTS.get(zone_tier, 0.25)
    conf = max(0.0, min(1.0, confidence_score))
    norm_waste = normalize_estimated_waste(event_type, evidence_value)
    sla_factor = compute_sla_urgency_factor(response_minutes)

    weighted_sum = (
        0.4 * w_crit
        + 0.3 * conf
        + 0.2 * norm_waste
        + 0.1 * sla_factor
    )
    return round(weighted_sum * 100.0, 2)


async def create_ticket_from_event(
    event: DetectionEvent,
    db: AsyncSession,
) -> Optional[Ticket]:
    """
    Creates and returns a new Ticket for a dispatched DetectionEvent.
    Fetches fixture and zone info to compute priority_score and sla_due.
    """
    if event.status != "dispatched":
        return None

    # Fetch fixture and zone details
    stmt = (
        select(Fixture, Zone)
        .join(Zone, Fixture.zone_id == Zone.zone_id)
        .where(Fixture.fixture_id == event.fixture_id)
    )
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        fixture_obj = None
        zone_obj = None
        zone_id = "zone-default"
        zone_tier = "Tier 4"
    else:
        fixture_obj, zone_obj = row
        zone_id = zone_obj.zone_id
        zone_tier = zone_obj.criticality_tier

    response_minutes = ZONE_SLA_MINUTES.get(zone_tier, 120)
    assigned_team = ZONE_TEAMS.get(zone_tier, "General Facilities")

    score = compute_priority_score(
        zone_tier=zone_tier,
        confidence_score=event.confidence_score,
        evidence_value=event.evidence_value,
        event_type=event.event_type,
        response_minutes=response_minutes,
    )

    detected_at = event.detected_at
    if detected_at.tzinfo is None:
        detected_at = detected_at.replace(tzinfo=timezone.utc)
    sla_due = detected_at + timedelta(minutes=response_minutes)

    ticket = Ticket(
        event_id=event.event_id,
        zone_id=zone_id,
        priority_score=score,
        status="open",
        sla_due=sla_due,
        assigned_team=assigned_team,
    )

    # Generate LLM summary for the ticket (PRD Section 12a)
    try:
        from app.services.llm_service import summarize_incident, FALLBACK_SUMMARY
        summary = summarize_incident(ticket, event, fixture_obj, zone_obj)
        ticket.summary_text = summary if summary != FALLBACK_SUMMARY else None
    except Exception:
        ticket.summary_text = None

    return ticket


async def escalate_overdue_tickets(
    db: AsyncSession,
    now: Optional[datetime] = None,
) -> list[Ticket]:
    """
    Finds open tickets past their sla_due timestamp and boosts priority_score by +25.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    stmt = select(Ticket).where(
        Ticket.status == "open",
        Ticket.sla_due < now,
        Ticket.is_escalated == False,
    )
    res = await db.execute(stmt)
    overdue_tickets = res.scalars().all()

    escalated = []
    for ticket in overdue_tickets:
        # Boost priority score by 25 points, capped at 100.0, and mark as escalated
        ticket.priority_score = min(100.0, round(ticket.priority_score + 25.0, 2))
        ticket.is_escalated = True
        escalated.append(ticket)

    if escalated:
        await db.commit()

    return escalated
