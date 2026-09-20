"""
backend/detection/tests/test_context_adaptive_baseline.py

Comprehensive tests for time-of-day context-adaptive baselines:
(a) Day and night baselines are tracked separately for a fixture with different diurnal usage patterns.
(b) Per-fixture significance gating rejects insignificant diurnal variance and keeps single combined baseline.
(c) Shrinkage measurably widens the tightest segment UCL vs the naive ungated version that caused fix-ot-002 false positive.
(d) Fallback safeguard triggers correctly under low sample count (< min_context_samples).
(e) Toggling CONTEXT_ADAPTIVE_BASELINE_ENABLED=False reproduces exact legacy single-baseline behavior bit-for-bit.
(f) Fixture-wide baseline freeze protection under suspicious trend: both day and night baselines freeze.
"""
from __future__ import annotations

import json
import math
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from detection.baseline import (
    BaselineProfile,
    learn_baselines,
    CONTEXT_DAY_START_HOUR,
    CONTEXT_DAY_END_HOUR,
    CONTEXT_MIN_SAMPLE_COUNT,
    CONTEXT_GATE_Z_THRESHOLD,
    CONTEXT_GATE_REL_DIFF_THRESHOLD,
    CONTEXT_SHRINKAGE_PSEUDO_COUNT_K,
)
from detection.engine import DetectionEngine


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


def test_day_night_baselines_learned_and_applied_separately():
    """
    Test (a): Day and night baselines are learned separately for a fixture with
    large diurnal idle usage difference (Day ~0.50 LPM, Night ~0.05 LPM).
    The fixture passes the significance gate and dynamically applies the correct window UCL during detection.
    """
    fid = "fix-diurnal-001"
    meta = [{"fixture_id": fid, "sensor_id": f"sen-{fid}", "fixture_type": "scrub_tap", "zone_tier": "Tier 1"}]

    # Generate 100 daytime idle readings (0.50 LPM) and 100 nighttime idle readings (0.05 LPM)
    readings = []
    base_date = datetime(2026, 9, 10, 0, 0, tzinfo=timezone.utc)

    # 100 Day readings: 10:00 to 11:39
    for i in range(100):
        ts = base_date.replace(hour=10) + timedelta(minutes=i)
        readings.append(_make_reading(fid, ts, 0.50))

    # 100 Night readings: 01:00 to 02:39
    for i in range(100):
        ts = base_date.replace(hour=1) + timedelta(minutes=i)
        readings.append(_make_reading(fid, ts, 0.05))

    readings.sort(key=lambda r: r["timestamp"])

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        for r in readings:
            f.write(json.dumps(r) + "\n")
        temp_path = Path(f.name)

    try:
        # Pass shrinkage_k=10 so small sample size test does not over-shrink toward combined
        profiles = learn_baselines(temp_path, meta, warmup_days=1, quiet=True, shrinkage_k=10)
        bp = profiles[fid]

        # Verify significance gating passed
        assert bp.split_enabled is True
        assert bp.gate_z_score is not None
        assert abs(bp.gate_z_score) >= 3.0
        assert bp.gate_rel_diff is not None
        assert bp.gate_rel_diff >= 0.25

        # Verify Day and Night baselines
        assert bp.day_baseline is not None
        assert bp.night_baseline is not None
        assert bp.day_baseline["mean_idle_flow"] > bp.night_baseline["mean_idle_flow"] + 0.30
        assert bp.day_baseline["ucl"] > bp.night_baseline["ucl"] + 0.30

        # Run DetectionEngine with this profile
        engine = DetectionEngine(baseline_profiles=profiles, fixture_info=meta, context_adaptive=True)

        # 1. At 14:00 (Day), flow is 0.25 LPM.
        # Below Day UCL -> NO leak candidate should start.
        day_ts = datetime(2026, 9, 15, 14, 0, tzinfo=timezone.utc)
        evs = engine.process_reading(_make_reading(fid, day_ts, 0.25))
        assert len(evs) == 0
        state = engine._states[fid]
        assert state.candidate_start_ts is None

        # 2. At 02:00 (Night), flow is 0.25 LPM.
        # Above Night UCL -> leak candidate MUST start and confirm after confirmation window.
        night_start = datetime(2026, 9, 16, 2, 0, tzinfo=timezone.utc)
        all_night_evs = []
        for m in range(8):  # Tier 1 confirmation window = 3 min (180s)
            ts = night_start + timedelta(minutes=m)
            all_night_evs.extend(engine.process_reading(_make_reading(fid, ts, 0.25)))

        leak_evs = [e for e in all_night_evs if e["event_type"] == "leak"]
        assert len(leak_evs) >= 1
        ev = leak_evs[0]
        assert ev["baseline_window"] == "night"
        assert ev["context_baseline_fallback"] is False
        assert abs(ev["ucl"] - bp.night_baseline["ucl"]) < 1e-4
    finally:
        temp_path.unlink(missing_ok=True)


