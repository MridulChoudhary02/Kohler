"""
app/api/events.py — Read-only Query Endpoints (PRD Section 11, Phase 4b).

Endpoints:
  GET /api/v1/events — List detection events with filtering & pagination
  GET /api/v1/events/{event_id} — Get single detection event with fixture/zone context
  GET /api/v1/tickets — List ticket rows (empty until Phase 5)
  GET /api/v1/hygiene-counters — List hygiene counter state per fixture
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import DetectionEvent, Fixture, Zone, Ticket, HygieneCounter

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
    summary_text: Optional[str] = None

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

    class Config:
        from_attributes = True


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
    description="List ticket rows (empty until Phase 5 dispatch engine creates tickets).",
)
async def list_tickets(
    zone_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Ticket)
    if zone_id:
        stmt = stmt.where(Ticket.zone_id == zone_id)
    if status:
        stmt = stmt.where(Ticket.status == status)
    stmt = stmt.order_by(Ticket.priority_score.desc()).offset(offset).limit(limit)

    res = await db.execute(stmt)
    tickets = res.scalars().all()
    return tickets


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
