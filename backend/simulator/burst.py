"""
simulator/burst.py — Traffic burst and hard-negative specifications.

BurstSpec:       A sustained usage-rate spike on one or more fixtures/zones.
                 This is NORMAL behavior (heavy traffic), NOT a fault.
                 → Written to burst_events.json, NEVER to anomaly_labels.json.
                 → Phase 3 uses this to test hygiene lead-time prediction under
                   high-load conditions.

HardNegativeSpec: A realistic scenario that a naive threshold detector could
                  mistake for an anomaly, but is actually normal behavior.
                  Types:
                    long_handwash  — legitimate use event lasting 3–4× normal
                    pressure_blip  — brief (<2 min) flow transient when
                                     occupancy=0, caused by pressure fluctuation
                                     from a neighboring fixture flushing
                  → Written to hard_negative_events.json, NEVER to anomaly_labels.json.
                  → Phase 2 uses these to verify false-positive rate < 5% (PRD §2).

Note: traffic_burst hard negatives are BurstSpecs referenced in
hard_negative_events.json with neg_type="traffic_burst". The burst itself
is implemented via BurstSpec so the engine's usage-rate logic handles it
uniformly; the HardNegative record just provides the metadata for scoring.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


# ─────────────────────────────────────────────────────────────────────────────
# BURST SPEC
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BurstSpec:
    """
    Specifies a period of elevated (but legitimate) usage traffic.
    The simulator multiplies the normal Poisson arrival rate by
    `usage_rate_multiplier` for all target fixtures during the window.

    Fixtures can be specified individually (fixture_ids) or by zone (zone_id),
    which causes the engine to apply the burst to every fixture in that zone.
    Both may be provided; the union is used.

    This is distinct from an anomaly:
      - flow_rate_lpm values remain within each fixture's normal active range
      - occupancy_state reflects real users
      - diagnostic_status stays "ok"
      - NO entry is written to anomaly_labels.json
    """
    start_ts:             datetime
    end_ts:               datetime
    usage_rate_multiplier: float       # e.g. 2.5 = 2.5× normal Poisson rate
    fixture_ids:          list[str]  = field(default_factory=list)
    zone_id:              Optional[str] = None   # if set, burst all fixtures in zone
    notes:                str         = ""

    @property
    def burst_id(self) -> str:
        target = self.zone_id or (self.fixture_ids[0] if self.fixture_ids else "unknown")
        return f"burst-{target}-{self.start_ts.strftime('%H%M')}"

    def to_event_dict(self) -> dict[str, Any]:
        """Serialisation for burst_events.json."""
        return {
            "burst_id":              self.burst_id,
            "zone_id":               self.zone_id,
            "fixture_ids":           self.fixture_ids,
            "start_timestamp":       self.start_ts.isoformat(),
            "end_timestamp":         self.end_ts.isoformat(),
            "usage_rate_multiplier": self.usage_rate_multiplier,
            "notes":                 self.notes or self._auto_note(),
        }

    def _auto_note(self) -> str:
        dur_min = int((self.end_ts - self.start_ts).total_seconds() / 60)
        target = f"zone {self.zone_id}" if self.zone_id else f"fixtures {self.fixture_ids}"
        return (f"Traffic burst on {target}: {self.usage_rate_multiplier}× normal usage rate "
                f"for {dur_min} min from {self.start_ts.isoformat()}.")

    def applies_to(self, fixture_id: str, fixture_zone_id: str) -> bool:
        """True if this burst applies to the given fixture."""
        if fixture_id in self.fixture_ids:
            return True
        if self.zone_id and fixture_zone_id == self.zone_id:
            return True
        return False


# ─────────────────────────────────────────────────────────────────────────────
# HARD NEGATIVE SPEC
# ─────────────────────────────────────────────────────────────────────────────

class HardNegativeType:
    LONG_HANDWASH  = "long_handwash"
    PRESSURE_BLIP  = "pressure_blip"
    TRAFFIC_BURST  = "traffic_burst"   # references a BurstSpec by burst_id


@dataclass
class HardNegativeSpec:
    """
    A scenario that looks suspicious to a naive detector but is normal.
    Written to hard_negative_events.json — NOT anomaly_labels.json.
    Phase 2 uses these to check FP rate; none should generate a dispatched ticket.

    long_handwash:
      The fixture stays IN_USE for long_duration_s instead of the normal mean.
      Flow is normal active flow — just longer. Should NOT trigger a leak alert.
      The EWMA signal should not breach UCL because:
        (a) occupancy=1 during the event, so Signal 1 (idle-flow EWMA) doesn't fire
        (b) when the person leaves, flow returns to baseline normally

    pressure_blip:
      A brief (blip_duration_s) pulse of blip_flow_lpm flow at occupancy=0.
      Simulates pressure fluctuation from a neighboring fixture flushing.
      Should NOT reach UCL for long enough to complete a confirmation window,
      so it should be absorbed by the EWMA without triggering a candidate event.
    """
    neg_type:        str          # HardNegativeType constant
    fixture_id:      str
    sensor_id:       str
    start_ts:        datetime
    end_ts:          datetime

    # long_handwash
    long_duration_s: float        = 300.0   # forced use event duration (seconds)

    # pressure_blip
    blip_flow_lpm:   float        = 0.30    # L/min during blip (well below leak-level)
    blip_duration_s: float        = 60.0   # seconds — must be < shortest confirm window

    # traffic_burst reference
    burst_id:        Optional[str] = None

    notes:           str           = ""

    @property
    def neg_id(self) -> str:
        return f"neg-{self.fixture_id}-{self.neg_type}-{self.start_ts.strftime('%H%M')}"

    def to_event_dict(self) -> dict[str, Any]:
        """Serialisation for hard_negative_events.json."""
        return {
            "neg_id":          self.neg_id,
            "neg_type":        self.neg_type,
            "fixture_id":      self.fixture_id,
            "sensor_id":       self.sensor_id,
            "start_timestamp": self.start_ts.isoformat(),
            "end_timestamp":   self.end_ts.isoformat(),
            "parameters": {
                "long_duration_s": self.long_duration_s,
                "blip_flow_lpm":   self.blip_flow_lpm,
                "blip_duration_s": self.blip_duration_s,
                "burst_id":        self.burst_id,
            },
            "notes": self.notes or self._auto_note(),
            "expected_detection": False,   # explicit flag: no TP expected
        }

    def _auto_note(self) -> str:
        dur_min = round((self.end_ts - self.start_ts).total_seconds() / 60, 1)
        match self.neg_type:
            case HardNegativeType.LONG_HANDWASH:
                return (f"Hard negative — long handwash/shower: {self.long_duration_s:.0f}s "
                        f"legitimate use on {self.fixture_id}. Occupancy=1 throughout; "
                        f"flow returns to baseline when done. Should NOT trigger leak alert.")
            case HardNegativeType.PRESSURE_BLIP:
                return (f"Hard negative — pressure blip: {self.blip_flow_lpm:.2f} L/min for "
                        f"{self.blip_duration_s:.0f}s on {self.fixture_id} at occupancy=0. "
                        f"Caused by neighboring fixture flush. Duration < any confirmation window.")
            case HardNegativeType.TRAFFIC_BURST:
                return (f"Hard negative — legitimate traffic burst on {self.fixture_id}: "
                        f"{dur_min} min of elevated usage. Uses hygiene counter but is normal. "
                        f"Should NOT trigger leak alert, only hygiene prediction.")
            case _:
                return "Hard negative (unknown type)."
