"""
detection/tests/test_hygiene.py — Unit test for PRD Section 8 hygiene threshold prediction.

Tests:
  - test_hygiene_prediction_fires_before_threshold:
      Simulates a traffic burst on a fixture (high use rate), asserts that a predictive_hygiene
      ticket event fires with minutes_to_breach <= lead_time_minutes BEFORE uses_since_clean
      crosses the static cleaning threshold.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from detection.hygiene import HygieneTracker, HYGIENE_THRESHOLDS, HYGIENE_LEAD_TIMES


FIXTURE = {
    "fixture_id":   "fix-hyg-test-001",
    "sensor_id":    "sen-hyg-test-001",
    "fixture_type": "flush_valve",
    "zone_tier":    "Tier 1",
    "zone_id":      "zone-icu",
}


def test_hygiene_prediction_fires_before_threshold():
    """
    Simulate rapid traffic burst (1 use every 2 minutes for 30 minutes = 15 uses in 30 min).
    Static threshold for Tier 1 = 20 uses.
    Lead time target for Tier 1 = 15 minutes.
    Assert predictive hygiene ticket fires at/before ~12-14 uses (when minutes_to_breach <= 15 min),
    BEFORE uses_since_clean reaches 20.
    """
    tracker = HygieneTracker(fixture_id=FIXTURE["fixture_id"], zone_tier=FIXTURE["zone_tier"])
    start_ts = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)

    predictive_event = None
    fired_at_uses = None

    # Simulate 1 use every 2 minutes (30 readings, 15 uses)
    for minute in range(30):
        ts = start_ts + timedelta(minutes=minute)
        # Flush every 2 minutes
        flush_flag = 1 if (minute % 2 == 0) else 0

        reading = {
            "fixture_id": FIXTURE["fixture_id"],
            "sensor_id": FIXTURE["sensor_id"],
            "timestamp": ts.isoformat(),
            "flow_rate_lpm": 6.0 if flush_flag else 0.0,
            "occupancy_state": 0,
            "flush_event": flush_flag,
            "diagnostic_status": "ok",
        }

        evt = tracker.process_reading(reading, warmup_complete=True)
        if evt and predictive_event is None:
            predictive_event = evt
            fired_at_uses = tracker.state.uses_since_clean

    # Assertions
    assert predictive_event is not None, "Predictive hygiene ticket must fire during traffic burst"
    assert predictive_event["event_type"] == "hygiene"
    assert predictive_event["sub_type"] == "predictive_hygiene"
    assert predictive_event["minutes_to_breach"] <= HYGIENE_LEAD_TIMES["Tier 1"], (
        f"minutes_to_breach ({predictive_event['minutes_to_breach']}) must be <= lead time target ({HYGIENE_LEAD_TIMES['Tier 1']})"
    )
    assert fired_at_uses < HYGIENE_THRESHOLDS["Tier 1"], (
        f"Predictive ticket fired at {fired_at_uses} uses, which must be BEFORE static threshold ({HYGIENE_THRESHOLDS['Tier 1']})"
    )


if __name__ == "__main__":
    test_hygiene_prediction_fires_before_threshold()
    print("✅ test_hygiene_prediction_fires_before_threshold PASSED")
