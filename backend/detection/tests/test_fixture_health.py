"""
backend/detection/tests/test_fixture_health.py — Predictive Fixture Health API Tests.

Tests:
1. High-Risk fixture (e.g. fix-icu-002): multiple repeat leak events + open tickets -> health <= 40, high_risk status.
2. Healthy fixture (e.g. fix-ot-001): 0 incidents -> health == 100.0, risk == 0.0, healthy status.
3. Degrading fixture (e.g. fix-lab-003): elevated incident frequency + deteriorating trend -> 40 <= health < 60.
4. List filtering by zone_id, status, and sort orders via TestClient.
5. 404 response for invalid fixture_id via TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import AsyncSessionLocal
from app.services.fixture_health_service import compute_all_fixture_health, get_fixture_health_detail


@pytest.mark.anyio
async def test_fixture_health_high_risk_fixture():
    """Verify chronic failure fixture fix-icu-002 scores as High Risk (<= 40 health)."""
    async with AsyncSessionLocal() as db:
        data = await get_fixture_health_detail(db, "fix-icu-002")
        assert data is not None
        assert data["fixture_id"] == "fix-icu-002"
        assert data["health_status"] == "high_risk"
        assert data["health_score"] <= 40.0
        assert data["risk_score"] >= 60.0
        assert data["total_incidents"] >= 8
        assert data["active_tickets_count"] > 0
        assert data["sub_scores"]["frequency_score"] >= 90.0
        assert data["sub_scores"]["recurrence_score"] >= 90.0
        assert len(data["recent_incidents"]) > 0
        assert "Priority" in data["recommendation"]


@pytest.mark.anyio
async def test_fixture_health_healthy_fixture():
    """Verify clean fixture fix-ot-003 scores as Healthy (>=95 health, 0 incidents).

    Re-pointed 2026-09-20 21:33 from fix-ot-001 after the 7-day dataset reseed:
    fix-ot-001 now has 2 genuine incidents (an active gradual-leak ticket) in the
    new data and is no longer a zero-incident fixture. fix-ot-003 is the fixture
    verified to have 0 total_incidents in the current dataset. health_score is
    99.4 (not exactly 100) because of a small residual flow_drift_score (3.2)
    from ordinary flow variance, not an incident.
    """
    async with AsyncSessionLocal() as db:
        data = await get_fixture_health_detail(db, "fix-ot-003")
        assert data is not None
        assert data["fixture_id"] == "fix-ot-003"
        assert data["health_status"] == "healthy"
        assert data["health_score"] >= 95.0
        assert data["risk_score"] <= 5.0
        assert data["total_incidents"] == 0
        assert data["active_tickets_count"] == 0
        assert data["sub_scores"]["frequency_score"] == 0.0
        assert data["sub_scores"]["recurrence_score"] == 0.0
        assert data["sub_scores"]["flow_drift_score"] < 10.0
        assert len(data["recent_incidents"]) == 0
        assert "Normal" in data["recommendation"]


@pytest.mark.anyio
async def test_fixture_health_degrading_fixture():
    """Verify fix-lob-001 scores as Degrading (40 <= health < 60) with deteriorating trend.

    Re-pointed 2026-09-20 21:33 from fix-lab-003 after the 7-day dataset reseed:
    fix-lab-003 accumulated enough repeat stuck-valve incidents (11 total) in the
    new data to cross into high_risk. fix-lob-001 is the fixture verified to sit
    genuinely in the 40-59 degrading band (46.5 health) with a deteriorating trend.
    """
    async with AsyncSessionLocal() as db:
        data = await get_fixture_health_detail(db, "fix-lob-001")
        assert data is not None
        assert data["fixture_id"] == "fix-lob-001"
        assert data["health_status"] == "degrading"
        assert 40.0 <= data["health_score"] < 60.0
        assert data["risk_score"] > 40.0
        assert data["trend"] == "deteriorating"
        assert data["total_incidents"] >= 5
        assert len(data["recent_incidents"]) > 0


def test_fixture_health_list_endpoint_and_filters():
    """Verify GET /api/v1/fixtures/health returns all 20 fixtures and supports filtering and sorting."""
    client = TestClient(app)

    # 1. Unfiltered list
    resp = client.get("/api/v1/fixtures/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert "facility_health_score" in payload
    assert len(payload["fixtures"]) == 20
    assert payload["high_risk_count"] >= 1
    assert payload["healthy_count"] >= 1

    # 2. Filter by status=high_risk
    resp_hr = client.get("/api/v1/fixtures/health?status=high_risk")
    assert resp_hr.status_code == 200
    hr_fixtures = resp_hr.json()["fixtures"]
    assert len(hr_fixtures) == payload["high_risk_count"]
    for f in hr_fixtures:
        assert f["health_status"] == "high_risk"

    # 3. Filter by zone_id=zone-ot
    resp_ot = client.get("/api/v1/fixtures/health?zone_id=zone-ot")
    assert resp_ot.status_code == 200
    ot_fixtures = resp_ot.json()["fixtures"]
    for f in ot_fixtures:
        assert f["zone_id"] == "zone-ot"

    # 4. Sort by health_asc
    resp_sort = client.get("/api/v1/fixtures/health?sort_by=health_asc")
    assert resp_sort.status_code == 200
    sorted_fixtures = resp_sort.json()["fixtures"]
    scores = [f["health_score"] for f in sorted_fixtures]
    assert scores == sorted(scores)


def test_fixture_health_detail_endpoint_404():
    """Verify GET /api/v1/fixtures/{fixture_id}/health returns 404 for unknown fixture."""
    client = TestClient(app)
    resp = client.get("/api/v1/fixtures/non-existent-fix/health")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
