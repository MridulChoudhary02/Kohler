"""
detection/tests/test_ordinary_flushes.py — Ordinary-flush no-false-positive validation.

Validates that normal flush events (spike + decay back to baseline within normal window)
do NOT trigger any false positive leak detection events, either via Signal 1 EWMA
or via Section 7.4 stuck-valve check.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from detection.baseline import BaselineProfile, learn_baselines
from detection.engine import DetectionEngine
from scripts.seed_data import SEED


def _fixture_info():
    zone_map   = {z["zone_id"]: z["criticality_tier"] for z in SEED["zones"]}
    sensor_map = {s["fixture_id"]: s["sensor_id"] for s in SEED["sensors"]}
    return [
        {
            "fixture_id":   fx["fixture_id"],
            "sensor_id":    sensor_map[fx["fixture_id"]],
            "fixture_type": fx["fixture_type"],
            "zone_tier":    zone_map[fx["zone_id"]],
        }
        for fx in SEED["fixtures"]
    ]


def test_ordinary_flushes_produce_no_false_positives(prewarm_jsonl_path: Path) -> dict:
    """
    Run DetectionEngine over clean telemetry containing thousands of ordinary flushes.
    Assert zero dispatched or logged leak events.
    """
    info = _fixture_info()
    baselines = learn_baselines(prewarm_jsonl_path, info, quiet=True)

    engine = DetectionEngine(baseline_profiles=baselines, fixture_info=info)

    all_events = []
    flush_count = 0
    with open(prewarm_jsonl_path) as f:
        for line in f:
            r = json.loads(line)
            if r.get("flush_event") == 1:
                flush_count += 1
            events = engine.process_reading(r)
            all_events.extend(events)

    leak_events = [e for e in all_events if e["event_type"] == "leak"]

    assert len(leak_events) == 0, f"Expected 0 leak events from ordinary flushes, got {len(leak_events)}"
    return {
        "ordinary_flushes_tested": flush_count,
        "false_positive_leak_events": len(leak_events),
        "status": "PASSED (0 false positives)",
    }
