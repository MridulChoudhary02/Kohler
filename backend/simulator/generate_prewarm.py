"""simulator/generate_prewarm.py — Generate 7-day clean pre-warm telemetry."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from simulator.engine import SimulatorEngine
from scripts.seed_data import SEED

OUT_DIR = Path(__file__).parent / "output" / "prewarm"

PREWARM_START = datetime(2026, 9, 8, 0, 0, 0, tzinfo=timezone.utc)
PREWARM_END   = datetime(2026, 9, 15, 0, 0, 0, tzinfo=timezone.utc)  # exclusive
PREWARM_SEED  = 9999   # orthogonal to test-set seeds 42/1042/2042


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


def generate(seed: int = PREWARM_SEED, quiet: bool = False) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "prewarm_telemetry.jsonl"

    if not quiet:
        days = (PREWARM_END - PREWARM_START).days
        print(f"🏥 Generating {days}-day pre-warm telemetry (clean — no anomalies)")
        print(f"   Period: {PREWARM_START.date()} → {PREWARM_END.date()}")
        print(f"   Seed:   {seed}")
        print(f"   Output: {out_path}")
        print()

    fixtures = _build_fixture_list()
    # No anomaly_specs, no burst_specs, no hard_negative_specs
    engine = SimulatorEngine(fixtures=fixtures, seed=seed)
    readings, labels, bursts, hard_negs = engine.run(PREWARM_START, PREWARM_END)

    assert not labels,    "Pre-warm must have zero anomaly labels"
    assert not bursts,    "Pre-warm must have zero burst events"
    assert not hard_negs, "Pre-warm must have zero hard-negative events"

    with open(out_path, "w") as f:
        for r in readings:
            f.write(json.dumps(r) + "\n")

    manifest = {
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "seed":           seed,
        "start":          PREWARM_START.isoformat(),
        "end":            PREWARM_END.isoformat(),
        "days":           (PREWARM_END - PREWARM_START).days,
        "fixture_count":  len(fixtures),
        "reading_count":  len(readings),
        "anomaly_count":  0,
        "purpose":        "baseline_warmup",
    }
    with open(OUT_DIR / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    if not quiet:
        print(f"✅ Pre-warm complete.")
        print(f"   Readings: {len(readings):,}  ({out_path.stat().st_size // 1024} KB)")

    return out_path


def main():
    parser = argparse.ArgumentParser(description="Generate pre-warm telemetry")
    parser.add_argument("--seed",  type=int, default=PREWARM_SEED)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    generate(seed=args.seed, quiet=args.quiet)


if __name__ == "__main__":
    main()
