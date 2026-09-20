"""
backend/app/api/sustainability.py — Sustainability & Water-Savings Endpoints

Track 2 Feature Specification (Section 2):
- GET /api/v1/sustainability/summary
- GET /api/v1/sustainability/ticket/{ticket_id}
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.sustainability_service import (
    PREVENTED_WASTE_REF_WINDOW_MINUTES,
    compute_facility_sustainability_summary,
    get_ticket_sustainability_impact,
)

router = APIRouter(prefix="/sustainability", tags=["Sustainability"])


class TopWasteFixtureRead(BaseModel):
    fixture_id: str
    fixture_type: str
    zone_id: str
    zone_name: str
    waste_liters: float
    cost_impact_inr: float


class TopWasteZoneRead(BaseModel):
    zone_id: str
    zone_name: str
    criticality_tier: str
    waste_liters: float
    cost_impact_inr: float
    incident_count: int


class FacilityProjectionsRead(BaseModel):
    plus_1hr_liters: float
    plus_1hr_cost_inr: float
    plus_6hr_liters: float
    plus_6hr_cost_inr: float
    plus_24hr_liters: float
    plus_24hr_cost_inr: float
    plus_7days_liters: float
    plus_7days_cost_inr: float


class SustainabilitySummaryRead(BaseModel):
    water_waste_liters: float
    estimated_water_saved_liters: float
    cost_impact: float
    avoided_cost: float
    projected_unresolved_loss_liters: float
    highest_waste_fixture: Optional[TopWasteFixtureRead] = None
    highest_waste_zone: Optional[TopWasteZoneRead] = None
    top_waste_fixtures: List[TopWasteFixtureRead] = []
    top_waste_zones: List[TopWasteZoneRead] = []
    facility_projections: FacilityProjectionsRead
    active_tickets_count: int
    active_leak_tickets_count: int
    resolved_tickets_count: int
    resolved_leaks_with_impact_count: int
    tariff_inr_per_liter: float
    reference_window_hours: float
    estimate_disclosure: str


class PreventedWasteRead(BaseModel):
    observed_flow_lpm: float
    elapsed_minutes: float
    actual_loss_liters: float
    potential_loss_liters: float
    estimated_water_saved_liters: float
    avoided_cost_inr: float
    cost_impact_inr: float
    reference_window_minutes: float


class TicketProjectionsRead(BaseModel):
    observed_flow_lpm: float
    projected_loss_1h_liters: float
    projected_cost_1h_inr: float
    projected_loss_6h_liters: float
    projected_cost_6h_inr: float
    projected_loss_24h_liters: float
    projected_cost_24h_inr: float
    projected_loss_7d_liters: float
    projected_cost_7d_inr: float


class TicketSustainabilityImpactRead(BaseModel):
    ticket_id: str
    event_id: str
    fixture_id: str
    fixture_type: str
    zone_name: str
    status: str
    event_type: str
    observed_flow_lpm: float
    observed_flow_lph: float
    detected_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    elapsed_minutes: Optional[float] = None
    is_resolved: bool
    has_valid_impact: bool
    prevented_waste: Optional[PreventedWasteRead] = None
    projections: TicketProjectionsRead
    tariff_inr_per_liter: float
    reference_window_hours: float


@router.get(
    "/summary",
    response_model=SustainabilitySummaryRead,
    summary="Get facility sustainability impact summary",
    description=(
        "Returns facility-level water waste, estimated water saved, cost impact, "
        "avoided cost, +24h projected unresolved loss, highest waste fixture, and highest waste zone."
    ),
)
async def get_sustainability_summary(
    db: AsyncSession = Depends(get_db),
    ref_window_hours: float = Query(6.0, description="Counterfactual unaddressed reference window in hours"),
):
    ref_window_minutes = max(1.0, ref_window_hours * 60.0)
    return await compute_facility_sustainability_summary(db, ref_window_minutes=ref_window_minutes)


@router.get(
    "/ticket/{ticket_id}",
    response_model=TicketSustainabilityImpactRead,
    summary="Get single ticket sustainability & intervention impact",
    description="Returns incident projection for active tickets, or intervention prevented waste for resolved tickets.",
)
async def get_ticket_impact(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    ref_window_hours: float = Query(6.0, description="Counterfactual unaddressed reference window in hours"),
):
    ref_window_minutes = max(1.0, ref_window_hours * 60.0)
    impact = await get_ticket_sustainability_impact(db, ticket_id=ticket_id, ref_window_minutes=ref_window_minutes)
    if not impact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found",
        )
    return impact
