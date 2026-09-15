"""
detection/tests/test_warmup_suppression.py — Isolated warm-up suppression test.

Tests that a fixture with warmup_complete=False NEVER produces a status="dispatched"
detection event, even when a high-confidence anomaly is injected.

This test is FULLY ISOLATED from the main 3-day accuracy test set:
  - Uses its own single-fixture simulation
  - Its events are NEVER fed into match_detections_to_labels() for the main scoring
  - Results are reported separately

PRD §7.1: "During warm-up, detection events are logged only, never dispatched."
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulator.anomaly import AnomalySpec, AnomalyType
from simulator.engine import SimulatorEngine
from detection.baseline import BaselineProfile
from detection.engine import DetectionEngine


def run_warmup_suppression_test(quiet: bool = False) -> bool:
    """
    Inject a strong sudden_leak on a cold-start fixture (warmup_complete=False).
    Assert: zero dispatched events.

    Returns True if the test passes.
    """
    # ── Fixture definition (single ICU faucet) ────────────────────────────────
    FIXTURE = {
        "fixture_id":   "fix-suppress-test-001",
        "sensor_id":    "sen-suppress-test-001",
        "fixture_type": "faucet",
        "zone_tier":    "Tier 1",
        "zone_id":      "zone-icu",
    }

    # ── Simulate 2 hours: first 30 min normal, then 60 min sudden_leak ────────
    sim_start   = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
    anomaly_start = sim_start + timedelta(minutes=30)
    anomaly_end   = sim_start + timedelta(minutes=90)
    sim_end       = sim_start + timedelta(hours=2)

    anomaly_spec = AnomalySpec(
        anomaly_type  = AnomalyType.SUDDEN_LEAK,
        fixture_id    = FIXTURE["fixture_id"],
        sensor_id     = FIXTURE["sensor_id"],
        start_ts      = anomaly_start,
        end_ts        = anomaly_end,
        leak_flow_lpm = 2.0,   # 2 L/min — far above any UCL, maximum confidence
    )

    engine_sim = SimulatorEngine(
        fixtures      = [FIXTURE],
        anomaly_specs = [anomaly_spec],
        seed          = 777,
    )
    readings, labels, _, _ = engine_sim.run(sim_start, sim_end)

    if not quiet:
        print(f"  Simulated {len(readings)} readings, {len(labels)} label(s)")

    # ── Baseline with warmup_complete=False (cold start) ─────────────────────
    # Use a realistic baseline (mean=0, std=0.02) but WARMUP NOT DONE.
    cold_baseline = BaselineProfile(
        fixture_id          = FIXTURE["fixture_id"],
        fixture_type        = FIXTURE["fixture_type"],
        zone_tier           = FIXTURE["zone_tier"],
        mean_idle_flow      = 0.0,
        std_idle_flow       = 0.020,
        sample_count        = 50,    # some data collected but not enough days
        ucl                 = 0.0 + 3.0 * 0.020,     # = 0.06 L/min
        initial_ewma        = 0.0,
        warmup_complete     = False,   # ← THE KEY FLAG
        warmup_started_at   = "2026-09-01T07:00:00+00:00",
        warmup_completed_at = None,    # not yet complete
    )

    # ── Run detection engine ──────────────────────────────────────────────────
    det_engine = DetectionEngine(
        baseline_profiles = {FIXTURE["fixture_id"]: cold_baseline},
        fixture_info      = [FIXTURE],
    )
    events = det_engine.process_batch(readings)

    # ── Assertions ────────────────────────────────────────────────────────────
    dispatched = [e for e in events if e["status"] == "dispatched"]
    logged     = [e for e in events if e["status"] == "logged"]

    passed = True

    if not quiet:
        print(f"  Total events:    {len(events)}")
        print(f"  Dispatched:      {len(dispatched)}  ← must be 0")
        print(f"  Logged-only:     {len(logged)}")
        if events:
            print(f"  Sample event confidence: {events[0]['confidence_score']:.3f}")
            print(f"  Sample event warmup_complete: {events[0]['warmup_complete']}")

    assert len(dispatched) == 0, (
        f"FAIL: warm-up suppression broken — {len(dispatched)} dispatched events "
        f"on a fixture with warmup_complete=False. "
        f"Events: {dispatched}"
    )

    # Sanity: some logged events SHOULD exist (the anomaly IS detectable)
    assert len(logged) > 0, (
        "FAIL: no events at all — anomaly was not detected even at log level. "
        "Check EWMA/UCL logic."
    )

    if not quiet:
        print("  ✅ warmup_complete=False → 0 dispatched events (warm-up suppression works)")
        print(f"  ✅ {len(logged)} logged-only event(s) confirm anomaly IS detectable, just suppressed")

    return True


def main():
    print("=" * 60)
    print("ISOLATED TEST: warm-up suppression")
    print("=" * 60)
    passed = run_warmup_suppression_test(quiet=False)
    if passed:
        print()
        print("✅ Warm-up suppression test PASSED")
    else:
        print()
        print("❌ Warm-up suppression test FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
