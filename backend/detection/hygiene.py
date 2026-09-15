"""
detection/hygiene.py — Hygiene threshold prediction (PRD Section 8).

Tracks fixture uses and forecasts cleaning threshold breaches on a sliding 60-min window:
  recent_use_rate = uses in last 60 minutes / 60         (uses per minute)
  uses_remaining  = threshold - uses_since_clean
  predicted_breach_time = now + (uses_remaining / recent_use_rate)

If predicted_breach_time - now <= lead_time_target:
  Raise a predictive_hygiene ticket event so cleaning staff arrive before breach.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

HYGIENE_THRESHOLDS = {
    "Tier 1": 20,
    "Tier 2": 30,
    "Tier 3": 40,
    "Tier 4": 60,
}

HYGIENE_LEAD_TIMES = {
    "Tier 1": 15,   # minutes
    "Tier 2": 30,
    "Tier 3": 30,
    "Tier 4": 30,
}

WINDOW_MINUTES = 60


def _parse_ts(s: str | datetime) -> datetime:
    if isinstance(s, datetime):
        dt = s
    else:
        dt = datetime.fromisoformat(str(s))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class HygieneTrackerState:
    fixture_id:        str
    zone_tier:         str
    threshold:         int
    lead_time_minutes: int
    
    uses_since_clean:  int = 0
    last_cleaned_at:   Optional[datetime] = None
    use_timestamps:    list[datetime] = field(default_factory=list)
    
    predictive_ticket_dispatched: bool = False


class HygieneTracker:
    """Stateful hygiene predictor per fixture."""

    def __init__(self, fixture_id: str, zone_tier: str):
        self.fixture_id        = fixture_id
        self.zone_tier         = zone_tier
        self.threshold         = HYGIENE_THRESHOLDS.get(zone_tier, 30)
        self.lead_time_minutes = HYGIENE_LEAD_TIMES.get(zone_tier, 30)
        self.state             = HygieneTrackerState(
            fixture_id=fixture_id,
            zone_tier=zone_tier,
            threshold=self.threshold,
            lead_time_minutes=self.lead_time_minutes,
        )
        self._prev_occ: bool = False

    def process_reading(self, reading: dict[str, Any], warmup_complete: bool = True) -> Optional[dict[str, Any]]:
        """
        Process a telemetry reading.
        If occupancy or flush indicates a use, record it and re-evaluate prediction.
        Returns optional predictive_hygiene event dict.
        """
        ts    = _parse_ts(reading["timestamp"])
        occ   = int(reading.get("occupancy_state", 0))
        flush = int(reading.get("flush_event", 0))

        # Register use when flush occurs or when occupancy state goes 0 -> 1
        is_use = (flush == 1) or (occ == 1 and not self._prev_occ)
        self._prev_occ = bool(occ)

        if is_use:
            self.state.uses_since_clean += 1
            self.state.use_timestamps.append(ts)

        # Clean old timestamps (> 60 min ago) from sliding window
        cutoff = ts - timedelta(minutes=WINDOW_MINUTES)
        self.state.use_timestamps = [t for t in self.state.use_timestamps if t >= cutoff]

        # Compute recent use rate (uses in observed sliding window / span in minutes = uses per minute)
        recent_use_count = len(self.state.use_timestamps)
        if self.state.use_timestamps:
            elapsed_min = (ts - self.state.use_timestamps[0]).total_seconds() / 60.0
            window_span_minutes = max(1.0, min(float(WINDOW_MINUTES), elapsed_min))
            recent_use_rate     = recent_use_count / window_span_minutes
        else:
            recent_use_rate     = 0.0

        uses_remaining = max(0, self.threshold - self.state.uses_since_clean)

        if recent_use_rate > 0 and uses_remaining > 0:
            minutes_to_breach     = uses_remaining / recent_use_rate
            predicted_breach_time = ts + timedelta(minutes=minutes_to_breach)
        elif uses_remaining == 0:
            minutes_to_breach     = 0.0
            predicted_breach_time = ts
        else:
            minutes_to_breach     = float("inf")
            predicted_breach_time = None

        # Check breach prediction trigger
        if minutes_to_breach <= self.lead_time_minutes:
            if not self.state.predictive_ticket_dispatched:
                self.state.predictive_ticket_dispatched = True
                status = "dispatched" if warmup_complete else "logged"
                return {
                    "event_id":                str(uuid.uuid4()),
                    "fixture_id":              self.fixture_id,
                    "zone_tier":               self.zone_tier,
                    "event_type":              "hygiene",
                    "sub_type":                "predictive_hygiene",
                    "detected_at":             ts.isoformat(),
                    "predicted_breach_time":   predicted_breach_time.isoformat() if predicted_breach_time else ts.isoformat(),
                    "minutes_to_breach":       round(minutes_to_breach, 1),
                    "uses_since_clean":        self.state.uses_since_clean,
                    "threshold":               self.threshold,
                    "recent_use_rate_per_min": round(recent_use_rate, 4),
                    "confidence_score":        0.90,
                    "status":                  status,
                    "warmup_complete":         warmup_complete,
                }

        return None

    def reset_cleaning(self, cleaned_at: datetime) -> None:
        """Reset counter when fixture is cleaned."""
        self.state.uses_since_clean = 0
        self.state.last_cleaned_at = cleaned_at
        self.state.use_timestamps.clear()
        self.state.predictive_ticket_dispatched = False
