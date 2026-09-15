"""
detection/runner.py — CLI harness: run detection on a JSONL file.

Usage:
    cd backend/
    # Run on combined 3-day test set:
    python -m detection.runner \\
        --telemetry simulator/output/test_set/combined_telemetry.jsonl \\
        --baselines simulator/output/prewarm/baseline_profiles.json \\
        --output    simulator/output/detection_events.jsonl

    # Run on a single day:
    python -m detection.runner \\
        --telemetry simulator/output/test_set/day1_telemetry.jsonl \\
        --baselines simulator/output/prewarm/baseline_profiles.json \\
        --output    simulator/output/day1_detection_events.jsonl

    # Score immediately after detection:
    python -m detection.runner ... --labels simulator/output/test_set/combined_anomaly_labels.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from detection.baseline import load_baselines
from detection.engine import DetectionEngine
from scripts.seed_data import SEED


# ─────────────────────────────────────────────────────────────────────────────
# Fixture info — single source of truth is seed_data.py
# ─────────────────────────────────────────────────────────────────────────────

def _build_fixture_list() -> list[dict[str, str]]:
    zone_map   = {z["zone_id"]: z["criticality_tier"] for z in SEED["zones"]}
    sensor_map = {s["fixture_id"]: s["sensor_id"]     for s in SEED["sensors"]}
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


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Kohler Phase 2 Detection Runner")
    p.add_argument("--telemetry", required=True,
                   help="Input JSONL file (readings sorted by timestamp)")
    p.add_argument("--baselines", required=True,
                   help="Baseline profiles JSON (from baseline learning)")
    p.add_argument("--output",    required=True,
                   help="Output JSONL for detection events")
    p.add_argument("--labels",    default=None,
                   help="(Optional) Ground-truth labels JSON — triggers scoring")
    p.add_argument("--quiet",     action="store_true")
    return p.parse_args()


def run(
    telemetry_path:  str | Path,
    baselines_path:  str | Path,
    output_path:     str | Path,
    labels_path:     str | Path | None = None,
    quiet:           bool = False,
) -> list[dict]:
    """
    Load baselines, run DetectionEngine on telemetry, write events, optionally score.
    Returns the list of detection_event dicts.
    """
    telemetry_path = Path(telemetry_path)
    baselines_path = Path(baselines_path)
    output_path    = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load baselines
    baselines = load_baselines(baselines_path)
    fixtures  = _build_fixture_list()

    if not quiet:
        warmed = sum(1 for bp in baselines.values() if bp.warmup_complete)
        print(f"🔍 Detection runner")
        print(f"   Telemetry: {telemetry_path.name}")
        print(f"   Baselines: {baselines_path.name}")
        print(f"   Fixtures with warmup_complete=True: {warmed}/{len(baselines)}")
        print()

    # Load readings
    readings: list[dict] = []
    with open(telemetry_path) as f:
        for line in f:
            line = line.strip()
            if line:
                readings.append(json.loads(line))
    # Ensure chronological order
    readings.sort(key=lambda r: r.get("timestamp", ""))

    # Run detection
    engine = DetectionEngine(baselines, fixtures)
    events = engine.process_batch(readings)

    # Finalize — catch trailing dropouts
    if readings:
        last_ts_str = readings[-1]["timestamp"]
        last_ts     = datetime.fromisoformat(last_ts_str)
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)
        events.extend(engine.finalize(last_ts))

    # Write detection events
    with open(output_path, "w") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")

    if not quiet:
        dispatched = sum(1 for e in events if e["status"] == "dispatched")
        logged     = sum(1 for e in events if e["status"] == "logged")
        leak_evts  = sum(1 for e in events if e["event_type"] == "leak")
        sf_evts    = sum(1 for e in events if e["event_type"] == "sensor_fault")
        print(f"✅ Detection complete.")
        print(f"   Total events:  {len(events)}")
        print(f"   Dispatched:    {dispatched}")
        print(f"   Logged-only:   {logged}")
        print(f"   Leak events:   {leak_evts}")
        print(f"   Sensor faults: {sf_evts}")
        print(f"   Output:        {output_path}")
        print()

    # Optional scoring
    if labels_path:
        _score_and_report(events, labels_path, quiet)

    return events


def _score_and_report(
    events: list[dict],
    labels_path: str | Path,
    quiet: bool = False,
) -> None:
    """Load labels and score detection events using simulator/scoring.py."""
    import json
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from simulator.scoring import match_detections_to_labels

    with open(labels_path) as f:
        raw = json.load(f)
    labels = raw["anomalies"] if "anomalies" in raw else raw

    # Score only DISPATCHED leak and sensor_fault events against anomaly labels
    # (Hygiene tickets are forward-looking predictions, not leak/sensor anomalies)
    dispatched_anomalies = [e for e in events if e["status"] == "dispatched" and e["event_type"] in ("leak", "sensor_fault")]
    dispatched_hygiene   = [e for e in events if e["status"] == "dispatched" and e["event_type"] == "hygiene"]

    result = match_detections_to_labels(dispatched_anomalies, labels)

    print("=" * 64)
    print("SCORING (dispatched leak & sensor fault events)")
    print("=" * 64)
    print(result.summary())
    print(f"  Predictive hygiene tickets dispatched: {len(dispatched_hygiene)}")
    print()

    # Per-type breakdown (recall + mean/median latency)
    from collections import defaultdict
    import statistics

    tp_by_type: dict[str, int] = defaultdict(int)
    fn_by_type: dict[str, int] = defaultdict(int)
    latencies_by_type: dict[str, list[float]] = defaultdict(list)

    for pair in result.true_positives:
        atype = pair.label["anomaly_type"]
        tp_by_type[atype] += 1
        latencies_by_type[atype].append(pair.latency_s)

    for lbl in result.false_negatives:
        fn_by_type[lbl["anomaly_type"]] += 1

    all_types = sorted(set(list(tp_by_type) + list(fn_by_type)))
    print("\nPer-anomaly-type breakdown (recall & latency):")
    print(f"  {'Type':18s}  {'TP':4}  {'FN':4}  {'Recall':8}  {'Mean Lat (s)':14}  {'Median Lat (s)':14}")
    print("  " + "-" * 72)
    for atype in all_types:
        tp  = tp_by_type[atype]
        fn  = fn_by_type[atype]
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        lats = latencies_by_type[atype]
        if lats:
            mean_lat = statistics.mean(lats)
            med_lat  = statistics.median(lats)
            lat_str  = f"{mean_lat:14.1f}  {med_lat:14.1f}"
        else:
            lat_str  = f"{'N/A':>14s}  {'N/A':>14s}"
        print(f"  {atype:18s}  {tp:4}  {fn:4}  {rec:8.3f}  {lat_str}")

    # Hard-negative FP analysis
    print()
    fp_by_tier: dict[str, int] = defaultdict(int)
    for det in result.false_positives:
        fp_by_tier[det.get("zone_tier", "?")] += 1
    print("False positives by tier:")
    for tier in sorted(fp_by_tier):
        print(f"  {tier}: {fp_by_tier[tier]} FP(s)")
    if not result.false_positives:
        print("  (none)")

    print()
    print(f"Redundant detections (same label, multiple fires): {result.rd}")


def main() -> None:
    args  = parse_args()
    run(
        telemetry_path = args.telemetry,
        baselines_path = args.baselines,
        output_path    = args.output,
        labels_path    = args.labels,
        quiet          = args.quiet,
    )


if __name__ == "__main__":
    main()
