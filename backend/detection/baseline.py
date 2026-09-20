"""
detection/baseline.py — Baseline learning for Phase 2 detection engine.

Reads pre-warm telemetry JSONL and computes per-fixture baseline statistics
using the Welford online algorithm (numerically stable; no catastrophic
cancellation in variance computation).

## What counts as an "idle" reading (used for baseline)

  occupancy_state == 0   AND
  diagnostic_status == "ok"  AND
  flush_event == 0

Flush events temporarily spike flow; post-flush decay contaminates the EWMA
if included. The POST_FLUSH_GRACE_S window is enforced inside the engine
(not here) since baseline learning only needs clean idle readings.

## warmup_complete rule

  warmup_complete = True  iff  elapsed_span >= BASELINE_WARMUP_DAYS days
  where elapsed_span = last_reading_ts - first_reading_ts per fixture.

## Sanity check

  After learning, compare mean_idle_flow / std_idle_flow against the
  simulator's ground-truth values (profiles.py). Acceptable error:
    mean: |learned - ground_truth| ≤ 0.01 L/min
    std : |learned - ground_truth| / ground_truth ≤ 0.40  (40% rel. error)
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

# ── Constants (mirrored from config to avoid heavy app imports) ───────────────
BASELINE_WARMUP_DAYS: int = 7
EWMA_LAMBDA: float        = 0.2
UCL_L_FACTOR: float       = 3.0

CONTEXT_ADAPTIVE_BASELINE_ENABLED: bool = True
CONTEXT_DAY_START_HOUR: int = 6
CONTEXT_DAY_END_HOUR: int = 22
CONTEXT_MIN_SAMPLE_COUNT: int = 60
CONTEXT_GATE_Z_THRESHOLD: float = 3.0
CONTEXT_GATE_REL_DIFF_THRESHOLD: float = 0.25
CONTEXT_SHRINKAGE_PSEUDO_COUNT_K: int = 6720


# ─────────────────────────────────────────────────────────────────────────────
# WELFORD ONLINE ACCUMULATOR
# ─────────────────────────────────────────────────────────────────────────────

class _Welford:
    """Numerically stable online mean / variance (Welford 1962)."""
    __slots__ = ("n", "mean", "_M2")

    def __init__(self):
        self.n    = 0
        self.mean = 0.0
        self._M2  = 0.0

    def update(self, x: float) -> None:
        self.n += 1
        delta  = x - self.mean
        self.mean += delta / self.n
        self._M2  += delta * (x - self.mean)

    @property
    def variance(self) -> float:
        return self._M2 / self.n if self.n > 1 else 0.0

    @property
    def std(self) -> float:
        return math.sqrt(self.variance)


# ─────────────────────────────────────────────────────────────────────────────
# BASELINE PROFILE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BaselineProfile:
    """
    Per-fixture learned baseline — output of learn_baselines().
    Used by DetectionEngine to compute UCL and initialise EWMA.
    """
    fixture_id:          str
    fixture_type:        str
    zone_tier:           str

    # Learned idle-flow statistics (occupancy=0, ok, not flushing)
    mean_idle_flow:      float   # L/min
    std_idle_flow:       float   # L/min
    sample_count:        int     # idle readings that contributed

    # Derived threshold
    ucl:                 float   # = mean + L * std

    # Initial EWMA value for the detection engine (= mean_idle_flow)
    initial_ewma:        float

    # Learned flush statistics (for flush-type fixtures; PRD §7.1, §7.4)
    mean_flush_duration_s: float = 10.0   # seconds
    std_flush_duration_s:  float = 2.0    # seconds

    # Warmup bookkeeping
    warmup_complete:     bool = False
    warmup_started_at:   Optional[str] = None
    warmup_completed_at: Optional[str] = None

    # Context-adaptive baseline windows (Day: 06:00-22:00, Night: 22:00-06:00)
    day_baseline:        Optional[dict[str, Any]] = None
    night_baseline:      Optional[dict[str, Any]] = None
    split_enabled:       bool = False
    gate_z_score:        Optional[float] = None
    gate_rel_diff:       Optional[float] = None

    def get_active_baseline(
        self,
        ts: datetime,
        adaptive_enabled: bool = True,
        min_samples: int = CONTEXT_MIN_SAMPLE_COUNT,
    ) -> tuple[float, float, float, str, bool]:
        """
        Determine active (mean, std, ucl, window_name, is_fallback) for reading at ts.
        """
        if not adaptive_enabled or not self.split_enabled:
            return self.mean_idle_flow, self.std_idle_flow, self.ucl, "combined", False

        hour = ts.hour
        is_day = (CONTEXT_DAY_START_HOUR <= hour < CONTEXT_DAY_END_HOUR)
        window = "day" if is_day else "night"
        target = self.day_baseline if is_day else self.night_baseline

        if target is not None and target.get("sample_count", 0) >= min_samples:
            return (
                target["mean_idle_flow"],
                target["std_idle_flow"],
                target["ucl"],
                window,
                False,
            )

        # Fallback to single combined baseline
        return (
            self.mean_idle_flow,
            self.std_idle_flow,
            self.ucl,
            f"{window}_fallback_to_combined",
            True,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "BaselineProfile":
        from dataclasses import fields
        valid_keys = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**filtered)

    def sanity_summary(self, ground_truth_mean: float, ground_truth_std: float) -> str:
        """Human-readable comparison of learned vs. ground-truth parameters."""
        mean_err = abs(self.mean_idle_flow - ground_truth_mean)
        rel_std  = (abs(self.std_idle_flow - ground_truth_std) / max(ground_truth_std, 1e-6))
        mean_ok  = "✅" if mean_err <= 0.01 else "❌"
        std_ok   = "✅" if rel_std  <= 0.40 else "❌"
        return (
            f"  fixture_id:     {self.fixture_id}\n"
            f"  fixture_type:   {self.fixture_type}  ({self.zone_tier})\n"
            f"  sample_count:   {self.sample_count:,}\n"
            f"  mean_idle_flow: {self.mean_idle_flow:.5f}  "
            f"(ground_truth={ground_truth_mean:.5f}  err={mean_err:.5f}) {mean_ok}\n"
            f"  std_idle_flow:  {self.std_idle_flow:.5f}  "
            f"(ground_truth={ground_truth_std:.5f}  rel_err={rel_std:.1%}) {std_ok}\n"
            f"  UCL:            {self.ucl:.5f}\n"
            f"  warmup_complete:{self.warmup_complete}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# BASELINE LEARNING
# ─────────────────────────────────────────────────────────────────────────────

def _parse_ts(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def learn_baselines(
    jsonl_path: str | Path,
    fixture_info: list[dict[str, str]],   # [{fixture_id, fixture_type, zone_tier, ...}]
    warmup_days: int = BASELINE_WARMUP_DAYS,
    ewma_lambda: float = EWMA_LAMBDA,
    ucl_l: float = UCL_L_FACTOR,
    quiet: bool = False,
    gate_z_threshold: float = CONTEXT_GATE_Z_THRESHOLD,
    gate_rel_diff_threshold: float = CONTEXT_GATE_REL_DIFF_THRESHOLD,
    shrinkage_k: int = CONTEXT_SHRINKAGE_PSEUDO_COUNT_K,
) -> dict[str, BaselineProfile]:
    """
    Learn per-fixture baseline statistics from clean pre-warm telemetry JSONL.

    Args:
        jsonl_path:   Path to the pre-warm JSONL file (readings sorted by ts).
        fixture_info: List of dicts with fixture_id, fixture_type, zone_tier.
        warmup_days:  Minimum span (days) required for warmup_complete=True.
        ewma_lambda:  EWMA smoothing factor (mirrors EWMA_LAMBDA in config).
        ucl_l:        UCL multiplier (mirrors UCL_L_FACTOR in config).

    Returns:
        dict[fixture_id → BaselineProfile]
    """
    # Build fixture metadata index
    fixture_meta: dict[str, dict] = {f["fixture_id"]: f for f in fixture_info}

    # Per-fixture state during learning pass
    accumulators:       dict[str, _Welford] = {}
    day_accumulators:   dict[str, _Welford] = {}
    night_accumulators: dict[str, _Welford] = {}
    flush_accumulators: dict[str, _Welford] = {}
    flush_start_ts:     dict[str, datetime] = {}
    ewma_state:         dict[str, float]    = {}
    first_ts:           dict[str, datetime] = {}
    last_ts:            dict[str, datetime] = {}

    jsonl_path = Path(jsonl_path)
    total_lines = 0

    with open(jsonl_path) as f:
        for line in f:
            total_lines += 1
            reading = json.loads(line)
            fid     = reading["fixture_id"]

            # Skip fixtures not in our list
            if fid not in fixture_meta:
                continue

            ts = _parse_ts(reading["timestamp"])
            if fid not in first_ts:
                first_ts[fid] = ts
                accumulators[fid]       = _Welford()
                day_accumulators[fid]   = _Welford()
                night_accumulators[fid] = _Welford()
                flush_accumulators[fid] = _Welford()
                ewma_state[fid]         = 0.0   # will be overridden once we have a mean
            last_ts[fid] = ts

            flow       = float(reading.get("flow_rate_lpm", 0.0))
            flush_flag = int(reading.get("flush_event", 0))

            # Track flush duration for flush-type fixtures (PRD §7.1, §7.4)
            if flush_flag == 1:
                flush_start_ts[fid] = ts
            elif fid in flush_start_ts:
                # Flush started on an earlier tick — check if flow returned to idle
                elapsed = (ts - flush_start_ts[fid]).total_seconds()
                if flow <= 0.10:   # flow back to near-zero idle flow
                    flush_accumulators[fid].update(elapsed)
                    del flush_start_ts[fid]
                elif elapsed > 120.0:
                    del flush_start_ts[fid]   # timeout safety

            # Only idle, non-flush, healthy readings go into the baseline
            if (reading.get("occupancy_state", 1) == 0
                    and flush_flag == 0
                    and reading.get("diagnostic_status", "error") == "ok"):
                accumulators[fid].update(flow)
                if CONTEXT_DAY_START_HOUR <= ts.hour < CONTEXT_DAY_END_HOUR:
                    day_accumulators[fid].update(flow)
                else:
                    night_accumulators[fid].update(flow)

                # Online EWMA update
                ewma_state[fid] = (ewma_lambda * flow
                                   + (1.0 - ewma_lambda) * ewma_state[fid])

    if not quiet:
        print(f"   Processed {total_lines:,} lines from {jsonl_path.name}")

    # Build BaselineProfile for each fixture
    profiles: dict[str, BaselineProfile] = {}
    warmup_required = timedelta(days=warmup_days)

    for fid, meta in fixture_meta.items():
        acc       = accumulators.get(fid)
        flush_acc = flush_accumulators.get(fid)

        if acc is None or acc.n == 0:
            # No data seen for this fixture — create a safe default
            profiles[fid] = BaselineProfile(
                fixture_id       = fid,
                fixture_type     = meta.get("fixture_type", "unknown"),
                zone_tier        = meta.get("zone_tier", "Tier 4"),
                mean_idle_flow   = 0.0,
                std_idle_flow    = 0.025,          # conservative noise floor
                sample_count     = 0,
                ucl              = 0.0 + ucl_l * 0.025,
                initial_ewma     = 0.0,
                mean_flush_duration_s = 10.0,
                std_flush_duration_s  = 2.0,
                warmup_complete  = False,
                warmup_started_at   = None,
                warmup_completed_at = None,
            )
            continue

        mean = acc.mean
        std  = max(acc.std, 0.005)   # floor: avoid UCL collapsing to 0
        ucl  = mean + ucl_l * std

        d_acc = day_accumulators.get(fid)
        n_acc = night_accumulators.get(fid)

        d_mean = d_acc.mean if (d_acc and d_acc.n > 0) else mean
        d_std  = max(d_acc.std, 0.005) if (d_acc and d_acc.n > 0) else std
        nd     = d_acc.n if d_acc else 0

        n_mean = n_acc.mean if (n_acc and n_acc.n > 0) else mean
        n_std  = max(n_acc.std, 0.005) if (n_acc and n_acc.n > 0) else std
        nn     = n_acc.n if n_acc else 0

        # PART 1: Per-fixture significance gating
        se_d = d_std / math.sqrt(nd) if nd > 1 else 1e-6
        se_n = n_std / math.sqrt(nn) if nn > 1 else 1e-6
        denom = math.sqrt(se_d**2 + se_n**2)
        z = (d_mean - n_mean) / denom if denom > 0 else 0.0
        rel_diff = abs(d_mean - n_mean) / max(mean, 1e-6)

        split_ok = (
            abs(z) >= gate_z_threshold
            and rel_diff >= gate_rel_diff_threshold
            and nd >= CONTEXT_MIN_SAMPLE_COUNT
            and nn >= CONTEXT_MIN_SAMPLE_COUNT
        )

        if split_ok:
            # PART 2: Empirical Bayes shrinkage toward combined baseline
            k = shrinkage_k
            shrunk_d_mean = (nd * d_mean + k * mean) / (nd + k)
            shrunk_d_std  = (nd * d_std + k * std) / (nd + k)
            shrunk_d_ucl  = shrunk_d_mean + ucl_l * shrunk_d_std

            shrunk_n_mean = (nn * n_mean + k * mean) / (nn + k)
            shrunk_n_std  = (nn * n_std + k * std) / (nn + k)
            shrunk_n_ucl  = shrunk_n_mean + ucl_l * shrunk_n_std

            day_dict = {
                "mean_idle_flow": round(shrunk_d_mean, 6),
                "std_idle_flow":  round(shrunk_d_std, 6),
                "ucl":            round(shrunk_d_ucl, 6),
                "sample_count":   nd,
                "initial_ewma":   round(shrunk_d_mean, 6),
            }
            night_dict = {
                "mean_idle_flow": round(shrunk_n_mean, 6),
                "std_idle_flow":  round(shrunk_n_std, 6),
                "ucl":            round(shrunk_n_ucl, 6),
                "sample_count":   nn,
                "initial_ewma":   round(shrunk_n_mean, 6),
            }
        else:
            day_dict = None
            night_dict = None

        started_at   = first_ts.get(fid)
        ended_at     = last_ts.get(fid)
        span         = ended_at - started_at if (started_at and ended_at) else timedelta(0)
        warmup_done  = span >= (warmup_required - timedelta(minutes=5))

        mean_flush_dur = flush_acc.mean if (flush_acc and flush_acc.n > 5) else 10.0
        std_flush_dur  = max(flush_acc.std, 1.0) if (flush_acc and flush_acc.n > 5) else 2.0

        profiles[fid] = BaselineProfile(
            fixture_id          = fid,
            fixture_type        = meta.get("fixture_type", "unknown"),
            zone_tier           = meta.get("zone_tier", "Tier 4"),
            mean_idle_flow      = mean,
            std_idle_flow       = std,
            sample_count        = acc.n,
            ucl                 = ucl,
            initial_ewma        = mean,   # start detection EWMA at learned mean
            mean_flush_duration_s = mean_flush_dur,
            std_flush_duration_s  = std_flush_dur,
            warmup_complete     = warmup_done,
            warmup_started_at   = started_at.isoformat() if started_at else None,
            warmup_completed_at = ended_at.isoformat() if warmup_done else None,
            day_baseline        = day_dict,
            night_baseline      = night_dict,
            split_enabled       = split_ok,
            gate_z_score        = round(z, 2),
            gate_rel_diff       = round(rel_diff, 4),
        )

    if not quiet:
        print(f"\n--- Context-Adaptive Baseline Significance Gating ---")
        print(f"{'Fixture ID':16} | {'Day Mean':8} | {'Night Mean':10} | {'Comb Mean':9} | {'Rel Diff':8} | {'Z-Score':8} | {'Status'}")
        print("-" * 85)
        for fid in sorted(profiles.keys()):
            p = profiles[fid]
            st = 'PASS (SPLIT)' if p.split_enabled else 'FAIL (COMBINED)'
            d_m = day_accumulators[fid].mean if fid in day_accumulators else 0.0
            n_m = night_accumulators[fid].mean if fid in night_accumulators else 0.0
            print(f"{fid:16} | {d_m:8.5f} | {n_m:10.5f} | {p.mean_idle_flow:9.5f} | {p.gate_rel_diff or 0.0:7.1%} | {p.gate_z_score or 0.0:8.2f} | {st}")
        print("-" * 85 + "\n")

    return profiles


def save_baselines(profiles: dict[str, BaselineProfile], path: str | Path) -> None:
    """Serialise baseline profiles to JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(
            {"generated_at": datetime.now(timezone.utc).isoformat(),
             "profiles": {fid: p.to_dict() for fid, p in profiles.items()}},
            f, indent=2,
        )


def load_baselines(path: str | Path) -> dict[str, BaselineProfile]:
    """Load baseline profiles from JSON."""
    with open(path) as f:
        raw = json.load(f)
    data = raw["profiles"] if "profiles" in raw else raw
    return {fid: BaselineProfile.from_dict(d) for fid, d in data.items()}
