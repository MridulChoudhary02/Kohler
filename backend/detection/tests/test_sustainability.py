"""
backend/detection/tests/test_sustainability.py — Unit & Integration Tests for Sustainability Impact

Verifies:
1. Incident projection math at +1hr, +6hr, +24hr, +7days using realistic fixture flow values
   from this codebase (e.g. fix-icu-002 @ 0.8163 LPM, fix-ward-002 @ 0.6667 LPM).
2. Prevented-waste counterfactual math for resolved tickets with 6-hour reference window (360 min).
3. Strict timestamp validation (missing/invalid timestamps excluded without fallback).
4. Tariff grounding (WATER_COST_INR_PER_LITRE = 0.15).
5. GET /api/v1/sustainability/summary endpoint integration.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.sustainability_service import (
    PREVENTED_WASTE_REF_WINDOW_MINUTES,
    compute_incident_projection,
    calculate_prevented_waste,
    compute_ticket_elapsed_minutes,
)


def test_tariff_constant_is_grounded():
    """Verify tariff constant is ₹0.15/L and imported directly from settings."""
    assert hasattr(settings, "WATER_COST_INR_PER_LITRE")
    assert settings.WATER_COST_INR_PER_LITRE == 0.15


def test_incident_projection_math_realistic_flows():
    """
    Verify incident loss projection at +1hr, +6hr, +24hr, +7days.
    Uses realistic flow rates from actual test fixtures:
    - fix-icu-002 slow leak: 48.98 L/hr => 0.816333... LPM
    - fix-ward-002 leak: 40.0 L/hr => 0.666667... LPM
    - fix-ot-001 clean fixture: 0.0 LPM
    """
    # 1. fix-icu-002 (48.98 L/hr)
    flow_icu = 48.98 / 60.0  # ~0.816333 LPM
    proj_icu = compute_incident_projection(flow_icu)

    assert proj_icu["observed_flow_lpm"] == round(flow_icu, 4)
    # +1hr (60m)
    assert proj_icu["projected_loss_1h_liters"] == round(flow_icu * 60.0, 2)
    assert proj_icu["projected_cost_1h_inr"] == round(proj_icu["projected_loss_1h_liters"] * 0.15, 2)
    # +6hr (360m)
    assert proj_icu["projected_loss_6h_liters"] == round(flow_icu * 360.0, 2)
    assert proj_icu["projected_cost_6h_inr"] == round(proj_icu["projected_loss_6h_liters"] * 0.15, 2)
    # +24hr (1440m)
    assert proj_icu["projected_loss_24h_liters"] == round(flow_icu * 1440.0, 2)
    assert proj_icu["projected_cost_24h_inr"] == round(proj_icu["projected_loss_24h_liters"] * 0.15, 2)
    # +7days (10080m)
    assert proj_icu["projected_loss_7d_liters"] == round(flow_icu * 10080.0, 2)
    assert proj_icu["projected_cost_7d_inr"] == round(proj_icu["projected_loss_7d_liters"] * 0.15, 2)

    # 2. fix-ward-002 (40.0 L/hr)
    flow_ward = 40.0 / 60.0
    proj_ward = compute_incident_projection(flow_ward)
    assert proj_ward["projected_loss_1h_liters"] == 40.0
    assert proj_ward["projected_cost_1h_inr"] == 6.0  # 40 * 0.15
    assert proj_ward["projected_loss_6h_liters"] == 240.0
    assert proj_ward["projected_cost_6h_inr"] == 36.0  # 240 * 0.15
    assert proj_ward["projected_loss_24h_liters"] == 960.0
    assert proj_ward["projected_cost_24h_inr"] == 144.0  # 960 * 0.15
    assert proj_ward["projected_loss_7d_liters"] == 6720.0
    assert proj_ward["projected_cost_7d_inr"] == 1008.0

    # 3. Healthy fixture (fix-ot-001) zero flow
    proj_clean = compute_incident_projection(0.0)
    assert proj_clean["projected_loss_1h_liters"] == 0.0
    assert proj_clean["projected_loss_24h_liters"] == 0.0
    assert proj_clean["projected_cost_24h_inr"] == 0.0


def test_prevented_waste_within_6hr_reference_window():
    """
    Verify counterfactual prevented waste calculation when an incident is resolved
    before the 6-hour reference window elapsed.
    Example: 18 minutes resolution time on fix-icu-002 flow rate (0.8163 LPM).
    """
    flow = 0.8163
    elapsed_min = 18.0
    ref_window = 360.0  # 6 hours

    result = calculate_prevented_waste(flow, elapsed_min, ref_window_minutes=ref_window)
    assert result is not None

    expected_actual = round(flow * elapsed_min, 2)  # 14.69 L
    expected_potential = round(flow * ref_window, 2)  # 293.87 L
    expected_saved = round(expected_potential - expected_actual, 2)  # 279.18 L
    expected_avoided_cost = round(expected_saved * 0.15, 2)

    assert result["actual_loss_liters"] == expected_actual
    assert result["potential_loss_liters"] == expected_potential
    assert result["estimated_water_saved_liters"] == expected_saved
    assert result["avoided_cost_inr"] == expected_avoided_cost
    assert result["reference_window_minutes"] == 360.0


def test_prevented_waste_exceeding_reference_window():
    """
    When incident took longer than reference window (e.g. 400 min > 360 min),
    potential duration projects forward by reference window (+360 min).
    """
    flow = 1.0  # 1 LPM
    elapsed_min = 400.0
    ref_window = 360.0

    result = calculate_prevented_waste(flow, elapsed_min, ref_window_minutes=ref_window)
    assert result is not None
    assert result["actual_loss_liters"] == 400.0
    assert result["potential_loss_liters"] == 760.0  # 400 + 360
    assert result["estimated_water_saved_liters"] == 360.0
    assert result["avoided_cost_inr"] == round(360.0 * 0.15, 2)  # ₹54.0


def test_strict_timestamp_exclusion_rule():
    """
    User Requirement: Any resolved ticket missing valid resolved_at/detected_at timestamps
    (or where resolved_at <= detected_at) must be excluded from estimated_water_saved entirely.
    No fallback duration substituted.
    """
    now = datetime.now(timezone.utc)

    # 1. Missing resolved_at
    assert compute_ticket_elapsed_minutes(now, None) is None
    assert calculate_prevented_waste(1.0, None) is None

    # 2. Missing detected_at
    assert compute_ticket_elapsed_minutes(None, now) is None

    # 3. resolved_at earlier than or equal to detected_at
    earlier = now - timedelta(minutes=10)
    assert compute_ticket_elapsed_minutes(now, earlier) is None
    assert compute_ticket_elapsed_minutes(now, now) is None

    # 4. Valid order
    later = now + timedelta(minutes=45)
    elapsed = compute_ticket_elapsed_minutes(now, later)
    assert elapsed is not None
    assert round(elapsed, 1) == 45.0


def test_sustainability_summary_endpoint():
    """
    Test GET /api/v1/sustainability/summary endpoint returns 200 and
    contains all required fields matching the feature spec.
    """
    client = TestClient(app)
    resp = client.get("/api/v1/sustainability/summary")
    assert resp.status_code == 200

    data = resp.json()
    assert "water_waste_liters" in data
    assert "estimated_water_saved_liters" in data
    assert "cost_impact" in data
    assert "avoided_cost" in data
    assert "projected_unresolved_loss_liters" in data
    assert "highest_waste_fixture" in data
    assert "highest_waste_zone" in data
    assert "top_waste_fixtures" in data
    assert "top_waste_zones" in data
    assert "facility_projections" in data
    assert "tariff_inr_per_liter" in data
    assert "reference_window_hours" in data
    assert "estimate_disclosure" in data

    # Grounding checks
    assert data["tariff_inr_per_liter"] == 0.15
    assert data["reference_window_hours"] == 6.0
    assert data["water_waste_liters"] >= 0.0
    assert data["estimated_water_saved_liters"] >= 0.0
    assert data["projected_unresolved_loss_liters"] >= 0.0

    # Ensure cost impact is consistent with tariff
    assert data["cost_impact"] == round(data["water_waste_liters"] * 0.15, 2)
    assert data["avoided_cost"] == round(data["estimated_water_saved_liters"] * 0.15, 2)

    # Projections matrix check
    proj = data["facility_projections"]
    assert "plus_1hr_liters" in proj
    assert "plus_6hr_liters" in proj
    assert "plus_24hr_liters" in proj
    assert "plus_7days_liters" in proj
    assert data["projected_unresolved_loss_liters"] == proj["plus_24hr_liters"]
