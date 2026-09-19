"""
detection/tests/test_gradual_leak_trend.py — Tests for the TrendDetector and baseline protection.

Validates:
(a) Genuine slow-ramp leak scenario that existing EWMA/UCL detector misses (e.g. fix-ot-001 with UCL=7.23 LPM),
    confirming the new TrendDetector catches it.
(b) Normal slowly-varying legitimate usage pattern that must NOT trigger a false warning.
(c) Baseline freeze protection: confirms EWMA baseline stops adapting once suspicious trend is flagged.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from detection.baseline import BaselineProfile
from detection.engine import DetectionEngine
from detection.trend_detector import TrendDetector


def _make_reading(fixture_id: str, ts: datetime, flow: float, occ: int = 0, flush: int = 0, diag: str = "ok") -> dict:
    return {
        "fixture_id": fixture_id,
        "sensor_id": f"sen-{fixture_id}",
        "timestamp": ts.isoformat(),
        "flow_rate_lpm": flow,
        "occupancy_state": occ,
        "flush_event": flush,
        "diagnostic_status": diag,
    }


def test_genuine_slow_ramp_leak_detected_by_trend_detector():
    """
    Scenario (a): A scrub-tap fixture where mean_idle_flow=0.80, std=2.14, UCL=7.23 LPM.
    A slow ramp leak climbs from 0.0 to 0.50 LPM over 90 minutes.
    - Pure EWMA/UCL will NEVER exceed UCL (7.23 LPM), causing a False Negative.
    - TrendDetector detects the positive regression slope and delta, dispatching gradual_leak_warning and confirmed leak.
    """
    fixture_id = "fix-ot-test-001"
    start_ts = datetime(2026, 9, 16, 7, 30, tzinfo=timezone.utc)

    bp = BaselineProfile(
        fixture_id=fixture_id,
        fixture_type="scrub_tap",
        zone_tier="Tier 1",
        mean_idle_flow=0.80,
        std_idle_flow=2.14,
        sample_count=20000,
        ucl=7.23,
        initial_ewma=0.01,
        mean_flush_duration_s=10.0,
        std_flush_duration_s=2.0,
        warmup_complete=True,
    )

    engine = DetectionEngine(
        baseline_profiles={fixture_id: bp},
        fixture_info=[{
            "fixture_id": fixture_id,
            "sensor_id": f"sen-{fixture_id}",
            "fixture_type": "scrub_tap",
            "zone_tier": "Tier 1",
        }],
    )

    all_events = []
    # 1. 30 minutes of clean baseline (07:30 to 08:00): idle flow ~0.01 LPM
    current_ts = start_ts
    for _ in range(60):  # 30 min at 30s intervals
        rd = _make_reading(fixture_id, current_ts, flow=0.01)
        all_events.extend(engine.process_reading(rd))
        current_ts += timedelta(seconds=30)

    # 2. 90 minutes of gradual leak ramp (08:00 to 09:30): flow ramps from 0.01 to 0.50 LPM
    ramp_steps = 180  # 90 min at 30s intervals
    for step in range(ramp_steps):
        flow = 0.01 + (0.50 - 0.01) * (step / ramp_steps)
        rd = _make_reading(fixture_id, current_ts, flow=flow)
        all_events.extend(engine.process_reading(rd))
        current_ts += timedelta(seconds=30)

    # Verify existing EWMA never breached UCL (UCL = 7.23, max flow was 0.50)
    state = engine._states[fixture_id]
    assert state.ewma < bp.ucl, f"EWMA {state.ewma} should remain well below UCL {bp.ucl}"

    # Verify TrendDetector caught it
    warning_events = [e for e in all_events if e.get("event_type") == "gradual_leak_warning"]
    confirmed_leak_events = [e for e in all_events if e.get("event_type") == "leak" and e.get("sub_type") == "gradual_leak"]

    assert len(warning_events) >= 1, "TrendDetector should have dispatched at least one gradual_leak_warning"
    assert len(confirmed_leak_events) >= 1, "TrendDetector should have escalated to a confirmed leak event"

    first_warn = warning_events[0]
    assert first_warn["status"] == "dispatched"
    assert first_warn["confidence_score"] == 0.75
    assert first_warn["evidence_value"] > 0.0

    first_leak = confirmed_leak_events[0]
    assert first_leak["status"] == "dispatched"
    assert first_leak["confidence_score"] == 0.88


def test_normal_usage_no_false_warning():
    """
    Scenario (b): Normal legitimate fixture operation with small random sensor noise (0.01 +/- 0.01 LPM)
    and intermittent legitimate uses (6.5 LPM scrubs with occupancy/active flow).
    Must NOT trigger any gradual_leak_warning or false leak events.
    """
    fixture_id = "fix-ot-normal-001"
    start_ts = datetime(2026, 9, 16, 7, 30, tzinfo=timezone.utc)

    bp = BaselineProfile(
        fixture_id=fixture_id,
        fixture_type="scrub_tap",
        zone_tier="Tier 1",
        mean_idle_flow=0.80,
        std_idle_flow=2.14,
        sample_count=20000,
        ucl=7.23,
        initial_ewma=0.01,
        mean_flush_duration_s=10.0,
        std_flush_duration_s=2.0,
        warmup_complete=True,
    )

    engine = DetectionEngine(
        baseline_profiles={fixture_id: bp},
        fixture_info=[{
            "fixture_id": fixture_id,
            "sensor_id": f"sen-{fixture_id}",
            "fixture_type": "scrub_tap",
            "zone_tier": "Tier 1",
        }],
    )

    all_events = []
    current_ts = start_ts
    # 2 hours of normal operation: idle noise between 0.00 and 0.02 LPM, plus occasional scrubs
    import random
    rng = random.Random(42)

    for i in range(240):  # 120 minutes
        # Every 30 minutes, simulate a 3-minute scrub draw (6.5 LPM)
        if 40 <= (i % 60) <= 46:
            flow = 6.5 + rng.gauss(0, 0.2)
        else:
            flow = max(0.0, 0.01 + rng.gauss(0, 0.005))

        rd = _make_reading(fixture_id, current_ts, flow=flow)
        all_events.extend(engine.process_reading(rd))
        current_ts += timedelta(seconds=30)

    # Must produce ZERO leak or warning events
    leak_or_warn_events = [e for e in all_events if e.get("event_type") in ("leak", "gradual_leak_warning")]
    assert len(leak_or_warn_events) == 0, f"Expected 0 false alarms, got {len(leak_or_warn_events)}: {leak_or_warn_events}"


def test_baseline_freeze_prevents_leak_absorption():
    """
    Scenario (c): Confirms that once is_suspicious=True is flagged by the TrendDetector,
    state.ewma stops absorbing the creeping leak flow.
    """
    fixture_id = "fix-ward-freeze-001"
    start_ts = datetime(2026, 9, 15, 13, 0, tzinfo=timezone.utc)

    bp = BaselineProfile(
        fixture_id=fixture_id,
        fixture_type="faucet",
        zone_tier="Tier 2",
        mean_idle_flow=0.02,
        std_idle_flow=0.01,
        sample_count=20000,
        ucl=0.05,
        initial_ewma=0.02,
        mean_flush_duration_s=10.0,
        std_flush_duration_s=2.0,
        warmup_complete=True,
    )

    engine = DetectionEngine(
        baseline_profiles={fixture_id: bp},
        fixture_info=[{
            "fixture_id": fixture_id,
            "sensor_id": f"sen-{fixture_id}",
            "fixture_type": "faucet",
            "zone_tier": "Tier 2",
        }],
    )

    current_ts = start_ts
    # 40 min normal idle at 0.02 LPM
    for _ in range(80):
        rd = _make_reading(fixture_id, current_ts, flow=0.02)
        engine.process_reading(rd)
        current_ts += timedelta(seconds=30)

    pre_leak_ewma = engine._states[fixture_id].ewma
    trend_det = engine._trend_detectors[fixture_id]

    # Ramp flow from 0.02 to 0.40 LPM over 60 min
    frozen_ewma_snapshots = []
    for step in range(120):
        flow = 0.02 + (0.40 - 0.02) * (step / 120.0)
        rd = _make_reading(fixture_id, current_ts, flow=flow)
        engine.process_reading(rd)
        current_ts += timedelta(seconds=30)

        if trend_det.is_suspicious:
            frozen_ewma_snapshots.append(engine._states[fixture_id].ewma)

    assert len(frozen_ewma_snapshots) > 0, "TrendDetector should have entered is_suspicious=True"
    # Verify that while suspicious, the EWMA value remained frozen (identical across snapshots)
    assert frozen_ewma_snapshots[0] == frozen_ewma_snapshots[-1], (
        f"EWMA changed during suspicious state! Start: {frozen_ewma_snapshots[0]}, End: {frozen_ewma_snapshots[-1]}"
    )
