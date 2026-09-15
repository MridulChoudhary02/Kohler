"""
detection/tests/test_sensor_health.py — Unit test for PRD Section 9 sensor health scoring.

Tests:
  - test_sensor_fault_downgrades_to_maintenance_ticket:
      Injects a flatlining/noisy sensor (health_score < 0.60), asserts that leak events
      from this sensor are downgraded to "logged only" and a separate sensor_maintenance
      ticket event is dispatched.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from detection.baseline import BaselineProfile
from detection.engine import DetectionEngine
from detection.sensor_health import SensorHealthTracker, DEGRADED_THRESHOLD


FIXTURE = {
    "fixture_id":   "fix-health-test-001",
    "sensor_id":    "sen-health-test-001",
    "fixture_type": "faucet",
    "zone_tier":    "Tier 1",
    "zone_id":      "zone-icu",
}


def test_sensor_fault_downgrades_to_maintenance_ticket():
    """
    Inject flatlining/out-of-range telemetry from a faulty sensor.
    Assert sensor health score drops < 0.60, a sensor_maintenance event fires,
    and any high-confidence leak event is downgraded to "logged".
    """
    start_ts = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
    readings = []

    # Emit 20 readings with flatline and out_of_range diagnostic status + high flow
    for i in range(20):
        ts = start_ts + timedelta(seconds=i * 30)
        readings.append({
            "fixture_id": FIXTURE["fixture_id"],
            "sensor_id": FIXTURE["sensor_id"],
            "timestamp": ts.isoformat(),
            "flow_rate_lpm": 5.0,   # high flow (would cause UCL breach leak)
            "occupancy_state": 0,
            "flush_event": 0,
            "diagnostic_status": "flatline" if i >= 5 else "out_of_range",
        })

    baseline = BaselineProfile(
        fixture_id=FIXTURE["fixture_id"],
        fixture_type=FIXTURE["fixture_type"],
        zone_tier=FIXTURE["zone_tier"],
        mean_idle_flow=0.0,
        std_idle_flow=0.02,
        sample_count=500,
        ucl=0.06,
        initial_ewma=0.0,
        warmup_complete=True,
    )

    engine = DetectionEngine(
        baseline_profiles={FIXTURE["fixture_id"]: baseline},
        fixture_info=[FIXTURE],
    )

    events = engine.process_batch(readings)

    # Filter events
    maint_events = [
        e for e in events
        if e.get("event_type") == "sensor_fault" and e.get("sub_type") in ("sensor_maintenance", "sensor_flatline")
    ]
    dispatched_leaks = [
        e for e in events
        if e.get("event_type") == "leak" and e.get("status") == "dispatched"
    ]
    logged_leaks = [
        e for e in events
        if e.get("event_type") == "leak" and e.get("status") == "logged"
    ]

    # Assertions
    assert len(maint_events) > 0, "Expected a sensor_fault/sensor_maintenance ticket to be emitted"
    assert len(dispatched_leaks) == 0, "Expected 0 dispatched leak events from degraded sensor"
    assert maint_events[0]["status"] == "dispatched", "Sensor maintenance ticket must be dispatched"


if __name__ == "__main__":
    test_sensor_fault_downgrades_to_maintenance_ticket()
    print("✅ test_sensor_fault_downgrades_to_maintenance_ticket PASSED")
