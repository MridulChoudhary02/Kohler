#!/usr/bin/env python3
"""
Regenerate fixture baseline profiles with context-adaptive Day/Night splits,
significance gating, and empirical Bayes shrinkage.

Usage:
    python -m scripts.regenerate_baselines
    python scripts/regenerate_baselines.py --telemetry simulator/output/prewarm/prewarm_telemetry.jsonl
"""

import argparse
import sys
from pathlib import Path

# Add backend directory to sys.path if invoked directly
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from detection.baseline import (
    BASELINE_WARMUP_DAYS,
    EWMA_LAMBDA,
    UCL_L_FACTOR,
    learn_baselines,
    save_baselines,
)
from detection.runner import _build_fixture_list


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Learn and save baseline profiles from prewarm telemetry."
    )
    parser.add_argument(
        "--telemetry",
        default="simulator/output/prewarm/prewarm_telemetry.jsonl",
        help="Path to prewarm telemetry JSONL file (default: simulator/output/prewarm/prewarm_telemetry.jsonl)",
    )
    parser.add_argument(
        "--output",
        default="simulator/output/prewarm/baseline_profiles.json",
        help="Destination path for baseline_profiles.json (default: simulator/output/prewarm/baseline_profiles.json)",
    )
    parser.add_argument(
        "--warmup-days",
        type=int,
        default=BASELINE_WARMUP_DAYS,
        help=f"Minimum duration (days) required for warmup completion (default: {BASELINE_WARMUP_DAYS})",
    )
    parser.add_argument(
        "--gate-z",
        type=float,
        default=settings.CONTEXT_GATE_Z_THRESHOLD,
        help=f"Minimum |z|-score required for significance gating (default: {settings.CONTEXT_GATE_Z_THRESHOLD})",
    )
    parser.add_argument(
        "--gate-rel-diff",
        type=float,
        default=settings.CONTEXT_GATE_REL_DIFF_THRESHOLD,
        help=f"Minimum relative difference (|day-night|/combined) required for gating (default: {settings.CONTEXT_GATE_REL_DIFF_THRESHOLD})",
    )
    parser.add_argument(
        "--shrinkage-k",
        type=int,
        default=settings.CONTEXT_SHRINKAGE_PSEUDO_COUNT_K,
        help=f"Empirical Bayes shrinkage prior pseudo-count k (default: {settings.CONTEXT_SHRINKAGE_PSEUDO_COUNT_K})",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console output during baseline learning",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    telemetry_path = Path(args.telemetry)
    output_path = Path(args.output)

    if not telemetry_path.exists():
        print(f"Error: Telemetry file not found at {telemetry_path}", file=sys.stderr)
        sys.exit(1)

    fixture_list = _build_fixture_list()

    if not args.quiet:
        print(f"Learning baselines from: {telemetry_path}")
        print(f"Fixtures configured:     {len(fixture_list)}")
        print(f"Significance Gate:       |z| >= {args.gate_z}, rel_diff >= {args.gate_rel_diff:.1%}")
        print(f"Bayes Shrinkage Prior:   k = {args.shrinkage_k}")

    profiles = learn_baselines(
        jsonl_path=telemetry_path,
        fixture_info=fixture_list,
        warmup_days=args.warmup_days,
        ewma_lambda=EWMA_LAMBDA,
        ucl_l=UCL_L_FACTOR,
        quiet=args.quiet,
        gate_z_threshold=args.gate_z,
        gate_rel_diff_threshold=args.gate_rel_diff,
        shrinkage_k=args.shrinkage_k,
    )

    save_baselines(profiles, output_path)

    split_count = sum(1 for p in profiles.values() if p.split_enabled)
    combined_count = len(profiles) - split_count

    if not args.quiet:
        print(f"Saved {len(profiles)} baseline profiles to: {output_path}")
        print(f"  Passed significance gate (Day/Night split): {split_count}")
        print(f"  Failed significance gate (Combined only):   {combined_count}")


if __name__ == "__main__":
    main()
