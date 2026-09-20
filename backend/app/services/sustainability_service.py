"""
backend/app/services/sustainability_service.py — Water-Savings & Sustainability Impact Service

Track 2 Feature Specification (Section 2 — Adapted to Current Kohler Architecture):
1. Incident Projections:
   For active tickets (open, acknowledged, in_progress):
   projected_loss = observed_flow_lpm * horizon_minutes
   Horizons: +1hr (60m), +6hr (360m), +24hr (1440m), +7days (10080m)

2. Prevented Waste:
   For resolved tickets:
   estimated_water_saved = potential_loss_without_intervention - actual_loss_before_resolution
   Where:
     - reference_window_minutes = 360.0 (6 hours)
     - tickets missing valid resolved_at/detected_at timestamps (or where resolved_at <= detected_at)
       are strictly excluded from the estimated_water_saved sum (no assumed duration substituted).
     - potential_duration_minutes = max(reference_window_minutes, elapsed_minutes + reference_window_minutes) if elapsed_minutes >= reference_window_minutes else reference_window_minutes
     - potential_loss = observed_flow_lpm * potential_duration_minutes
     - actual_loss = observed_flow_lpm * elapsed_minutes
     - avoided_cost = estimated_water_saved * WATER_COST_INR_PER_LITRE

3. Facility-Level Aggregation:
   Summary of water waste, estimated water saved, cost impact, avoided cost,
   projected unresolved loss (+24h horizon sum), highest-waste fixture, highest-waste zone,
   top 5 highest-waste fixtures, and top zones.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import DetectionEvent, Fixture, Ticket, Zone

# Default reference window for prevented-waste calculation on resolved tickets (6 hours)
PREVENTED_WASTE_REF_WINDOW_HOURS: float = 6.0
PREVENTED_WASTE_REF_WINDOW_MINUTES: float = PREVENTED_WASTE_REF_WINDOW_HOURS * 60.0  # 360.0 minutes

# Active ticket statuses under projection
ACTIVE_TICKET_STATUSES = ("open", "acknowledged", "in_progress")


def compute_incident_projection(observed_flow_lpm: float) -> Dict[str, float]:
    """
    Project water loss at +1hr, +6hr, +24hr, and +7days using observed flow rate.
    Formula: projected_loss = observed_flow_lpm * horizon_minutes.
    Cost projection: projected_loss * settings.WATER_COST_INR_PER_LITRE.
    """
    tariff = getattr(settings, "WATER_COST_INR_PER_LITRE", 0.15)
    flow = max(0.0, float(observed_flow_lpm or 0.0))

    loss_1h = round(flow * 60.0, 2)
    loss_6h = round(flow * 360.0, 2)
    loss_24h = round(flow * 1440.0, 2)
    loss_7d = round(flow * 10080.0, 2)

    return {
        "observed_flow_lpm": round(flow, 4),
        "projected_loss_1h_liters": loss_1h,
        "projected_cost_1h_inr": round(loss_1h * tariff, 2),
        "projected_loss_6h_liters": loss_6h,
        "projected_cost_6h_inr": round(loss_6h * tariff, 2),
        "projected_loss_24h_liters": loss_24h,
        "projected_cost_24h_inr": round(loss_24h * tariff, 2),
        "projected_loss_7d_liters": loss_7d,
        "projected_cost_7d_inr": round(loss_7d * tariff, 2),
    }


def calculate_prevented_waste(
    observed_flow_lpm: float,
    elapsed_minutes: Optional[float],
    ref_window_minutes: float = PREVENTED_WASTE_REF_WINDOW_MINUTES,
) -> Optional[Dict[str, float]]:
    """
    Calculate estimated water saved and avoided cost for a resolved ticket.
    Strict Rule: If elapsed_minutes is None, negative, or zero, return None
    (ticket is excluded from estimated_water_saved sum — no assumed duration).
    """
    if elapsed_minutes is None or elapsed_minutes <= 0.0:
        return None

    tariff = getattr(settings, "WATER_COST_INR_PER_LITRE", 0.15)
    flow = max(0.0, float(observed_flow_lpm or 0.0))
    if flow <= 0.0:
        return {
            "observed_flow_lpm": 0.0,
            "elapsed_minutes": round(elapsed_minutes, 2),
            "actual_loss_liters": 0.0,
            "potential_loss_liters": 0.0,
            "estimated_water_saved_liters": 0.0,
            "avoided_cost_inr": 0.0,
            "cost_impact_inr": 0.0,
            "reference_window_minutes": ref_window_minutes,
        }

    actual_loss = round(flow * elapsed_minutes, 2)
    potential_loss = round(flow * ref_window_minutes, 2)
    estimated_water_saved = max(0.0, round(potential_loss - actual_loss, 2))
    avoided_cost = round(estimated_water_saved * tariff, 2)
    cost_impact = round(actual_loss * tariff, 2)

    return {
        "observed_flow_lpm": round(flow, 4),
        "elapsed_minutes": round(elapsed_minutes, 2),
        "actual_loss_liters": actual_loss,
        "potential_loss_liters": potential_loss,
        "estimated_water_saved_liters": estimated_water_saved,
        "avoided_cost_inr": avoided_cost,
        "cost_impact_inr": cost_impact,
        "reference_window_minutes": ref_window_minutes,
    }


def compute_ticket_elapsed_minutes(
    detected_at: Optional[datetime],
    resolved_at: Optional[datetime],
) -> Optional[float]:
    """
    Compute actual incident duration in minutes between detected_at and resolved_at.
    Strict rule: Returns None if either timestamp is missing or resolved_at <= detected_at.
    """
    if not detected_at or not resolved_at:
        return None

    dt_start = detected_at if detected_at.tzinfo else detected_at.replace(tzinfo=timezone.utc)
    dt_end = resolved_at if resolved_at.tzinfo else resolved_at.replace(tzinfo=timezone.utc)

    delta_seconds = (dt_end - dt_start).total_seconds()
    if delta_seconds <= 0.0:
        return None

    return delta_seconds / 60.0


async def compute_facility_sustainability_summary(
    db: AsyncSession,
    ref_window_minutes: float = PREVENTED_WASTE_REF_WINDOW_MINUTES,
) -> Dict[str, Any]:
    """
    Facility-level aggregate sustainability metrics:
    - water_waste_liters (reuses existing DB sum from events.py get_facility_metrics)
    - estimated_water_saved_liters (new prevented waste sum)
    - cost_impact (reuses existing tariff conversion)
    - avoided_cost (new avoided financial loss)
    - projected_unresolved_loss_liters (sum of open tickets' +24hr projections)
    - highest_waste_fixture
    - highest_waste_zone
    - top_waste_fixtures (top 5)
    - top_waste_zones
    - facility_projections (+1h, +6h, +24h, +7d sums across active tickets)
    """
    tariff = getattr(settings, "WATER_COST_INR_PER_LITRE", 0.15)

    # 1. Total water wasted (reusing existing calculation from events.py:821)
    stmt_waste = select(func.coalesce(func.sum(DetectionEvent.evidence_value), 0.0)).where(
        DetectionEvent.event_type == "leak"
    )
    total_water_wasted = float((await db.execute(stmt_waste)).scalar() or 0.0)
    cost_impact = round(total_water_wasted * tariff, 2)

    # 2. Incident projections for active tickets (open, acknowledged, in_progress)
    stmt_active = (
        select(Ticket, DetectionEvent)
        .join(DetectionEvent, Ticket.event_id == DetectionEvent.event_id)
        .where(Ticket.status.in_(ACTIVE_TICKET_STATUSES))
    )
    active_rows = (await db.execute(stmt_active)).all()

    proj_1h_total = 0.0
    proj_6h_total = 0.0
    proj_24h_total = 0.0
    proj_7d_total = 0.0
    active_leak_count = 0

    for ticket, ev in active_rows:
        if ev.event_type == "leak" and ev.evidence_value:
            active_leak_count += 1
            flow_lpm = float(ev.evidence_value) / 60.0
            proj = compute_incident_projection(flow_lpm)
            proj_1h_total += proj["projected_loss_1h_liters"]
            proj_6h_total += proj["projected_loss_6h_liters"]
            proj_24h_total += proj["projected_loss_24h_liters"]
            proj_7d_total += proj["projected_loss_7d_liters"]

    # 3. Prevented waste for resolved tickets
    # Strict rule: tickets missing valid resolved_at/detected_at timestamps (or where resolved_at <= detected_at)
    # are strictly excluded from estimated_water_saved.
    stmt_resolved = (
        select(Ticket, DetectionEvent)
        .join(DetectionEvent, Ticket.event_id == DetectionEvent.event_id)
        .where(Ticket.status == "resolved")
    )
    resolved_rows = (await db.execute(stmt_resolved)).all()

    total_water_saved = 0.0
    resolved_leaks_with_impact = 0

    for ticket, ev in resolved_rows:
        if ev.event_type == "leak" and ev.evidence_value:
            flow_lpm = float(ev.evidence_value) / 60.0
            elapsed_min = compute_ticket_elapsed_minutes(ev.detected_at, ticket.resolved_at)
            impact = calculate_prevented_waste(
                observed_flow_lpm=flow_lpm,
                elapsed_minutes=elapsed_min,
                ref_window_minutes=ref_window_minutes,
            )
            if impact is not None:
                total_water_saved += impact["estimated_water_saved_liters"]
                resolved_leaks_with_impact += 1

    avoided_cost = round(total_water_saved * tariff, 2)

    # 4. Top 5 highest-waste fixtures
    stmt_top_fixtures = (
        select(
            DetectionEvent.fixture_id,
            Fixture.fixture_type,
            Fixture.zone_id,
            Zone.name.label("zone_name"),
            func.coalesce(func.sum(DetectionEvent.evidence_value), 0.0).label("waste_liters"),
        )
        .join(Fixture, DetectionEvent.fixture_id == Fixture.fixture_id)
        .join(Zone, Fixture.zone_id == Zone.zone_id)
        .where(DetectionEvent.event_type == "leak")
        .group_by(DetectionEvent.fixture_id, Fixture.fixture_type, Fixture.zone_id, Zone.name)
        .order_by(func.sum(DetectionEvent.evidence_value).desc())
        .limit(5)
    )
    top_fixture_rows = (await db.execute(stmt_top_fixtures)).all()

    top_waste_fixtures = []
    for fid, ftype, zid, zname, waste in top_fixture_rows:
        w = round(float(waste or 0.0), 2)
        top_waste_fixtures.append({
            "fixture_id": fid,
            "fixture_type": ftype,
            "zone_id": zid,
            "zone_name": zname,
            "waste_liters": w,
            "cost_impact_inr": round(w * tariff, 2),
        })

    highest_waste_fixture = top_waste_fixtures[0] if top_waste_fixtures else None

    # 5. Top water-waste zones
    stmt_top_zones = (
        select(
            Zone.zone_id,
            Zone.name.label("zone_name"),
            Zone.criticality_tier,
            func.coalesce(func.sum(DetectionEvent.evidence_value), 0.0).label("waste_liters"),
            func.count(DetectionEvent.event_id).label("incident_count"),
        )
        .join(Fixture, DetectionEvent.fixture_id == Fixture.fixture_id)
        .join(Zone, Fixture.zone_id == Zone.zone_id)
        .where(DetectionEvent.event_type == "leak")
        .group_by(Zone.zone_id, Zone.name, Zone.criticality_tier)
        .order_by(func.sum(DetectionEvent.evidence_value).desc())
    )
    top_zone_rows = (await db.execute(stmt_top_zones)).all()

    top_waste_zones = []
    for zid, zname, tier, waste, inc_count in top_zone_rows:
        w = round(float(waste or 0.0), 2)
        top_waste_zones.append({
            "zone_id": zid,
            "zone_name": zname,
            "criticality_tier": tier,
            "waste_liters": w,
            "cost_impact_inr": round(w * tariff, 2),
            "incident_count": int(inc_count or 0),
        })

    highest_waste_zone = top_waste_zones[0] if top_waste_zones else None

    return {
        "water_waste_liters": round(total_water_wasted, 2),
        "estimated_water_saved_liters": round(total_water_saved, 2),
        "cost_impact": cost_impact,
        "avoided_cost": avoided_cost,
        "projected_unresolved_loss_liters": round(proj_24h_total, 2),
        "highest_waste_fixture": highest_waste_fixture,
        "highest_waste_zone": highest_waste_zone,
        "top_waste_fixtures": top_waste_fixtures,
        "top_waste_zones": top_waste_zones,
        "facility_projections": {
            "plus_1hr_liters": round(proj_1h_total, 2),
            "plus_1hr_cost_inr": round(proj_1h_total * tariff, 2),
            "plus_6hr_liters": round(proj_6h_total, 2),
            "plus_6hr_cost_inr": round(proj_6h_total * tariff, 2),
            "plus_24hr_liters": round(proj_24h_total, 2),
            "plus_24hr_cost_inr": round(proj_24h_total * tariff, 2),
            "plus_7days_liters": round(proj_7d_total, 2),
            "plus_7days_cost_inr": round(proj_7d_total * tariff, 2),
        },
        "active_tickets_count": len(active_rows),
        "active_leak_tickets_count": active_leak_count,
        "resolved_tickets_count": len(resolved_rows),
        "resolved_leaks_with_impact_count": resolved_leaks_with_impact,
        "tariff_inr_per_liter": tariff,
        "reference_window_hours": round(ref_window_minutes / 60.0, 1),
        "estimate_disclosure": "Estimated water saved is a counterfactual calculation based on a 6-hour unaddressed baseline reference window. Actual facility water savings may vary.",
    }


async def get_ticket_sustainability_impact(
    db: AsyncSession,
    ticket_id: str,
    ref_window_minutes: float = PREVENTED_WASTE_REF_WINDOW_MINUTES,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve single-ticket sustainability impact metrics:
    - If status == 'resolved': calculates intervention impact (water lost, estimated water avoided, avoided cost).
    - If active: returns incident loss projections at +1h, +6h, +24h, +7d.
    """
    tariff = getattr(settings, "WATER_COST_INR_PER_LITRE", 0.15)

    stmt = (
        select(Ticket, DetectionEvent, Fixture.fixture_type, Zone.name.label("zone_name"))
        .join(DetectionEvent, Ticket.event_id == DetectionEvent.event_id)
        .join(Fixture, DetectionEvent.fixture_id == Fixture.fixture_id)
        .join(Zone, Fixture.zone_id == Zone.zone_id)
        .where(Ticket.ticket_id == ticket_id)
    )
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        return None

    ticket, ev, ftype, zname = row
    is_leak = ev.event_type == "leak"
    flow_lph = float(ev.evidence_value or 0.0) if is_leak else 0.0
    flow_lpm = flow_lph / 60.0

    projections = compute_incident_projection(flow_lpm)

    elapsed_min = compute_ticket_elapsed_minutes(ev.detected_at, ticket.resolved_at)
    prevented = calculate_prevented_waste(
        observed_flow_lpm=flow_lpm,
        elapsed_minutes=elapsed_min,
        ref_window_minutes=ref_window_minutes,
    )

    return {
        "ticket_id": ticket.ticket_id,
        "event_id": ev.event_id,
        "fixture_id": ev.fixture_id,
        "fixture_type": ftype,
        "zone_name": zname,
        "status": ticket.status,
        "event_type": ev.event_type,
        "observed_flow_lpm": round(flow_lpm, 4),
        "observed_flow_lph": round(flow_lph, 2),
        "detected_at": ev.detected_at,
        "started_at": ticket.started_at,
        "resolved_at": ticket.resolved_at,
        "elapsed_minutes": elapsed_min,
        "is_resolved": ticket.status == "resolved",
        "has_valid_impact": prevented is not None,
        "prevented_waste": prevented,
        "projections": projections,
        "tariff_inr_per_liter": tariff,
        "reference_window_hours": round(ref_window_minutes / 60.0, 1),
    }