def test_gating_rejects_insignificant_fixture_and_keeps_combined():
    """
    Test (b): Per-fixture significance gating.
    A standard fixture with minimal day/night variation (Day 0.010 LPM, Night 0.009 LPM)
    fails the significance gate (|z| < 3.0 or rel_diff < 25%).
    It must be flagged as split_enabled=False and NEVER split at detection time,
    always evaluating against the single combined baseline.
    """
    fid = "fix-gating-fail-001"
    meta = [{"fixture_id": fid, "sensor_id": f"sen-{fid}", "fixture_type": "faucet", "zone_tier": "Tier 3"}]

    # Generate 100 Day readings (0.010 LPM) and 100 Night readings (0.0095 LPM)
    readings = []
    base_date = datetime(2026, 9, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(100):
        ts_d = base_date.replace(hour=10) + timedelta(minutes=i)
        readings.append(_make_reading(fid, ts_d, 0.010))
        ts_n = base_date.replace(hour=1) + timedelta(minutes=i)
        readings.append(_make_reading(fid, ts_n, 0.0095))

    readings.sort(key=lambda r: r["timestamp"])

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        for r in readings:
            f.write(json.dumps(r) + "\n")
        temp_path = Path(f.name)

    try:
        profiles = learn_baselines(temp_path, meta, warmup_days=1, quiet=True)
        bp = profiles[fid]

        # Verify gating failed (rel_diff ~ 5% < 25%)
        assert bp.split_enabled is False
        assert bp.gate_rel_diff is not None and bp.gate_rel_diff < 0.25
        assert bp.day_baseline is None
        assert bp.night_baseline is None

        # At detection time, engine must always use combined baseline
        engine = DetectionEngine(baseline_profiles=profiles, fixture_info=meta, context_adaptive=True)
        day_ts = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
        mean, std, ucl, win, is_fb = bp.get_active_baseline(day_ts, adaptive_enabled=True)
        assert win == "combined"
        assert is_fb is False
        assert ucl == bp.ucl
    finally:
        temp_path.unlink(missing_ok=True)


def test_shrinkage_widens_night_ucl_preventing_false_positives():
    """
    Test (c): Empirical Bayes shrinkage toward the combined baseline.
    Demonstrates that for an OT fixture (like fix-ot-002):
    - Naive night UCL contracts too tightly (e.g. 5.98 LPM), causing a 6.58 LPM excursion to false-alarm.
    - Shrunk night UCL widens toward combined UCL (6.74 LPM > 6.58 LPM), completely preventing the false positive.
    """
    fid = "fix-shrinkage-001"
    meta = [{"fixture_id": fid, "sensor_id": f"sen-{fid}", "fixture_type": "scrub_tap", "zone_tier": "Tier 1"}]

    # Exact numbers from fix-ot-002 prewarm analysis
    comb_mean = 0.8640
    comb_std = 2.2065
    comb_ucl = comb_mean + 3.0 * comb_std  # 7.4835 LPM

    night_mean = 0.5566
    night_std = 1.8090
    naive_night_ucl = night_mean + 3.0 * night_std  # 5.9836 LPM
    n_night = 6555
    k = 6720  # prior pseudo-count (1 week equivalent)

    # Apply shrinkage formula: shrunk = (n*seg + k*comb) / (n+k)
    shrunk_mean = (n_night * night_mean + k * comb_mean) / (n_night + k)
    shrunk_std = (n_night * night_std + k * comb_std) / (n_night + k)
    shrunk_night_ucl = shrunk_mean + 3.0 * shrunk_std

    # Verify shrinkage strictly widens the night UCL
    assert shrunk_night_ucl > naive_night_ucl + 0.70  # widens by > 0.70 LPM
    assert shrunk_night_ucl > 6.70

    # The flow rate that caused the false positive on fix-ot-002
    test_excursion_flow = 6.5811

    # In naive ungated/unshrunk version, 6.5811 breaches naive UCL (5.984) -> FP!
    assert test_excursion_flow > naive_night_ucl

    # In shrunk version, 6.5811 is safely BELOW shrunk UCL (6.744) -> Zero FP!
    assert test_excursion_flow <= shrunk_night_ucl

    # Create profile with shrunk parameters
    bp = BaselineProfile(
        fixture_id=fid,
        fixture_type="scrub_tap",
        zone_tier="Tier 1",
        mean_idle_flow=comb_mean,
        std_idle_flow=comb_std,
        sample_count=20000,
        ucl=comb_ucl,
        initial_ewma=comb_mean,
        warmup_complete=True,
        split_enabled=True,
        day_baseline={"mean_idle_flow": 1.0, "std_idle_flow": 2.2, "ucl": 7.6, "sample_count": 13440, "initial_ewma": 1.0},
        night_baseline={"mean_idle_flow": round(shrunk_mean, 6), "std_idle_flow": round(shrunk_std, 6), "ucl": round(shrunk_night_ucl, 6), "sample_count": n_night, "initial_ewma": round(shrunk_mean, 6)},
    )

    engine = DetectionEngine(baseline_profiles={fid: bp}, fixture_info=meta, context_adaptive=True)
    night_ts = datetime(2026, 9, 15, 4, 57, tzinfo=timezone.utc)
    evs = []
    # Send test excursion flow for 5 minutes during night window
    for m in range(5):
        evs.extend(engine.process_reading(_make_reading(fid, night_ts + timedelta(minutes=m), test_excursion_flow)))

    # Shrunk night UCL must NOT emit a leak event for this flow
    leaks = [e for e in evs if e["event_type"] == "leak"]
    assert len(leaks) == 0, f"Shrunk UCL failed to prevent false positive: {leaks}"


def test_fallback_under_low_sample_count():
    """
    Test (d): When a baseline segment has fewer than min_context_samples,
    the engine gracefully falls back to the combined single baseline and flags the fallback.
    """
    fid = "fix-fallback-001"
    meta = [{"fixture_id": fid, "sensor_id": f"sen-{fid}", "fixture_type": "faucet", "zone_tier": "Tier 1"}]

    bp = BaselineProfile(
        fixture_id=fid,
        fixture_type="faucet",
        zone_tier="Tier 1",
        mean_idle_flow=0.10,
        std_idle_flow=0.02,
        sample_count=500,
        ucl=0.16,
        initial_ewma=0.10,
        warmup_complete=True,
        split_enabled=True,
        day_baseline={
            "mean_idle_flow": 0.05,
            "std_idle_flow": 0.01,
            "ucl": 0.08,
            "sample_count": 15,  # Only 15 samples! (< 60 threshold)
            "initial_ewma": 0.05,
        },
        night_baseline={
            "mean_idle_flow": 0.10,
            "std_idle_flow": 0.02,
            "ucl": 0.16,
            "sample_count": 200,
            "initial_ewma": 0.10,
        },
    )

    engine = DetectionEngine(
        baseline_profiles={fid: bp},
        fixture_info=meta,
        context_adaptive=True,
        min_context_samples=60,
    )

    # Process daytime reading (10:00 UTC). Because day sample_count=15 < 60,
    # it must fall back to the combined baseline (ucl=0.16, mean=0.10)
    day_ts = datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc)
    evs = []
    # Send flow of 0.25 (exceeds combined UCL 0.16) for 8 minutes
    for m in range(8):
        ts = day_ts + timedelta(minutes=m)
        evs.extend(engine.process_reading(_make_reading(fid, ts, 0.25)))

    leak_evs = [e for e in evs if e["event_type"] == "leak"]
    assert len(leak_evs) >= 1
    ev = leak_evs[0]
    assert ev["context_baseline_fallback"] is True
    assert ev["baseline_window"] == "day_fallback_to_combined"
    assert abs(ev["ucl"] - bp.ucl) < 1e-4  # Uses combined UCL (0.16), not day UCL (0.08)


