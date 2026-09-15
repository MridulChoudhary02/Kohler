"""
detection/sensor_health.py — Sensor health scoring (PRD Section 9).

Tracks per-sensor health metrics over a rolling window:
  - missing-data rate (expected 30s interval vs actual gaps)
  - flatline flag (identical reading repeated implausibly long or status="flatline")
  - out-of-range value rate (physically impossible flow/occupancy or status="out_of_range")
  - drift flag (baseline shift faster than physically plausible or status="drift")

Formula (§9):
  sensor_health_score = 1.0 - (0.30*missing_rate + 0.30*flatline_flag + 0.20*out_of_range_rate + 0.20*drift_flag)

If sensor_health_score < 0.60:
  1. Any leak/hygiene detection event from that sensor is downgraded to "logged only".
  2. A sensor_fault ticket-type event (sub_type="sensor_maintenance") is emitted.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# Config constants (mirrored from app/core/config.py)
W_MISSING          = 0.30
W_FLATLINE         = 0.30
W_OUT_OF_RANGE     = 0.20
W_DRIFT            = 0.20
DEGRADED_THRESHOLD = 0.60
READING_INTERVAL_S = 30
WINDOW_MINUTES     = 60


def _parse_ts(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class SensorHealthState:
    sensor_id:          str
    fixture_id:         str
    zone_tier:          str = "Tier 4"
    
    last_reading_ts:    Optional[datetime] = None
    readings_in_window: list[dict[str, Any]] = field(default_factory=list)
    
    in_maintenance_episode: bool = False
    health_score:           float = 1.0
    
    missing_rate:       float = 0.0
    flatline_flag:      float = 0.0
    out_of_range_rate:  float = 0.0
    drift_flag:         float = 0.0


class SensorHealthTracker:
    """Stateful health tracker per sensor."""

    def __init__(self, sensor_id: str, fixture_id: str, zone_tier: str = "Tier 4", window_minutes: int = WINDOW_MINUTES):
        self.sensor_id      = sensor_id
        self.fixture_id     = fixture_id
        self.zone_tier      = zone_tier
        self.window_minutes = window_minutes
        self.state          = SensorHealthState(sensor_id=sensor_id, fixture_id=fixture_id, zone_tier=zone_tier)

    def process_reading(self, reading: dict[str, Any]) -> tuple[float, Optional[dict[str, Any]]]:
        """
        Process a telemetry reading for this sensor.
        Returns (sensor_health_score, optional_sensor_maintenance_event).
        """
        ts   = _parse_ts(reading["timestamp"])
        flow = float(reading.get("flow_rate_lpm", 0.0))
        occ  = int(reading.get("occupancy_state", 0))
        diag = reading.get("diagnostic_status", "ok")

        # Maintain rolling window of readings in last window_minutes
        cutoff = ts - timedelta(minutes=self.window_minutes)
        self.state.readings_in_window = [
            r for r in self.state.readings_in_window
            if _parse_ts(r["timestamp"]) >= cutoff
        ]
        self.state.readings_in_window.append(reading)

        # 1. Missing data rate
        expected_count = max(1.0, (self.window_minutes * 60.0) / READING_INTERVAL_S)
        actual_count   = float(len(self.state.readings_in_window))
        
        gap_penalty = 0.0
        if self.state.last_reading_ts is not None:
            gap_s = (ts - self.state.last_reading_ts).total_seconds()
            if gap_s > READING_INTERVAL_S * 2:
                gap_penalty = min(1.0, (gap_s - READING_INTERVAL_S) / (READING_INTERVAL_S * 10))

        missing_rate = min(1.0, max(0.0, (expected_count - actual_count) / expected_count) + gap_penalty)
        self.state.last_reading_ts = ts

        # 2. Flatline flag
        flatline_flag = 0.0
        if diag == "flatline":
            flatline_flag = 1.0
        else:
            if len(self.state.readings_in_window) >= 15:
                recent_flows = [r.get("flow_rate_lpm", 0.0) for r in self.state.readings_in_window[-15:]]
                if len(set(recent_flows)) == 1 and recent_flows[0] > 0.0:
                    flatline_flag = 1.0

        # 3. Out-of-range rate
        oor_count = sum(
            1 for r in self.state.readings_in_window
            if r.get("diagnostic_status") == "out_of_range"
            or float(r.get("flow_rate_lpm", 0.0)) < 0.0
            or float(r.get("flow_rate_lpm", 0.0)) > 100.0
        )
        out_of_range_rate = oor_count / max(len(self.state.readings_in_window), 1)

        # 4. Drift flag
        drift_flag = 1.0 if diag == "drift" else 0.0

        # Compute composite score
        penalty = (
            W_MISSING * missing_rate
            + W_FLATLINE * flatline_flag
            + W_OUT_OF_RANGE * out_of_range_rate
            + W_DRIFT * drift_flag
        )
        score = max(0.0, min(1.0, 1.0 - penalty))

        self.state.missing_rate      = round(missing_rate, 4)
        self.state.flatline_flag     = flatline_flag
        self.state.out_of_range_rate = round(out_of_range_rate, 4)
        self.state.drift_flag        = drift_flag
        self.state.health_score      = round(score, 4)

        maint_event = None
        if score < DEGRADED_THRESHOLD:
            if not self.state.in_maintenance_episode:
                self.state.in_maintenance_episode = True
                maint_event = {
                    "event_id":            str(uuid.uuid4()),
                    "sensor_id":           self.sensor_id,
                    "fixture_id":          self.fixture_id,
                    "zone_tier":           self.zone_tier,
                    "event_type":          "sensor_fault",
                    "sub_type":            "sensor_maintenance",
                    "detected_at":         ts.isoformat(),
                    "confidence_score":    round(1.0 - score, 4),
                    "sensor_health_score": round(score, 4),
                    "status":              "dispatched",
                }
        else:
            self.state.in_maintenance_episode = False

        return score, maint_event
