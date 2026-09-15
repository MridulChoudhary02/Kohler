"""
simulator/runner.py — CLI entry point for the telemetry simulator.

Usage examples:

  # Simulate one normal day for all fixtures → JSONL
  python -m simulator.runner --date 2026-09-15 --output output/telemetry.jsonl

  # Inject anomalies + write ground-truth labels
  python -m simulator.runner \\
    --date 2026-09-15 --output output/telemetry.jsonl \\
    --anomalies output/anomaly_labels.json --inject all

  # Inject a specific anomaly type on a specific fixture
  python -m simulator.runner \\
    --date 2026-09-15 --output output/telemetry.jsonl \\
    --inject sudden_leak --fixture fix-icu-002 \\
    --anomaly-start 10:30 --anomaly-duration 45

  # Add a traffic burst (normal usage spike, NOT an anomaly)
  python -m simulator.runner \\
    --date 2026-09-15 --output output/telemetry.jsonl \\
    --burst zone-ward --burst-start 07:30 --burst-duration 120 --burst-multiplier 2.5

  # Inject anomalies AND a traffic burst simultaneously
  python -m simulator.runner \\
    --date 2026-09-15 --output output/telemetry.jsonl \\
    --inject all --burst zone-ward --burst-start 07:30 --burst-duration 120

Options:
  --date DATE              Simulation date YYYY-MM-DD (default: today UTC)
  --output PATH            JSONL file for telemetry readings
  --anomalies PATH         JSON for ground-truth anomaly labels (--inject required)
  --inject TYPE            all | sudden_leak | gradual_leak | stuck_valve |
                           sensor_flatline | sensor_dropout  (repeatable)
  --fixture ID             Fixture ID for anomaly injection (overrides default per type)
  --anomaly-start HH:MM    Anomaly window start (default: 10:30)
  --anomaly-duration N     Anomaly window length in minutes (default: 45)
  --burst ZONE_OR_FIXTURE  Zone ID or fixture ID to apply a traffic burst to
  --burst-start HH:MM      Burst window start (default: 07:30)
  --burst-duration N       Burst window length in minutes (default: 120)
  --burst-multiplier F     Usage-rate multiplier during burst (default: 2.5)
  --bursts PATH            JSON output for burst_events (default: output/burst_events.json)
  --seed INT               RNG seed (default: 42)
  --quiet                  Suppress summary output
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.engine import SimulatorEngine
from simulator.anomaly import AnomalySpec, AnomalyType
from simulator.burst import BurstSpec
from scripts.seed_data import SEED


# ─────────────────────────────────────────────────────────────────────────────
# Fixture list
# ─────────────────────────────────────────────────────────────────────────────

def _build_fixture_list() -> list[dict[str, str]]:
    zone_map   = {z["zone_id"]: z["criticality_tier"] for z in SEED["zones"]}
    sensor_map = {s["fixture_id"]: s["sensor_id"]     for s in SEED["sensors"]}
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
_ZONE_IDS    = {z["zone_id"] for z in SEED["zones"]}
_FIXTURE_IDS = {fx["fixture_id"] for fx in SEED["fixtures"]}


# ─────────────────────────────────────────────────────────────────────────────
# Anomaly spec builder
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_FIXTURE_PER_TYPE: dict[str, str] = {
    "sudden_leak":     "fix-icu-002",
    "gradual_leak":    "fix-ward-001",
    "stuck_valve":     "fix-icu-003",
    "sensor_flatline": "fix-lab-002",
    "sensor_dropout":  "fix-lob-001",
}


def build_anomaly_specs(
    types:            list[str],
    fixtures:         list[dict[str, str]],
    date:             datetime,
    start_hm:         str,
    duration_m:       int,
    fixture_override: str | None = None,
) -> list[AnomalySpec]:
    h, m   = map(int, start_hm.split(":"))
    start  = date.replace(hour=h, minute=m, second=0, microsecond=0, tzinfo=timezone.utc)
    end    = start + timedelta(minutes=duration_m)
    fixture_by_id = {f["fixture_id"]: f for f in fixtures}
    specs: list[AnomalySpec] = []

    for atype in types:
        fid = fixture_override or DEFAULT_FIXTURE_PER_TYPE.get(atype)
        if not fid or fid not in fixture_by_id:
            print(f"  [WARN] Fixture {fid!r} not found for {atype}, skipping.", file=sys.stderr)
            continue
        fx = fixture_by_id[fid]
        match atype:
            case "sudden_leak":
                spec = AnomalySpec(AnomalyType.SUDDEN_LEAK,   fid, fx["sensor_id"], start, end, leak_flow_lpm=0.85)
            case "gradual_leak":
                spec = AnomalySpec(AnomalyType.GRADUAL_LEAK,  fid, fx["sensor_id"], start, end, leak_flow_lpm=0.60)
            case "stuck_valve":
                spec = AnomalySpec(AnomalyType.STUCK_VALVE,   fid, fx["sensor_id"], start, end, stuck_threshold_s=30.0)
            case "sensor_flatline":
                spec = AnomalySpec(AnomalyType.SENSOR_FLATLINE, fid, fx["sensor_id"], start, end, flatline_value=0.0)
            case "sensor_dropout":
                spec = AnomalySpec(AnomalyType.SENSOR_DROPOUT, fid, fx["sensor_id"], start, end)
            case _:
                print(f"  [WARN] Unknown anomaly type: {atype}", file=sys.stderr)
                continue
        specs.append(spec)
    return specs


# ─────────────────────────────────────────────────────────────────────────────
# Burst spec builder
# ─────────────────────────────────────────────────────────────────────────────

def build_burst_spec(
    target:     str,
    date:       datetime,
    start_hm:   str,
    duration_m: int,
    multiplier: float,
) -> BurstSpec:
    """
    Build a BurstSpec for --burst.
    `target` is either a zone_id (applies to all fixtures in zone) or a
    fixture_id (single fixture only).
    """
    h, m   = map(int, start_hm.split(":"))
    start  = date.replace(hour=h, minute=m, second=0, microsecond=0, tzinfo=timezone.utc)
    end    = start + timedelta(minutes=duration_m)

    if target in _ZONE_IDS:
        return BurstSpec(zone_id=target, start_ts=start, end_ts=end,
                         usage_rate_multiplier=multiplier)
    elif target in _FIXTURE_IDS:
        return BurstSpec(fixture_ids=[target], start_ts=start, end_ts=end,
                         usage_rate_multiplier=multiplier)
    else:
        raise ValueError(
            f"--burst target {target!r} is neither a known zone_id nor fixture_id.\n"
            f"  Known zones:    {sorted(_ZONE_IDS)}\n"
            f"  Known fixtures: (use --date and review seed_data.py)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Kohler Hospital Telemetry Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--date",             default=None)
    parser.add_argument("--output",           default="simulator/output/telemetry.jsonl")
    parser.add_argument("--anomalies",        default="simulator/output/anomaly_labels.json")
    parser.add_argument("--inject",           nargs="+", default=[],
                        choices=["all", "sudden_leak", "gradual_leak", "stuck_valve",
                                 "sensor_flatline", "sensor_dropout"])
    parser.add_argument("--fixture",          default=None)
    parser.add_argument("--anomaly-start",    default="10:30")
    parser.add_argument("--anomaly-duration", type=int, default=45)
    # Burst options
    parser.add_argument("--burst",            default=None,
                        metavar="ZONE_OR_FIXTURE",
                        help="Zone or fixture ID for traffic burst")
    parser.add_argument("--burst-start",      default="07:30")
    parser.add_argument("--burst-duration",   type=int, default=120)
    parser.add_argument("--burst-multiplier", type=float, default=2.5)
    parser.add_argument("--bursts",           default="simulator/output/burst_events.json")
    # General
    parser.add_argument("--seed",             type=int, default=42)
    parser.add_argument("--quiet",            action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.date:
        sim_date = datetime.strptime(args.date, "%Y-%m-%d")
    else:
        sim_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

    start_ts = sim_date.replace(tzinfo=timezone.utc)
    end_ts   = start_ts + timedelta(hours=24)

    # Anomaly specs
    inject_types = (
        ["sudden_leak", "gradual_leak", "stuck_valve", "sensor_flatline", "sensor_dropout"]
        if "all" in args.inject else list(args.inject)
    )
    anomaly_specs = build_anomaly_specs(
        inject_types, ALL_FIXTURES, sim_date,
        args.anomaly_start, args.anomaly_duration, args.fixture,
    ) if inject_types else []

    # Burst spec (optional)
    burst_specs = []
    if args.burst:
        try:
            burst_specs = [build_burst_spec(
                args.burst, sim_date,
                args.burst_start, args.burst_duration, args.burst_multiplier,
            )]
        except ValueError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)

    # Paths
    out_path    = Path(args.output)
    labels_path = Path(args.anomalies)
    bursts_path = Path(args.bursts)
    for p in [out_path, labels_path, bursts_path]:
        p.parent.mkdir(parents=True, exist_ok=True)

    if not args.quiet:
        print("🏥 Kohler Hospital Telemetry Simulator")
        print(f"   Date:       {sim_date.date()}")
        print(f"   Fixtures:   {len(ALL_FIXTURES)}")
        print(f"   Anomalies:  {len(anomaly_specs)}")
        print(f"   Bursts:     {len(burst_specs)}")
        print(f"   Seed:       {args.seed}")
        print(f"   Output:     {out_path}")
        print()

    # Run
    engine = SimulatorEngine(
        fixtures      = ALL_FIXTURES,
        anomaly_specs = anomaly_specs,
        burst_specs   = burst_specs,
        seed          = args.seed,
    )
    readings, labels, burst_events, _ = engine.run(start_ts, end_ts)

    # Write telemetry
    with open(out_path, "w") as f:
        for r in readings:
            f.write(json.dumps(r) + "\n")

    # Write anomaly labels
    if labels:
        with open(labels_path, "w") as f:
            json.dump({"generated_at": datetime.now(timezone.utc).isoformat(),
                       "simulation_date": str(sim_date.date()),
                       "seed": args.seed,
                       "anomalies": labels}, f, indent=2)

    # Write burst events (always written if --burst given)
    if burst_events:
        with open(bursts_path, "w") as f:
            json.dump({"generated_at": datetime.now(timezone.utc).isoformat(),
                       "simulation_date": str(sim_date.date()),
                       "burst_events": burst_events}, f, indent=2)

    if not args.quiet:
        print(f"✅ Done.")
        print(f"   Readings:   {len(readings):,}  ({out_path.stat().st_size // 1024} KB)")
        print(f"   Labels:     {len(labels)}")
        print(f"   Bursts:     {len(burst_events)}")
        if burst_events:
            for be in burst_events:
                print(f"     [{be['burst_id']}]  {be['start_timestamp'][11:16]}→"
                      f"{be['end_timestamp'][11:16]}  ×{be['usage_rate_multiplier']}"
                      f"  ({be['notes'][:60]})")
        if labels:
            print()
            print("   Anomalies:")
            for lbl in labels:
                print(f"     [{lbl['anomaly_type']:16s}] {lbl['fixture_id']}  "
                      f"{lbl['start_timestamp'][11:16]}→{lbl['end_timestamp'][11:16]}")


if __name__ == "__main__":
    main()
