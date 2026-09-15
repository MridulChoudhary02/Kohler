"""
app/services/detection_service.py — In-memory stateful detection service for live telemetry ingestion.

Wraps DetectionEngine (+ SensorHealthTracker + HygieneTracker) as an app-level singleton.
Maintains per-fixture state machines in memory across API requests.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from detection.baseline import BaselineProfile, load_baselines
from detection.engine import DetectionEngine
from scripts.seed_data import SEED

logger = logging.getLogger("kohler.detection_service")

PREWARM_BASELINES_PATH = Path(__file__).resolve().parents[2] / "simulator" / "output" / "prewarm" / "baseline_profiles.json"


def _build_fixture_list() -> list[dict[str, str]]:
    zone_map   = {z["zone_id"]: z["criticality_tier"] for z in SEED["zones"]}
    sensor_map = {s["fixture_id"]: s["sensor_id"] for s in SEED["sensors"]}
    return [
        {
            "fixture_id":   fx["fixture_id"],
            "sensor_id":    sensor_map[fx["fixture_id"]],
            "fixture_type": fx["fixture_type"],
            "zone_tier":    zone_map[fx["zone_id"]],
            "zone_id":      fx["zone_id"],
        }
        for fx in SEED["fixtures"]
    ]


class DetectionService:
    """Singleton service wrapping DetectionEngine for live FastAPI ingestion."""

    _instance: Optional["DetectionService"] = None

    def __init__(self):
        self.engine: Optional[DetectionEngine] = None
        self.baselines: dict[str, BaselineProfile] = {}
        self.fixture_info: list[dict[str, str]] = _build_fixture_list()
        self.sensor_to_fixture: dict[str, str] = {f["sensor_id"]: f["fixture_id"] for f in self.fixture_info}
        self.fixture_to_sensor: dict[str, str] = {f["fixture_id"]: f["sensor_id"] for f in self.fixture_info}
        self.is_initialized: bool = False

    @classmethod
    def get_instance(cls) -> "DetectionService":
        if cls._instance is None:
            cls._instance = DetectionService()
        return cls._instance

    async def initialize(self, db_session: Optional[AsyncSession] = None) -> None:
        """
        Load baseline profiles from DB if available; fall back to prewarm JSON file.
        Initialize stateful DetectionEngine.
        """
        from app.models.models import BaselineProfile as DBBaselineProfile, Fixture as DBFixture, Zone as DBZone

        profiles: dict[str, BaselineProfile] = {}

        if db_session is not None:
            try:
                stmt = select(DBBaselineProfile, DBFixture.fixture_type, DBZone.criticality_tier)\
                    .join(DBFixture, DBBaselineProfile.fixture_id == DBFixture.fixture_id)\
                    .join(DBZone, DBFixture.zone_id == DBZone.zone_id)
                res = await db_session.execute(stmt)
                rows = res.all()

                if rows:
                    for db_bp, ftype, tier in rows:
                        fid = db_bp.fixture_id
                        profiles[fid] = BaselineProfile(
                            fixture_id=fid,
                            fixture_type=ftype,
                            zone_tier=tier,
                            mean_idle_flow=db_bp.mean_off_flow,
                            std_idle_flow=db_bp.std_off_flow,
                            sample_count=500 if db_bp.warmup_complete else 0,
                            ucl=db_bp.mean_off_flow + 3.0 * db_bp.std_off_flow,
                            initial_ewma=db_bp.mean_off_flow,
                            mean_flush_duration_s=db_bp.mean_flush_duration_s,
                            std_flush_duration_s=2.0,
                            warmup_complete=db_bp.warmup_complete,
                            warmup_started_at=db_bp.warmup_started_at.isoformat() if db_bp.warmup_started_at else None,
                        )
                    print(f"🏥 DetectionService: Loaded {len(profiles)} baseline profiles from PostgreSQL database.")
            except Exception as e:
                print(f"⚠️ DetectionService: Could not query DB baselines ({e}). Falling back to JSON.")

        if not profiles:
            if PREWARM_BASELINES_PATH.exists():
                profiles = load_baselines(PREWARM_BASELINES_PATH)
                print(f"🏥 DetectionService: Loaded {len(profiles)} baseline profiles from {PREWARM_BASELINES_PATH.name}.")
            else:
                print("⚠️ DetectionService: No prewarm JSON baselines found. Initialized with un-warmed defaults.")
                for f in self.fixture_info:
                    fid = f["fixture_id"]
                    profiles[fid] = BaselineProfile(
                        fixture_id=fid,
                        fixture_type=f["fixture_type"],
                        zone_tier=f["zone_tier"],
                        mean_idle_flow=0.0,
                        std_idle_flow=0.025,
                        sample_count=0,
                        ucl=0.075,
                        initial_ewma=0.0,
                        warmup_complete=False,
                    )

        self.baselines = profiles
        self.engine = DetectionEngine(baseline_profiles=profiles, fixture_info=self.fixture_info)
        self.is_initialized = True

    def process_reading(self, reading: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Process one reading dict.
        Resolves fixture_id from sensor_id if missing, and vice versa.
        Returns list of resulting event dicts.
        """
        if not self.is_initialized or self.engine is None:
            self._initialize_sync_fallback()

        # Ensure fixture_id is populated
        if "fixture_id" not in reading or not reading["fixture_id"]:
            sid = reading.get("sensor_id", "")
            reading["fixture_id"] = self.sensor_to_fixture.get(sid, sid)

        # Ensure sensor_id is populated
        if "sensor_id" not in reading or not reading["sensor_id"]:
            fid = reading.get("fixture_id", "")
            reading["sensor_id"] = self.fixture_to_sensor.get(fid, fid)

        return self.engine.process_reading(reading)

    def _initialize_sync_fallback(self) -> None:
        """Sync initialization fallback if called outside FastAPI lifespan."""
        if PREWARM_BASELINES_PATH.exists():
            profiles = load_baselines(PREWARM_BASELINES_PATH)
        else:
            profiles = {}
            for f in self.fixture_info:
                fid = f["fixture_id"]
                profiles[fid] = BaselineProfile(
                    fixture_id=fid,
                    fixture_type=f["fixture_type"],
                    zone_tier=f["zone_tier"],
                    mean_idle_flow=0.0,
                    std_idle_flow=0.025,
                    sample_count=0,
                    ucl=0.075,
                    initial_ewma=0.0,
                    warmup_complete=False,
                )
        self.baselines = profiles
        self.engine = DetectionEngine(baseline_profiles=profiles, fixture_info=self.fixture_info)
        self.is_initialized = True


detection_service = DetectionService.get_instance()
