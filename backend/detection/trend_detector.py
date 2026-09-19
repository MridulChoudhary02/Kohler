"""
detection/trend_detector.py — Trend-based gradual leak detection (PRD §7).

Operates alongside the instantaneous EWMA/UCL control-chart detector to identify
creeping micro-leaks and slow ramps (e.g. valve seal degradation, slow pinhole leaks)
that stay below static Upper Control Limits (UCL) on fixtures with high baseline noise.

## Mathematical Design: Linear Regression Slope vs. CUSUM
We select linear regression slope over CUSUM (Cumulative Sum Control Chart) for the following reasons:
1. Physical Interpretability: The regression slope directly measures the physical rate of flow
   increase in LPM per minute (or L/hr per hour), which directly reflects continuous physical leakage growth.
2. Invariance to Target Value: CUSUM requires an exact reference mean target (k parameter).
   On fixtures with elevated baseline standard deviation (such as scrub taps or high-flow fixtures),
   CUSUM accumulates standard stochastic variance over long 2-hour windows, causing false alarms.
3. Dual-Verification Architecture: Linear regression slope is combined with a dual sub-window mean
   difference (Δμ = y_recent - y_ref). This ensures that both the continuous directional derivative
   (slope > 0) and the absolute cumulative elevation (Δμ >= threshold) are validated before triggering.

## Detection Lifecycle
1. Suspicious State (is_suspicious = True):
   Triggered as soon as slope >= TREND_SLOPE_THRESHOLD and Δμ >= TREND_DELTA_WARNING_THRESHOLD.
   Instantly signals the engine to freeze baseline/EWMA adaptation for this fixture.
2. Warning Event (gradual_leak_warning):
   Emitted when the suspicious trend persists continuously for >= TREND_PERSISTENCE_MINUTES.
   Dispatches an early warning maintenance ticket at discounted priority.
3. Confirmed Escalation (leak):
   Emitted when the trend persists and Δμ reaches the stricter TREND_DELTA_LEAK_THRESHOLD.
   Dispatches a confirmed leak ticket with full SLA escalation.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# Config constants (mirrored from app/core/config.py)
TREND_WINDOW_MINUTES          = 120
TREND_PERSISTENCE_MINUTES     = 15
TREND_SLOPE_THRESHOLD         = 0.001     # LPM / min (+0.06 LPM/hr)
TREND_DELTA_WARNING_THRESHOLD = 0.08      # +0.08 LPM recent vs reference
TREND_DELTA_LEAK_THRESHOLD    = 0.20      # +0.20 LPM escalation to confirmed leak
TREND_IDLE_FLOW_CEILING       = 2.0       # Max LPM considered candidate idle flow
POST_FLUSH_GRACE_S            = 60


def _parse_ts(s: str | datetime) -> datetime:
    if isinstance(s, datetime):
        dt = s
    else:
        dt = datetime.fromisoformat(str(s))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class TrendDetectorState:
    fixture_id: str
    zone_tier: str

    idle_history: list[tuple[datetime, float]] = field(default_factory=list)
    last_flush_ts: Optional[datetime] = None

    trend_start_ts: Optional[datetime] = None
    warning_dispatched: bool = False
    leak_dispatched: bool = False

    is_suspicious: bool = False
    current_slope: float = 0.0
    current_delta_mean: float = 0.0


class TrendDetector:
    """Stateful trend-based leak detector per fixture."""

    def __init__(
        self,
        fixture_id: str,
        zone_tier: str = "Tier 4",
        window_minutes: int = TREND_WINDOW_MINUTES,
        persistence_minutes: int = TREND_PERSISTENCE_MINUTES,
        slope_threshold: float = TREND_SLOPE_THRESHOLD,
        delta_warn_threshold: float = TREND_DELTA_WARNING_THRESHOLD,
        delta_leak_threshold: float = TREND_DELTA_LEAK_THRESHOLD,
    ):
        self.fixture_id = fixture_id
        self.zone_tier = zone_tier
        self.window_minutes = window_minutes
        self.persistence_minutes = persistence_minutes
        self.slope_threshold = slope_threshold
        self.delta_warn_threshold = delta_warn_threshold
        self.delta_leak_threshold = delta_leak_threshold

        self.state = TrendDetectorState(fixture_id=fixture_id, zone_tier=zone_tier)

    @property
    def is_suspicious(self) -> bool:
        """Returns True if fixture is exhibiting a suspicious positive idle-flow trend."""
        return self.state.is_suspicious

    def process_reading(self, reading: dict[str, Any], warmup_complete: bool = True) -> list[dict[str, Any]]:
        """
        Process one reading and return any gradual_leak_warning or confirmed leak events.
        """
        events: list[dict[str, Any]] = []

        ts = _parse_ts(reading["timestamp"])
        flow = float(reading.get("flow_rate_lpm", 0.0))
        occ = int(reading.get("occupancy_state", 0))
        flush = int(reading.get("flush_event", 0))
        diag = reading.get("diagnostic_status", "ok")

        # Track flush events for post-flush grace
        if flush == 1:
            self.state.last_flush_ts = ts
            return events

        in_post_flush = (
            self.state.last_flush_ts is not None
            and (ts - self.state.last_flush_ts).total_seconds() < POST_FLUSH_GRACE_S
        )
        if in_post_flush:
            return events

        # Only evaluate valid idle readings
        if diag != "ok" or occ == 1:
            return events

        # Filter out active draws for flow-only sensors (e.g. scrub taps during use)
        if flow > TREND_IDLE_FLOW_CEILING:
            return events

        # Add to idle history
        self.state.idle_history.append((ts, flow))

        # Prune readings older than rolling window
        cutoff = ts - timedelta(minutes=self.window_minutes)
        if self.state.idle_history and self.state.idle_history[0][0] < cutoff:
            self.state.idle_history = [h for h in self.state.idle_history if h[0] >= cutoff]

        history = self.state.idle_history
        n = len(history)
        # Need at least 30 readings (~15 min of idle observations) to evaluate trend
        if n < 30:
            return events

        # 1. Fast analytical linear regression slope computation:
        # slope = sum((x - mean_x) * (y - mean_y)) / sum((x - mean_x)^2)
        t0 = history[0][0]
        sum_x = 0.0
        sum_y = 0.0
        for h in history:
            sum_x += (h[0] - t0).total_seconds() / 60.0
            sum_y += h[1]

        mean_x = sum_x / n
        mean_y = sum_y / n

        num = 0.0
        den = 0.0
        recent_sum = 0.0
        recent_count = 0
        ref_sum = 0.0
        ref_count = 0

        recent_cutoff = ts - timedelta(minutes=25)
        ref_cutoff = t0 + timedelta(minutes=35)

        for h in history:
            x_val = (h[0] - t0).total_seconds() / 60.0
            y_val = h[1]
            dx = x_val - mean_x
            num += dx * (y_val - mean_y)
            den += dx * dx

            if h[0] >= recent_cutoff:
                recent_sum += y_val
                recent_count += 1
            if h[0] <= ref_cutoff:
                ref_sum += y_val
                ref_count += 1

        slope = (num / den) if den > 1e-9 else 0.0

        if recent_count == 0 or ref_count == 0:
            return events

        ref_mean = ref_sum / ref_count
        recent_mean = recent_sum / recent_count
        delta_mean = recent_mean - ref_mean

        self.state.current_slope = round(slope, 6)
        self.state.current_delta_mean = round(delta_mean, 4)

        # 2. Check trend criteria
        is_trending = (slope >= self.slope_threshold and delta_mean >= self.delta_warn_threshold)
        self.state.is_suspicious = is_trending

        if is_trending:
            if self.state.trend_start_ts is None:
                self.state.trend_start_ts = ts

            elapsed_minutes = (ts - self.state.trend_start_ts).total_seconds() / 60.0

            if elapsed_minutes >= self.persistence_minutes:
                # Stage 1: gradual_leak_warning
                if not self.state.warning_dispatched:
                    self.state.warning_dispatched = True
                    status = "dispatched" if warmup_complete else "logged"
                    events.append({
                        "event_id":         str(uuid.uuid4()),
                        "fixture_id":       self.fixture_id,
                        "zone_tier":        self.zone_tier,
                        "event_type":       "gradual_leak_warning",
                        "sub_type":         "gradual_leak_warning",
                        "detected_at":      ts.isoformat(),
                        "confidence_score": 0.75,
                        "evidence_value":   round(delta_mean * 60.0, 2),  # Estimated L/hr waste rate
                        "status":           status,
                        "warmup_complete":  warmup_complete,
                        "extra": {
                            "slope_lpm_per_min": round(slope, 6),
                            "delta_mean_lpm":    round(delta_mean, 4),
                            "ref_mean_lpm":      round(ref_mean, 4),
                            "recent_mean_lpm":   round(recent_mean, 4),
                        },
                    })

                # Stage 2: Confirmed leak escalation
                if delta_mean >= self.delta_leak_threshold and not self.state.leak_dispatched:
                    self.state.leak_dispatched = True
                    status = "dispatched" if warmup_complete else "logged"
                    events.append({
                        "event_id":         str(uuid.uuid4()),
                        "fixture_id":       self.fixture_id,
                        "zone_tier":        self.zone_tier,
                        "event_type":       "leak",
                        "sub_type":         "gradual_leak",
                        "detected_at":      ts.isoformat(),
                        "confidence_score": 0.88,
                        "evidence_value":   round(delta_mean * 60.0, 2),  # Estimated L/hr waste rate
                        "status":           status,
                        "warmup_complete":  warmup_complete,
                        "extra": {
                            "slope_lpm_per_min": round(slope, 6),
                            "delta_mean_lpm":    round(delta_mean, 4),
                            "escalated_from":    "gradual_leak_warning",
                        },
                    })
        else:
            # Recovery hysteresis: reset only when delta drops below half the warning threshold
            if delta_mean < (self.delta_warn_threshold * 0.5):
                self.state.trend_start_ts = None
                self.state.warning_dispatched = False
                self.state.leak_dispatched = False
                self.state.is_suspicious = False

        return events
