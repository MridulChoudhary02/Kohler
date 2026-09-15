"""
simulator/generate_test_set.py — Generate the canonical 3-day labeled test set.

Reads scenarios from test_scenarios.py (the authoritative definition),
runs SimulatorEngine for each day, and writes:

  simulator/output/test_set/
    day1_telemetry.jsonl          — 20-fixture telemetry for 2026-09-15
    day1_anomaly_labels.json      — 5 ground-truth anomaly labels
    day1_burst_events.json        — 1 burst event (Ward shift change)
    day1_hard_negative_events.json — 3 hard-negative scenarios
    day2_telemetry.jsonl
    day2_anomaly_labels.json
    day2_burst_events.json
    day2_hard_negative_events.json
    day3_telemetry.jsonl
    day3_anomaly_labels.json
    day3_burst_events.json
    day3_hard_negative_events.json
    combined_anomaly_labels.json  — all 15 labels (for single-pass Phase 2 scoring)
    combined_hard_negative_events.json — all 9 hard negatives
    manifest.json                 — summary of what was generated

Usage:
    cd backend/
    python -m simulator.generate_test_set [--seed 42] [--quiet]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.engine import SimulatorEngine
from simulator.test_scenarios import ALL_DAYS
from scripts.seed_data import SEED

# ─────────────────────────────────────────────────────────────────────────────
# Fixture list (same as runner.py)
# ─────────────────────────────────────────────────────────────────────────────

def _build_fixture_list():
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


ALL_FIXTURES = _build_fixture_list()
OUT_DIR = Path(__file__).parent / "output" / "test_set"


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _write_jsonl(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def generate(seed: int = 42, quiet: bool = False) -> None:
    if not quiet:
        print("🏥 Generating 3-day canonical test set …\n")

    all_labels:   list[dict] = []
    all_hard_neg: list[dict] = []
    manifest_days = []

    # Each day uses a deterministic seed derived from the base seed + day index
    for day_idx, (date_str, anomaly_specs, burst_specs, hard_neg_specs) in enumerate(ALL_DAYS):
        day_seed = seed + day_idx * 1000   # day 1 = 42, day 2 = 1042, day 3 = 2042
        day_num  = day_idx + 1

        start_ts = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_ts   = start_ts + timedelta(hours=24)

        engine = SimulatorEngine(
            fixtures            = ALL_FIXTURES,
            anomaly_specs       = anomaly_specs,
            burst_specs         = burst_specs,
            hard_negative_specs = hard_neg_specs,
            seed                = day_seed,
        )
        readings, labels, burst_events, hard_neg_events = engine.run(start_ts, end_ts)

        # Per-day output
        _write_jsonl(OUT_DIR / f"day{day_num}_telemetry.jsonl", readings)

        labels_doc = {
            "generated_at":    datetime.now(timezone.utc).isoformat(),
            "simulation_date": date_str,
            "seed":            day_seed,
            "anomalies":       labels,
        }
        _write_json(OUT_DIR / f"day{day_num}_anomaly_labels.json", labels_doc)

        burst_doc = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "simulation_date": date_str,
            "burst_events": burst_events,
        }
        _write_json(OUT_DIR / f"day{day_num}_burst_events.json", burst_doc)

        hard_neg_doc = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "simulation_date": date_str,
            "hard_negative_events": hard_neg_events,
        }
        _write_json(OUT_DIR / f"day{day_num}_hard_negative_events.json", hard_neg_doc)

        all_labels.extend(labels)
        all_hard_neg.extend(hard_neg_events)

        telem_mb = (OUT_DIR / f"day{day_num}_telemetry.jsonl").stat().st_size / 1_048_576
        if not quiet:
            print(f"  Day {day_num} ({date_str}, seed={day_seed}):")
            print(f"    Readings:        {len(readings):,}  ({telem_mb:.1f} MB)")
            print(f"    Anomaly labels:  {len(labels)}")
            print(f"    Burst events:    {len(burst_events)}")
            print(f"    Hard negatives:  {len(hard_neg_events)}")
            for lbl in labels:
                tier_fixture = lbl["fixture_id"]
                print(f"      [{lbl['anomaly_type']:16s}] {tier_fixture}  "
                      f"{lbl['start_timestamp'][11:16]}→{lbl['end_timestamp'][11:16]}")
            for neg in hard_neg_events:
                print(f"      [NEG:{neg['neg_type']:14s}] {neg['fixture_id']}  "
                      f"{neg['start_timestamp'][11:16]}→{neg['end_timestamp'][11:16]}")
            print()

        manifest_days.append({
            "day":             day_num,
            "date":            date_str,
            "seed":            day_seed,
            "reading_count":   len(readings),
            "anomaly_count":   len(labels),
            "burst_count":     len(burst_events),
            "hard_neg_count":  len(hard_neg_events),
        })

    # Combined output for single-pass Phase 2 scoring
    _write_json(OUT_DIR / "combined_anomaly_labels.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_anomalies": len(all_labels),
        "anomalies": all_labels,
    })
    _write_json(OUT_DIR / "combined_hard_negative_events.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_hard_negatives": len(all_hard_neg),
        "hard_negative_events": all_hard_neg,
    })

    # Manifest
    manifest = {
        "generated_at":         datetime.now(timezone.utc).isoformat(),
        "base_seed":            seed,
        "total_readings":       sum(d["reading_count"] for d in manifest_days),
        "total_anomaly_labels": len(all_labels),
        "total_burst_events":   sum(d["burst_count"] for d in manifest_days),
        "total_hard_negatives": len(all_hard_neg),
        "days":                 manifest_days,
        "anomaly_type_coverage": _coverage_summary(all_labels),
    }
    _write_json(OUT_DIR / "manifest.json", manifest)

    if not quiet:
        print("─" * 60)
        print(f"✅ Test set complete → {OUT_DIR}")
        print(f"   Total readings:     {manifest['total_readings']:,}")
        print(f"   Anomaly labels:     {manifest['total_anomaly_labels']}  (15 expected)")
        print(f"   Burst events:       {manifest['total_burst_events']}   (3 expected)")
        print(f"   Hard negatives:     {manifest['total_hard_negatives']}  (9 expected)")
        print()
        print("   Tier × type coverage:")
        for row in manifest["anomaly_type_coverage"]:
            print(f"     {row['anomaly_type']:18s}  "
                  f"D1={row['day1_tier']}  D2={row['day2_tier']}  D3={row['day3_tier']}")


def _coverage_summary(labels: list[dict]) -> list[dict]:
    """Build a type × tier coverage table for the manifest."""
    from collections import defaultdict
    by_type: dict[str, list] = defaultdict(list)
    for lbl in labels:
        by_type[lbl["anomaly_type"]].append(lbl)

    rows = []
    for atype in sorted(by_type.keys()):
        entries = sorted(by_type[atype], key=lambda l: l["start_timestamp"])
        rows.append({
            "anomaly_type": atype,
            "count":        len(entries),
            "day1_tier":    entries[0].get("tier", "?") if len(entries) > 0 else "?",
            "day2_tier":    entries[1].get("tier", "?") if len(entries) > 1 else "?",
            "day3_tier":    entries[2].get("tier", "?") if len(entries) > 2 else "?",
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description="Generate canonical 3-day test set")
    parser.add_argument("--seed",  type=int, default=42)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    generate(seed=args.seed, quiet=args.quiet)


if __name__ == "__main__":
    main()
