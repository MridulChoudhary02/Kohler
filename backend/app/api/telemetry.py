"""
app/api/telemetry.py — Telemetry Ingestion API endpoint (PRD Section 11, Phase 4).

Endpoint:
  POST /api/v1/telemetry/ingest

Accepts single reading or batch (list) of readings.
Persists TelemetryReading rows, passes readings through stateful DetectionService,
persists resulting DetectionEvent rows, and upserts HygieneCounter rows.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, List, Union
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import TelemetryReading, DetectionEvent, HygieneCounter, Sensor
from app.services.detection_service import detection_service

router = APIRouter(tags=["Telemetry"])


class TelemetryReadingIngest(BaseModel):
    sensor_id: str = Field(..., description="Sensor ID emitting the reading")
    timestamp: datetime = Field(..., description="ISO-8601 reading timestamp")
    flow_rate_lpm: float = Field(..., description="Flow rate in Litres per Minute")
    flush_event: int = Field(0, description="1 if flush event occurred, else 0")
    occupancy_state: int = Field(0, description="1 if occupied, else 0")
    diagnostic_status: str = Field("ok", description="Sensor status: ok | flatline | out_of_range | missing | drift")


def _parse_ts(dt_or_str: Any) -> datetime:
    if isinstance(dt_or_str, datetime):
        dt = dt_or_str
    else:
        dt = datetime.fromisoformat(str(dt_or_str))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@router.post(
    "/telemetry/ingest",
    status_code=status.HTTP_201_CREATED,
    summary="Ingest telemetry reading(s)",
    description="Ingest single or batch telemetry readings, run stateful detection engine, persist readings, events, and hygiene counters.",
)
async def ingest_telemetry(
    payload: Union[TelemetryReadingIngest, List[TelemetryReadingIngest]],
    db: AsyncSession = Depends(get_db),
):
    # Normalize single reading vs list
    readings_input = payload if isinstance(payload, list) else [payload]
    if not readings_input:
        return {"status": "success", "readings_ingested": 0, "events_generated": 0, "events": []}

    db_readings: list[TelemetryReading] = []
    generated_event_dicts: list[dict[str, Any]] = []

    for item in readings_input:
        reading_dict = item.model_dump()
        ts = _parse_ts(reading_dict["timestamp"])

        # 1. Persist TelemetryReading row
        db_reading = TelemetryReading(
            reading_id=str(uuid.uuid4()),
            sensor_id=item.sensor_id,
            timestamp=ts,
            flow_rate_lpm=item.flow_rate_lpm,
            flush_event=item.flush_event,
            occupancy_state=item.occupancy_state,
            diagnostic_status=item.diagnostic_status,
        )
        db_readings.append(db_reading)
        db.add(db_reading)

        # 2. Process reading through DetectionService
        events_out = detection_service.process_reading(reading_dict)
        generated_event_dicts.extend(events_out)

    # 3. Persist resulting DetectionEvent rows and update HygieneCounters
    db_events: list[DetectionEvent] = []
    for ev in generated_event_dicts:
        ev_id = ev.get("event_id") or str(uuid.uuid4())
        ev_type = ev.get("event_type", "leak")
        ev_status = ev.get("status", "logged")
        fid = ev.get("fixture_id", "")
        conf = float(ev.get("confidence_score", 0.90))
        ev_ts = _parse_ts(ev.get("detected_at", datetime.now(timezone.utc)))

        # Evidence value calculation (litres/hr estimated waste for leak; breach min for hygiene)
        evidence = ev.get("evidence_value")
        if evidence is None:
            if ev_type == "leak":
                ewma = float(ev.get("ewma_at_detection", 1.0))
                ucl = float(ev.get("ucl", 0.05))
                evidence = round(max(0.0, ewma - ucl) * 60.0, 2)   # Litres per hour estimated waste
            elif ev_type == "hygiene":
                evidence = float(ev.get("minutes_to_breach", 0.0))
            elif ev_type == "sensor_fault":
                evidence = float(ev.get("sensor_health_score", 0.0))

        db_ev = DetectionEvent(
            event_id=ev_id,
            fixture_id=fid,
            event_type=ev_type,
            confidence_score=conf,
            evidence_value=evidence,
            detected_at=ev_ts,
            status=ev_status,
        )
        db_events.append(db_ev)
        db.add(db_ev)

        # Upsert HygieneCounter row when a hygiene prediction event occurs
        if ev_type == "hygiene":
            pred_time_str = ev.get("predicted_breach_time")
            pred_time = _parse_ts(pred_time_str) if pred_time_str else None
            uses = int(ev.get("uses_since_clean", 0))

            stmt = select(HygieneCounter).where(HygieneCounter.fixture_id == fid)
            res = await db.execute(stmt)
            hc = res.scalar_one_or_none()

            if hc is None:
                hc = HygieneCounter(
                    id=str(uuid.uuid4()),
                    fixture_id=fid,
                    uses_since_clean=uses,
                    predicted_breach_time=pred_time,
                )
                db.add(hc)
            else:
                hc.uses_since_clean = uses
                hc.predicted_breach_time = pred_time

    await db.flush()

    return {
        "status": "success",
        "readings_ingested": len(db_readings),
        "events_generated": len(generated_event_dicts),
        "events": [
            {
                "event_id": e.event_id,
                "fixture_id": e.fixture_id,
                "event_type": e.event_type,
                "confidence_score": e.confidence_score,
                "evidence_value": e.evidence_value,
                "detected_at": e.detected_at.isoformat(),
                "status": e.status,
            }
            for e in db_events
        ],
    }
