"""
simulator/runner.py — CLI entry point for the telemetry simulator.

Usage examples:

  # Simulate one normal day for all fixtures → stdout (JSONL)
  python -m simulator.runner --date 2026-09-15 --output output/telemetry.jsonl

  # Simulate with injected anomalies, write labeled ground truth
  python -m simulator.runner \\
    --date 2026-09-15 \\
    --output output/telemetry.jsonl \\
    --anomalies output/anomaly_labels.json \\
    --inject all

  # Inject a single anomaly type on a specific fixture
  python -m simulator.runner \\
    --date 2026-09-15 \\
    --output output/telemetry.jsonl \\
    --anomalies output/anomaly_labels.json \\
    --inject sudden_leak --fixture fix-icu-002 \\
    --anomaly-start 10:30 --anomaly-duration 45

  # Run in fast-forward (simulated time, no wall-clock delay) — default mode
  # Real-time streaming mode is Phase 4 (POST /telemetry ingestion)

Options:
  --date DATE          Simulation date (YYYY-MM-DD), default: today UTC
  --output PATH        JSONL file for telemetry readings
  --anomalies PATH     JSON file for ground-truth labels (created only if --inject is set)
  --inject TYPE        Anomaly type(s): all | sudden_leak | gradual_leak |
                       stuck_valve | sensor_flatline | sensor_dropout
                       (may be repeated for multiple types)
  --fixture ID         Fixture ID to inject anomaly into (default: auto-select per type)
  --anomaly-start HH:MM  Start time of anomaly window (default: 10:30)
  --anomaly-duration N   Duration in minutes (default: 45)
  --seed INT           RNG seed for reproducibility (default: 42)
  --quiet              Suppress summary output
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure backend root is on path when run as module
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.engine import SimulatorEngine
from simulator.anomaly import AnomalySpec, AnomalyType
from scripts.seed_data import SEED


# ─────────────────────────────────────────────────────────────────────────────
# Fixture metadata — pulled from seed_data so there's a single source of truth
# ─────────────────────────────────────────────────────────────────────────────

def _build_fixture_list() -> list[dict[str, str]]:
    """
    Join fixtures + sensors + zones from seed data to build the list the
    engine needs: {fixture_id, sensor_id, fixture_type, zone_tier}.
    """
    zone_map  = {z["zone_id"]: z["criticality_tier"] for z in SEED["zones"]}
    sensor_map = {s["fixture_id"]: s["sensor_id"] for s in SEED["sensors"]}

    fixtures = []
    for fx in SEED["fixtures"]:
        fixtures.append({
            "fixture_id":   fx["fixture_id"],
            "sensor_id":    sensor_map[fx["fixture_id"]],
            "fixture_type": fx["fixture_type"],
            "zone_tier":    zone_map[fx["zone_id"]],
            "zone_id":      fx["zone_id"],
        })
    return fixtures


ALL_FIXTURES = _build_fixture_list()


# ─────────────────────────────────────────────────────────────────────────────
# Anomaly scenario builder
# ─────────────────────────────────────────────────────────────────────────────

# Default fixtures for each anomaly type — chosen to cover interesting cases:
#   sudden_leak   → ICU flush_valve (Tier 1, high criticality)
#   gradual_leak  → Ward faucet    (Tier 2)
#   stuck_valve   → ICU flush_valve (Tier 1, demonstrates post-flush non-return)
#   sensor_flatline → Lab sensor   (Tier 3, demonstrates health-score downgrade)
#   sensor_dropout  → Lobby sensor  (Tier 4)
DEFAULT_FIXTURE_PER_TYPE: dict[str, str] = {
    "sudden_leak":     "fix-icu-002",
    "gradual_leak":    "fix-ward-001",
    "stuck_valve":     "fix-icu-003",
    "sensor_flatline": "fix-lab-002",
    "sensor_dropout":  "fix-lob-001",
}


def build_anomaly_specs(
    types:     list[str],
    fixtures:  list[dict[str, str]],
    date:      datetime,
    start_hm:  str,
    duration_m: int,
    fixture_override: str | None = None,
) -> list[AnomalySpec]:
    """Build AnomalySpec instances for each requested anomaly type."""
    h, m   = map(int, start_hm.split(":"))
    start  = date.replace(hour=h, minute=m, second=0, microsecond=0, tzinfo=timezone.utc)
    end    = start + timedelta(minutes=duration_m)

    fixture_by_id = {f["fixture_id"]: f for f in fixtures}
    specs: list[AnomalySpec] = []

    for atype in types:
        fid = fixture_override or DEFAULT_FIXTURE_PER_TYPE.get(atype)
        if fid not in fixture_by_id:
            print(f"  [WARN] Fixture {fid} not found for anomaly {atype}, skipping.", file=sys.stderr)
            continue
        fx = fixture_by_id[fid]

        match atype:
            case "sudden_leak":
                spec = AnomalySpec(
                    anomaly_type = AnomalyType.SUDDEN_LEAK,
                    fixture_id   = fid,
                    sensor_id    = fx["sensor_id"],
                    start_ts     = start,
                    end_ts       = end,
                    leak_flow_lpm = 0.85,    # PRD Section 7.6: clearly above UCL
                )
            case "gradual_leak":
                spec = AnomalySpec(
                    anomaly_type = AnomalyType.GRADUAL_LEAK,
                    fixture_id   = fid,
                    sensor_id    = fx["sensor_id"],
                    start_ts     = start,
                    end_ts       = end,
                    leak_flow_lpm = 0.60,    # final rate after full ramp
                )
            case "stuck_valve":
                spec = AnomalySpec(
                    anomaly_type  = AnomalyType.STUCK_VALVE,
                    fixture_id    = fid,
                    sensor_id     = fx["sensor_id"],
                    start_ts      = start,
                    end_ts        = end,
                    stuck_threshold_s = 30.0,
                )
            case "sensor_flatline":
                spec = AnomalySpec(
                    anomaly_type  = AnomalyType.SENSOR_FLATLINE,
                    fixture_id    = fid,
                    sensor_id     = fx["sensor_id"],
                    start_ts      = start,
                    end_ts        = end,
                    flatline_value = 0.0,    # stuck at exactly 0
                )
            case "sensor_dropout":
                spec = AnomalySpec(
                    anomaly_type = AnomalyType.SENSOR_DROPOUT,
                    fixture_id   = fid,
                    sensor_id    = fx["sensor_id"],
                    start_ts     = start,
                    end_ts       = end,
                )
            case _:
                print(f"  [WARN] Unknown anomaly type: {atype}", file=sys.stderr)
                continue

        specs.append(spec)

    return specs


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Kohler Hospital Telemetry Simulator — Phase 1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--date",             default=None,
                        help="Simulation date YYYY-MM-DD (default: today UTC)")
    parser.add_argument("--output",           default="simulator/output/telemetry.jsonl",
                        help="Output JSONL file for telemetry readings")
    parser.add_argument("--anomalies",        default="simulator/output/anomaly_labels.json",
                        help="Output JSON file for ground-truth anomaly labels")
    parser.add_argument("--inject",           nargs="+", default=[],
                        choices=["all", "sudden_leak", "gradual_leak", "stuck_valve",
                                 "sensor_flatline", "sensor_dropout"],
                        help="Anomaly type(s) to inject")
    parser.add_argument("--fixture",          default=None,
                        help="Fixture ID for anomaly injection (overrides default per type)")
    parser.add_argument("--anomaly-start",    default="10:30",
                        help="Start time HH:MM for anomaly window (default: 10:30)")
    parser.add_argument("--anomaly-duration", type=int, default=45,
                        help="Duration in minutes (default: 45)")
    parser.add_argument("--seed",             type=int, default=42,
                        help="RNG seed (default: 42)")
    parser.add_argument("--quiet",            action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Resolve date
    if args.date:
        sim_date = datetime.strptime(args.date, "%Y-%m-%d")
    else:
        sim_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    start_ts = sim_date.replace(tzinfo=timezone.utc)
    end_ts   = start_ts + timedelta(hours=24)

    # Resolve anomaly types
    inject_types: list[str] = []
    if "all" in args.inject:
        inject_types = ["sudden_leak", "gradual_leak", "stuck_valve",
                        "sensor_flatline", "sensor_dropout"]
    else:
        inject_types = list(args.inject)

    # Build anomaly specs
    anomaly_specs: list[AnomalySpec] = []
    if inject_types:
        anomaly_specs = build_anomaly_specs(
            types            = inject_types,
            fixtures         = ALL_FIXTURES,
            date             = sim_date,
            start_hm         = args.anomaly_start,
            duration_m       = args.anomaly_duration,
            fixture_override = args.fixture,
        )

    # Create output directory
    out_path      = Path(args.output)
    labels_path   = Path(args.anomalies)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    labels_path.parent.mkdir(parents=True, exist_ok=True)

    if not args.quiet:
        print(f"🏥 Kohler Hospital Telemetry Simulator — Phase 1")
        print(f"   Date:     {sim_date.date()}")
        print(f"   Fixtures: {len(ALL_FIXTURES)}")
        print(f"   Anomalies:{len(anomaly_specs)}")
        print(f"   Seed:     {args.seed}")
        print(f"   Output:   {out_path}")
        if anomaly_specs:
            print(f"   Labels:   {labels_path}")
        print()

    # Run simulation
    engine = SimulatorEngine(
        fixtures      = ALL_FIXTURES,
        anomaly_specs = anomaly_specs,
        seed          = args.seed,
    )
    readings, labels = engine.run(start_ts, end_ts)

    # Write telemetry JSONL
    with open(out_path, "w") as f:
        for r in readings:
            f.write(json.dumps(r) + "\n")

    # Write ground-truth labels JSON (only if anomalies were injected)
    if labels:
        with open(labels_path, "w") as f:
            json.dump({"generated_at": datetime.utcnow().isoformat() + "Z",
                       "simulation_date": str(sim_date.date()),
                       "seed": args.seed,
                       "anomalies": labels}, f, indent=2)

    if not args.quiet:
        total = len(readings)
        print(f"✅ Done.")
        print(f"   Readings written:   {total:,}")
        print(f"   Anomaly labels:     {len(labels)}")
        print(f"   Output file:        {out_path}  ({out_path.stat().st_size // 1024} KB)")
        if labels:
            print(f"   Ground-truth file:  {labels_path}")
            print()
            print("   Injected anomalies:")
            for lbl in labels:
                print(f"     [{lbl['anomaly_type']:16s}] fixture={lbl['fixture_id']}  "
                      f"{lbl['start_timestamp'][11:16]}→{lbl['end_timestamp'][11:16]}")


if __name__ == "__main__":
    main()
