"""
simulator/anomaly.py — Anomaly injection specification and injector.

All 5 PRD Section 14 (Phase 1) anomaly types are implemented here:
  1. sudden_leak       — abrupt onset of idle flow well above normal
  2. gradual_leak      — slow linear ramp of idle flow over the window
  3. stuck_valve       — post-flush flow fails to return to baseline
  4. sensor_flatline   — identical reading repeated for an extended period
  5. sensor_dropout    — readings are absent (gaps) for the window duration

Ground-truth label schema (written to JSON for Phase 2 precision/recall):
{
  "anomaly_id":        str (UUID),
  "fixture_id":        str,
  "sensor_id":         str,
  "anomaly_type":      "sudden_leak" | "gradual_leak" | "stuck_valve"
                       | "sensor_flatline" | "sensor_dropout",
  "start_timestamp":   ISO-8601 UTC string,
  "end_timestamp":     ISO-8601 UTC string,
  "parameters":        { type-specific params used to generate this anomaly },
  "notes":             str (human-readable description)
}
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class AnomalyType(str, Enum):
    SUDDEN_LEAK     = "sudden_leak"
    GRADUAL_LEAK    = "gradual_leak"
    STUCK_VALVE     = "stuck_valve"
    SENSOR_FLATLINE = "sensor_flatline"
    SENSOR_DROPOUT  = "sensor_dropout"


@dataclass
class AnomalySpec:
    """
    Specification for a single injected anomaly.
    Passed to the simulator engine to alter telemetry in the specified window.
    """
    anomaly_type:    AnomalyType
    fixture_id:      str
    sensor_id:       str
    start_ts:        datetime
    end_ts:          datetime

    # Type-specific parameters
    # sudden_leak / gradual_leak:
    leak_flow_lpm:   float  = 0.8     # L/min sustained or final leak rate
    # gradual_leak ramp starts at 0 and linearly grows to leak_flow_lpm over window

    # stuck_valve: how many seconds post-flush before we decide it's stuck
    stuck_threshold_s: float = 30.0

    # sensor_flatline: the value that gets repeated
    flatline_value:  float  = 0.0

    # Notes field — auto-populated by from_dict, can be overridden
    notes:           str    = ""

    @property
    def anomaly_id(self) -> str:
        """Stable ID derived from fixture + type + start. Deterministic for test reproducibility."""
        return f"anom-{self.fixture_id}-{self.anomaly_type.value}-{self.start_ts.strftime('%H%M')}"

    def to_label_dict(self) -> dict[str, Any]:
        """Serialize to ground-truth label format consumed by Phase 2."""
        return {
            "anomaly_id":     self.anomaly_id,
            "fixture_id":     self.fixture_id,
            "sensor_id":      self.sensor_id,
            "anomaly_type":   self.anomaly_type.value,
            "start_timestamp": self.start_ts.isoformat(),
            "end_timestamp":   self.end_ts.isoformat(),
            "parameters": {
                "leak_flow_lpm":     self.leak_flow_lpm,
                "stuck_threshold_s": self.stuck_threshold_s,
                "flatline_value":    self.flatline_value,
            },
            "notes": self.notes or self._auto_note(),
        }

    def _auto_note(self) -> str:
        dur_min = int((self.end_ts - self.start_ts).total_seconds() / 60)
        match self.anomaly_type:
            case AnomalyType.SUDDEN_LEAK:
                return (f"Sudden idle-flow anomaly: flow jumps to ~{self.leak_flow_lpm:.1f} L/min "
                        f"at {self.start_ts.isoformat()} for {dur_min} min.")
            case AnomalyType.GRADUAL_LEAK:
                return (f"Gradual idle-flow ramp from 0 to ~{self.leak_flow_lpm:.1f} L/min "
                        f"over {dur_min} min starting {self.start_ts.isoformat()}.")
            case AnomalyType.STUCK_VALVE:
                return (f"Stuck-valve: post-flush flow does not return to baseline for {dur_min} min "
                        f"from {self.start_ts.isoformat()}.")
            case AnomalyType.SENSOR_FLATLINE:
                return (f"Sensor flatline at value {self.flatline_value} L/min for {dur_min} min "
                        f"from {self.start_ts.isoformat()}.")
            case AnomalyType.SENSOR_DROPOUT:
                return (f"Sensor dropout (no readings) for {dur_min} min "
                        f"from {self.start_ts.isoformat()}.")
            case _:
                return "Unknown anomaly type."


def is_in_window(ts: datetime, spec: AnomalySpec) -> bool:
    """True if ts falls within [spec.start_ts, spec.end_ts)."""
    return spec.start_ts <= ts < spec.end_ts
