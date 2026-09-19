"""
app/api/events.py — Read-only Query Endpoints (PRD Section 11, Phase 4b).

Endpoints:
  GET /api/v1/events — List detection events with filtering & pagination
  GET /api/v1/events/{event_id} — Get single detection event with fixture/zone context
  GET /api/v1/tickets — List ticket rows (empty until Phase 5)
  GET /api/v1/hygiene-counters — List hygiene counter state per fixture
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.models import DetectionEvent, Fixture, Zone, Ticket, HygieneCounter, BaselineProfile, Sensor, TelemetryReading
from app.services.llm_service import summarize_incident, answer_facility_query, FALLBACK_SUMMARY
from detection.sensor_health import SensorHealthTracker

router = APIRouter(tags=["Events & Operations"])


# ─────────────────────────────────────────────
# PYDANTIC RESPONSE SCHEMAS
# ─────────────────────────────────────────────
class DetectionEventRead(BaseModel):
    event_id: str
    fixture_id: str
    event_type: str
    confidence_score: float
    evidence_value: Optional[float] = None
    detected_at: datetime
    status: str
    fixture_type: Optional[str] = None
    zone_id: Optional[str] = None
    zone_name: Optional[str] = None
    criticality_tier: Optional[str] = None

    class Config:
        from_attributes = True


class TicketRead(BaseModel):
    ticket_id: str
    event_id: str
    zone_id: str
    priority_score: float
    status: str
    sla_due: Optional[datetime] = None
    assigned_team: Optional[str] = None
    assigned_tech_id: Optional[str] = None
    is_escalated: bool = False
    summary_text: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HygieneCounterRead(BaseModel):
    id: str
    fixture_id: str
    uses_since_clean: int
    last_cleaned: Optional[datetime] = None
    predicted_breach_time: Optional[datetime] = None
    fixture_type: Optional[str] = None
    zone_id: Optional[str] = None
    criticality_tier: Optional[str] = None

class BaselineProfileRead(BaseModel):
    fixture_id: str
    mean_off_flow: float
    std_off_flow: float
    mean_flush_volume: float
    mean_flush_duration_s: float
    ucl: float
    warmup_complete: bool
    last_updated: datetime

    class Config:
        from_attributes = True


class TelemetryReadingRead(BaseModel):
    reading_id: str
    sensor_id: str
    timestamp: datetime
    flow_rate_lpm: float
    flush_event: int
    occupancy_state: int
    diagnostic_status: str

    class Config:
        from_attributes = True


class ChatQueryRequest(BaseModel):
    query: str


class ChatQueryResponse(BaseModel):
    answer: str


class SummaryRegenerateResponse(BaseModel):
    ticket_id: str
    summary_text: str


class FacilityMetricsRead(BaseModel):
    total_water_wasted_litres: float = Field(..., description="Total water wasted across leak events (litres)")
    cost_at_risk_inr: float = Field(..., description="Estimated cost saved/at risk in INR (₹)")
    co2_at_risk_kg: float = Field(..., description="Estimated CO2 equivalent at risk in kg")
    sensors_online: int = Field(..., description="Number of active reporting sensors")
    sensors_total: int = Field(..., description="Total installed sensors")
    avg_sensor_health_score: float = Field(..., description="Average sensor health score across facility (0.0 to 1.0)")
    anomalies_today: int = Field(..., description="Total anomalies detected on active date (leak + hygiene + sensor_fault)")
    total_anomalies: int = Field(..., description="Total anomalies detected all-time")
    water_cost_per_litre: float = Field(..., description="Configured water cost conversion factor in ₹/L")
    co2_per_litre: float = Field(..., description="Configured CO2 conversion factor in kg/L")


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────
@router.get(
    "/events",
    response_model=List[DetectionEventRead],
    summary="List detection events",
    description="List detection events filterable by fixture_id, zone_id, event_type, status with pagination.",
)
async def list_events(
    fixture_id: Optional[str] = Query(None, description="Filter by fixture ID"),
    zone_id: Optional[str] = Query(None, description="Filter by zone ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type: leak | hygiene | sensor_fault"),
    status: Optional[str] = Query(None, description="Filter by status: logged | dispatched | resolved"),
    limit: int = Query(50, ge=1, le=1000, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(DetectionEvent, Fixture.fixture_type, Zone.zone_id, Zone.name.label("zone_name"), Zone.criticality_tier)
        .join(Fixture, DetectionEvent.fixture_id == Fixture.fixture_id)
        .join(Zone, Fixture.zone_id == Zone.zone_id)
    )

    if fixture_id:
        stmt = stmt.where(DetectionEvent.fixture_id == fixture_id)
    if zone_id:
        stmt = stmt.where(Zone.zone_id == zone_id)
    if event_type:
        stmt = stmt.where(DetectionEvent.event_type == event_type)
    if status:
        stmt = stmt.where(DetectionEvent.status == status)

    stmt = stmt.order_by(DetectionEvent.detected_at.desc()).offset(offset).limit(limit)

    res = await db.execute(stmt)
    rows = res.all()

    items = []
    for ev, ftype, zid, zname, tier in rows:
        items.append(
            DetectionEventRead(
                event_id=ev.event_id,
                fixture_id=ev.fixture_id,
                event_type=ev.event_type,
                confidence_score=ev.confidence_score,
                evidence_value=ev.evidence_value,
                detected_at=ev.detected_at,
                status=ev.status,
                fixture_type=ftype,
                zone_id=zid,
                zone_name=zname,
                criticality_tier=tier,
            )
        )
    return items


@router.get(
    "/events/{event_id}",
    response_model=DetectionEventRead,
    summary="Get single detection event",
    description="Retrieve a single detection event by ID with fixture and zone context joined.",
)
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(DetectionEvent, Fixture.fixture_type, Zone.zone_id, Zone.name.label("zone_name"), Zone.criticality_tier)
        .join(Fixture, DetectionEvent.fixture_id == Fixture.fixture_id)
        .join(Zone, Fixture.zone_id == Zone.zone_id)
        .where(DetectionEvent.event_id == event_id)
    )
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detection event {event_id} not found",
        )

    ev, ftype, zid, zname, tier = row
    return DetectionEventRead(
        event_id=ev.event_id,
        fixture_id=ev.fixture_id,
        event_type=ev.event_type,
        confidence_score=ev.confidence_score,
        evidence_value=ev.evidence_value,
        detected_at=ev.detected_at,
        status=ev.status,
        fixture_type=ftype,
        zone_id=zid,
        zone_name=zname,
        criticality_tier=tier,
    )


@router.get(
    "/tickets",
    response_model=List[TicketRead],
    summary="List tickets",
    description="List ticket rows filterable by status, zone_id, assigned_tech_id, sorted by priority_score descending.",
)
async def list_tickets(
    status: Optional[str] = Query(None, description="Filter by status: open | acknowledged | in_progress | resolved"),
    zone_id: Optional[str] = Query(None, description="Filter by zone ID"),
    assigned_tech_id: Optional[str] = Query(None, description="Filter by assigned technician ID"),
    limit: int = Query(50, ge=1, le=1000, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Ticket)
    if status:
        stmt = stmt.where(Ticket.status == status)
    if zone_id:
        stmt = stmt.where(Ticket.zone_id == zone_id)
    if assigned_tech_id:
        stmt = stmt.where(Ticket.assigned_tech_id == assigned_tech_id)

    stmt = stmt.order_by(Ticket.priority_score.desc()).offset(offset).limit(limit)

    res = await db.execute(stmt)
    tickets = res.scalars().all()
    return tickets


@router.post(
    "/tickets/{ticket_id}/acknowledge",
    response_model=TicketRead,
    summary="Acknowledge ticket",
    description="Transition ticket status to 'acknowledged' with timestamp.",
)
async def acknowledge_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Ticket).where(Ticket.ticket_id == ticket_id)
    res = await db.execute(stmt)
    ticket = res.scalars().first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found",
        )
    ticket.status = "acknowledged"
    ticket.acknowledged_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.post(
    "/tickets/{ticket_id}/start",
    response_model=TicketRead,
    summary="Start work on ticket",
    description="Transition ticket status to 'in_progress' with started_at timestamp.",
)
async def start_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Ticket).where(Ticket.ticket_id == ticket_id)
    res = await db.execute(stmt)
    ticket = res.scalars().first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found",
        )
    ticket.status = "in_progress"
    ticket.started_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.post(
    "/tickets/{ticket_id}/resolve",
    response_model=TicketRead,
    summary="Resolve ticket",
    description="Transition ticket status to 'resolved' with timestamp.",
)
async def resolve_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Ticket).where(Ticket.ticket_id == ticket_id)
    res = await db.execute(stmt)
    ticket = res.scalars().first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found",
        )
    ticket.status = "resolved"
    ticket.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.get(
    "/hygiene-counters",
    response_model=List[HygieneCounterRead],
    summary="List hygiene counters",
    description="List current hygiene counter states per fixture with zone context.",
)
async def list_hygiene_counters(
    fixture_id: Optional[str] = Query(None),
    zone_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(HygieneCounter, Fixture.fixture_type, Zone.zone_id, Zone.criticality_tier)
        .join(Fixture, HygieneCounter.fixture_id == Fixture.fixture_id)
        .join(Zone, Fixture.zone_id == Zone.zone_id)
    )

    if fixture_id:
        stmt = stmt.where(HygieneCounter.fixture_id == fixture_id)
    if zone_id:
        stmt = stmt.where(Zone.zone_id == zone_id)

    res = await db.execute(stmt)
    rows = res.all()

    items = []
    for hc, ftype, zid, tier in rows:
        items.append(
            HygieneCounterRead(
                id=hc.id,
                fixture_id=hc.fixture_id,
                uses_since_clean=hc.uses_since_clean,
                last_cleaned=hc.last_cleaned,
                predicted_breach_time=hc.predicted_breach_time,
                fixture_type=ftype,
                zone_id=zid,
                criticality_tier=tier,
            )
        )
    return items


@router.get(
    "/fixtures/{fixture_id}/baseline",
    response_model=BaselineProfileRead,
    summary="Get baseline profile for fixture",
    description="Retrieve baseline statistical profile and UCL for a fixture.",
)
async def get_fixture_baseline(
    fixture_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(BaselineProfile).where(BaselineProfile.fixture_id == fixture_id)
    res = await db.execute(stmt)
    bp = res.scalars().first()
    if not bp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Baseline profile for fixture {fixture_id} not found",
        )
    ucl = round(bp.mean_off_flow + 3.0 * bp.std_off_flow, 4)
    return BaselineProfileRead(
        fixture_id=bp.fixture_id,
        mean_off_flow=bp.mean_off_flow,
        std_off_flow=bp.std_off_flow,
        mean_flush_volume=bp.mean_flush_volume,
        mean_flush_duration_s=bp.mean_flush_duration_s,
        ucl=ucl,
        warmup_complete=bp.warmup_complete,
        last_updated=bp.last_updated,
    )


@router.get(
    "/fixtures/{fixture_id}/telemetry",
    response_model=List[TelemetryReadingRead],
    summary="Get recent telemetry readings for fixture",
    description="Retrieve recent raw telemetry readings emitted by fixture's sensor around a timestamp.",
)
async def get_fixture_telemetry(
    fixture_id: str,
    detected_at: Optional[str] = Query(None, description="ISO timestamp around which to fetch telemetry"),
    limit: int = Query(30, ge=1, le=200, description="Max readings to return"),
    db: AsyncSession = Depends(get_db),
):
    # 1. Get sensor_id for fixture_id
    sensor_stmt = select(Sensor.sensor_id).where(Sensor.fixture_id == fixture_id)
    sensor_res = await db.execute(sensor_stmt)
    sensor_id = sensor_res.scalar_one_or_none()
    if not sensor_id:
        return []

    stmt = select(TelemetryReading).where(TelemetryReading.sensor_id == sensor_id)

    if detected_at:
        try:
            target_dt = datetime.fromisoformat(detected_at.replace('Z', '+00:00'))
            if target_dt.tzinfo is None:
                target_dt = target_dt.replace(tzinfo=timezone.utc)
            start_window = target_dt - timedelta(minutes=15)
            end_window = target_dt + timedelta(minutes=5)
            stmt = stmt.where(TelemetryReading.timestamp >= start_window, TelemetryReading.timestamp <= end_window)
        except Exception:
            pass

    stmt = stmt.order_by(TelemetryReading.timestamp.asc()).limit(limit)
    res = await db.execute(stmt)
    readings = res.scalars().all()
    return readings


@router.post(
    "/chat",
    response_model=ChatQueryResponse,
    summary="Chat-over-data query interface",
    description="Ask natural-language queries about facility status, active leaks, priority tickets, and sensor health (PRD Section 12b).",
)
async def chat_query(
    body: ChatQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    answer = await answer_facility_query(body.query, db)
    return ChatQueryResponse(answer=answer)


@router.post(
    "/tickets/{ticket_id}/summary/regenerate",
    response_model=SummaryRegenerateResponse,
    summary="Regenerate ticket summary",
    description="Regenerates the LLM-derived summary for an existing ticket using its event, fixture, and zone context (PRD Section 12a).",
)
async def regenerate_ticket_summary(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Ticket).where(Ticket.ticket_id == ticket_id)
    res = await db.execute(stmt)
    ticket = res.scalars().first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found",
        )

    # Fetch event, fixture, and zone for this ticket
    event_stmt = select(DetectionEvent).where(DetectionEvent.event_id == ticket.event_id)
    event_res = await db.execute(event_stmt)
    event = event_res.scalars().first()

    fixture_obj, zone_obj = None, None
    if event:
        fz_stmt = (
            select(Fixture, Zone)
            .join(Zone, Fixture.zone_id == Zone.zone_id)
            .where(Fixture.fixture_id == event.fixture_id)
        )
        fz_res = await db.execute(fz_stmt)
        fz_row = fz_res.first()
        if fz_row:
            fixture_obj, zone_obj = fz_row

    summary = summarize_incident(ticket, event, fixture_obj, zone_obj)
    if summary != FALLBACK_SUMMARY:
        ticket.summary_text = summary
        await db.commit()
        await db.refresh(ticket)
    return SummaryRegenerateResponse(ticket_id=ticket.ticket_id, summary_text=ticket.summary_text)


@router.get(
    "/facility/metrics",
    response_model=FacilityMetricsRead,
    summary="Get real-time facility sustainability and health metrics",
    description="Returns real DB-backed sustainability and system-health KPIs (water waste, cost, CO2, sensor online count, sensor health, anomalies today).",
)
async def get_facility_metrics(
    db: AsyncSession = Depends(get_db),
):
    # 1. Total water wasted (leak events continuous flow sum)
    stmt_waste = select(func.coalesce(func.sum(DetectionEvent.evidence_value), 0.0)).where(
        DetectionEvent.event_type == "leak"
    )
    total_water_wasted = float((await db.execute(stmt_waste)).scalar() or 0.0)

    # 2. Sensors online vs total
    stmt_sensors = select(
        func.count(Sensor.sensor_id),
        func.count(case((Sensor.status == "active", 1)))
    ).select_from(Sensor)
    res_sensors = (await db.execute(stmt_sensors)).first()
    sensors_total = res_sensors[0] or 0
    sensors_active = res_sensors[1] or 0

    # 3. Average sensor health score across facility using rolling window from TelemetryReading
    sensors_res = (await db.execute(select(Sensor.sensor_id, Sensor.fixture_id))).fetchall()
    health_scores = []
    for sid, fid in sensors_res:
        tracker = SensorHealthTracker(sensor_id=sid, fixture_id=fid)
        readings = (await db.execute(
            select(
                TelemetryReading.timestamp,
                TelemetryReading.flow_rate_lpm,
                TelemetryReading.occupancy_state,
                TelemetryReading.diagnostic_status,
            )
            .where(TelemetryReading.sensor_id == sid)
            .order_by(TelemetryReading.timestamp.desc())
            .limit(120)
        )).fetchall()
        for r in reversed(readings):
            score, _ = tracker.process_reading({
                "timestamp": r[0],
                "flow_rate_lpm": r[1],
                "occupancy_state": r[2],
                "diagnostic_status": r[3],
            })
        health_scores.append(score)

    avg_health = sum(health_scores) / len(health_scores) if health_scores else 1.0

    # 4. Anomalies today (latest simulation date or today UTC)
    max_date = (await db.execute(select(func.date(func.max(DetectionEvent.detected_at))))).scalar()
    stmt_today = select(func.count(DetectionEvent.event_id)).where(
        func.date(DetectionEvent.detected_at) == max_date
    )
    anomalies_today = int((await db.execute(stmt_today)).scalar() or 0)
    stmt_total_events = select(func.count(DetectionEvent.event_id))
    total_anomalies = int((await db.execute(stmt_total_events)).scalar() or 0)

    # 5. Sustainability calculations using config conversion factors
    cost_rate = getattr(settings, "WATER_COST_INR_PER_LITRE", 0.15)
    co2_rate = getattr(settings, "WATER_CO2_KG_PER_LITRE", 0.0004)
    cost_at_risk = round(total_water_wasted * cost_rate, 2)
    co2_at_risk = round(total_water_wasted * co2_rate, 2)

    return FacilityMetricsRead(
        total_water_wasted_litres=round(total_water_wasted, 2),
        cost_at_risk_inr=cost_at_risk,
        co2_at_risk_kg=co2_at_risk,
        sensors_online=sensors_active,
        sensors_total=sensors_total,
        avg_sensor_health_score=round(avg_health, 4),
        anomalies_today=anomalies_today,
        total_anomalies=total_anomalies,
        water_cost_per_litre=cost_rate,
        co2_per_litre=co2_rate,
    )

