"""
detection/tests/test_ingestion_api.py — Unit test for FastAPI Telemetry Ingestion Endpoint.

Tests POST /api/v1/telemetry/ingest using FastAPI TestClient (or httpx) with SQLite/in-memory fallback session.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unittest.mock import AsyncMock
from app.main import app
from app.core.database import get_db

async def override_get_db():
    mock_session = AsyncMock()
    mock_res = AsyncMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_res
    yield mock_session

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ingest_single_reading():
    reading = {
        "sensor_id": "sen-icu-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "flow_rate_lpm": 0.0,
        "flush_event": 0,
        "occupancy_state": 0,
        "diagnostic_status": "ok",
    }
    response = client.post("/api/v1/telemetry/ingest", json=reading)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["readings_ingested"] == 1


def test_ingest_batch_readings():
    readings = [
        {
            "sensor_id": "sen-icu-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "flow_rate_lpm": 0.0,
            "flush_event": 0,
            "occupancy_state": 0,
            "diagnostic_status": "ok",
        },
        {
            "sensor_id": "sen-icu-002",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "flow_rate_lpm": 6.0,
            "flush_event": 1,
            "occupancy_state": 0,
            "diagnostic_status": "ok",
        }
    ]
    response = client.post("/api/v1/telemetry/ingest", json=readings)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["readings_ingested"] == 2


if __name__ == "__main__":
    test_health_check()
    test_ingest_single_reading()
    test_ingest_batch_readings()
    print("✅ Ingestion API unit tests PASSED")