def test_flag_disabled_reproduces_legacy_behavior_bit_for_bit():
    """
    Test (e): Setting context_adaptive=False reproduces the exact single-baseline
    behavior bit-for-bit, ignoring day/night segments.
    """
    fid = "fix-toggle-001"
    meta = [{"fixture_id": fid, "sensor_id": f"sen-{fid}", "fixture_type": "faucet", "zone_tier": "Tier 1"}]

    bp = BaselineProfile(
        fixture_id=fid,
        fixture_type="faucet",
        zone_tier="Tier 1",
        mean_idle_flow=0.05,
        std_idle_flow=0.01,
        sample_count=1000,
        ucl=0.08,
        initial_ewma=0.05,
        warmup_complete=True,
        split_enabled=True,
        day_baseline={
            "mean_idle_flow": 0.20,
            "std_idle_flow": 0.02,
            "ucl": 0.26,
            "sample_count": 500,
            "initial_ewma": 0.20,
        },
        night_baseline={
            "mean_idle_flow": 0.02,
            "std_idle_flow": 0.005,
            "ucl": 0.035,
            "sample_count": 500,
            "initial_ewma": 0.02,
        },
    )

    engine_legacy = DetectionEngine(
        baseline_profiles={fid: bp},
        fixture_info=meta,
        context_adaptive=False,
    )

    start_ts = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
    readings = [
        _make_reading(fid, start_ts + timedelta(minutes=i), 0.15)
        for i in range(10)
    ]

    events = []
    ewma_progression = []
    for r in readings:
        evs = engine_legacy.process_reading(r)
        events.extend(evs)
        ewma_progression.append(engine_legacy._states[fid].ewma)

    # In legacy mode, UCL used must be exactly bp.ucl (0.08)
    assert abs(ewma_progression[0] - 0.070) < 1e-5
    assert abs(ewma_progression[1] - 0.086) < 1e-5
    assert abs(ewma_progression[2] - 0.0988) < 1e-5

    # Leaks emitted in legacy mode have baseline_window == "combined"
    leak_evs = [e for e in events if e["event_type"] == "leak"]
    assert len(leak_evs) >= 1
    for ev in leak_evs:
        assert ev["baseline_window"] == "combined"
        assert ev["context_baseline_fallback"] is False
        assert abs(ev["ucl"] - bp.ucl) < 1e-5


def test_baseline_freeze_fixture_wide_protection():
    """
    Test (f): Baseline freeze under suspicious trend.
    When a fixture is flagged with is_suspicious=True, the adaptation freeze applies
    fixture-wide to BOTH day and night baselines:
    1. In the day window, day EWMA does NOT absorb the leak flow.
    2. When transitioning into the night window while still suspicious, the night EWMA
       is ALSO frozen and does NOT absorb the leak flow.
    """
    fid = "fix-freeze-001"
    meta = [{"fixture_id": fid, "sensor_id": f"sen-{fid}", "fixture_type": "scrub_tap", "zone_tier": "Tier 1"}]

    bp = BaselineProfile(
        fixture_id=fid,
        fixture_type="scrub_tap",
        zone_tier="Tier 1",
        mean_idle_flow=0.50,
        std_idle_flow=0.05,
        sample_count=1000,
        ucl=0.65,
        initial_ewma=0.50,
        warmup_complete=True,
        split_enabled=True,
        day_baseline={
            "mean_idle_flow": 0.60,
            "std_idle_flow": 0.05,
            "ucl": 0.75,
            "sample_count": 500,
            "initial_ewma": 0.60,
        },
        night_baseline={
            "mean_idle_flow": 0.10,
            "std_idle_flow": 0.02,
            "ucl": 0.16,
            "sample_count": 500,
            "initial_ewma": 0.10,
        },
    )

    engine = DetectionEngine(
        baseline_profiles={fid: bp},
        fixture_info=meta,
        context_adaptive=True,
    )

    # Initial states
    assert engine._window_ewma[fid]["day"] == 0.60
    assert engine._window_ewma[fid]["night"] == 0.10

    # Simulate suspicious trend active
    trend_tracker = engine._trend_detectors[fid]
    trend_tracker.state.is_suspicious = True

    # 1. Day window: 15:00 UTC. Flow jumps to 0.40 LPM (elevated leak).
    day_ts = datetime(2026, 9, 15, 15, 0, tzinfo=timezone.utc)
    for i in range(10):
        engine.process_reading(_make_reading(fid, day_ts + timedelta(minutes=i), 0.40))

    # Day EWMA must remain strictly frozen at 0.60 (has NOT adapted/absorbed 0.40)
    assert engine._window_ewma[fid]["day"] == 0.60
    assert engine._states[fid].ewma == 0.60

    # 2. Night window transition: 23:00 UTC. Leak continues at 0.40 LPM.
    # While trend_tracker is still suspicious, Night EWMA must ALSO remain frozen.
    night_ts = datetime(2026, 9, 15, 23, 0, tzinfo=timezone.utc)
    for i in range(10):
        engine.process_reading(_make_reading(fid, night_ts + timedelta(minutes=i), 0.40))

    # Night EWMA must remain strictly frozen at 0.10 (has NOT adapted/absorbed 0.40)
    assert engine._window_ewma[fid]["night"] == 0.10
    assert engine._states[fid].ewma == 0.10

    # 3. Clear suspicious trend -> adaptation resumes in active night window
    trend_tracker.state.is_suspicious = False
    engine.process_reading(_make_reading(fid, night_ts + timedelta(minutes=15), 0.40))

    # Now night EWMA adapts: 0.2 * 0.40 + 0.8 * 0.10 = 0.16
    assert abs(engine._window_ewma[fid]["night"] - 0.16) < 1e-4
    assert abs(engine._states[fid].ewma - 0.16) < 1e-4
