"""
simulator/profiles.py — per-fixture-type flow signatures and shift curves.

All values here are engineering judgements for realistic simulation.
They are NOT the same as the BASELINE_PROFILE learned stats — those are
computed from real (or simulated) telemetry. These are the ground-truth
parameters the simulator uses to generate synthetic telemetry.

PRD Section 5: fixture types are faucet, flush_valve, urinal, shower, scrub_tap.
"""
from dataclasses import dataclass, field
from typing import Optional
import math


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURE TYPE PROFILES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FixtureTypeProfile:
    """
    Ground-truth generation parameters for a fixture type.
    These drive the simulator; the detection engine learns these back from
    the telemetry (which is the point of Phase 2 baseline learning).
    """
    fixture_type:           str

    # Idle flow (L/min) — Gaussian noise added on top
    idle_flow_mean:         float   # should be ~0 for a healthy fixture
    idle_flow_std:          float   # sensor noise floor

    # Active (in-use) flow (L/min) — applies when occupancy=1 and no flush
    active_flow_mean:       float
    active_flow_std:        float

    # Use duration (seconds) — how long a fixture runs per use event
    use_duration_mean_s:    float
    use_duration_std_s:     float

    # Flush parameters (only meaningful for flush_valve, urinal, shower is continuous)
    generates_flush_event:  bool    = False
    flush_volume_mean_l:    float   = 0.0   # litres
    flush_volume_std_l:     float   = 0.0
    flush_duration_mean_s:  float   = 0.0   # seconds for the flush spike
    flush_duration_std_s:   float   = 0.0
    post_flush_decay_s:     float   = 3.0   # seconds to return to idle after flush

    # Does this fixture type have a meaningful occupancy signal?
    has_occupancy_signal:   bool    = True


# One profile per fixture type named exactly as in the PRD / seed data
FIXTURE_PROFILES: dict[str, FixtureTypeProfile] = {
    "faucet": FixtureTypeProfile(
        fixture_type        = "faucet",
        idle_flow_mean      = 0.0,
        idle_flow_std       = 0.02,     # ~20 mL/min sensor noise floor
        active_flow_mean    = 7.5,      # L/min (standard faucet)
        active_flow_std     = 0.8,
        use_duration_mean_s = 20.0,     # ~20 s hand-wash
        use_duration_std_s  = 8.0,
        generates_flush_event = False,
        has_occupancy_signal  = True,
    ),

    "flush_valve": FixtureTypeProfile(
        fixture_type        = "flush_valve",
        idle_flow_mean      = 0.0,
        idle_flow_std       = 0.025,
        active_flow_mean    = 0.0,      # between flushes, flow is zero
        active_flow_std     = 0.0,
        use_duration_mean_s = 5.0,      # brief visit to trigger flush
        use_duration_std_s  = 2.0,
        generates_flush_event = True,
        flush_volume_mean_l   = 6.0,    # L per flush (6 L standard)
        flush_volume_std_l    = 0.5,
        flush_duration_mean_s = 9.0,    # seconds for the flush to complete
        flush_duration_std_s  = 1.5,
        post_flush_decay_s    = 4.0,    # seconds to settle back to idle
        has_occupancy_signal  = True,
    ),

    "urinal": FixtureTypeProfile(
        fixture_type        = "urinal",
        idle_flow_mean      = 0.0,
        idle_flow_std       = 0.02,
        active_flow_mean    = 0.0,
        active_flow_std     = 0.0,
        use_duration_mean_s = 3.0,
        use_duration_std_s  = 1.0,
        generates_flush_event = True,
        flush_volume_mean_l   = 3.5,    # L per flush (water-efficient urinal)
        flush_volume_std_l    = 0.3,
        flush_duration_mean_s = 6.0,
        flush_duration_std_s  = 1.0,
        post_flush_decay_s    = 3.0,
        has_occupancy_signal  = True,
    ),

    "shower": FixtureTypeProfile(
        fixture_type        = "shower",
        idle_flow_mean      = 0.0,
        idle_flow_std       = 0.03,
        active_flow_mean    = 9.5,      # L/min (hospital shower head)
        active_flow_std     = 1.2,
        use_duration_mean_s = 300.0,    # ~5 min patient shower
        use_duration_std_s  = 90.0,
        generates_flush_event = False,
        has_occupancy_signal  = True,
    ),

    "scrub_tap": FixtureTypeProfile(
        fixture_type        = "scrub_tap",
        idle_flow_mean      = 0.0,
        idle_flow_std       = 0.02,
        active_flow_mean    = 6.5,      # L/min (surgical scrub)
        active_flow_std     = 0.6,
        use_duration_mean_s = 180.0,    # ~3 min surgical scrub
        use_duration_std_s  = 60.0,
        generates_flush_event = False,
        has_occupancy_signal  = False,  # scrub_tap sensors are flow_only per Phase 0 seed
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# SHIFT / TIME-OF-DAY USAGE CURVES
# ─────────────────────────────────────────────────────────────────────────────

def usage_multiplier(hour: int, zone_tier: str) -> float:
    """
    Returns a multiplier (0.0–1.0+) on the base usage rate for a given
    hour of day and zone criticality tier.

    Hospital shift patterns:
      Day shift:    07:00–15:00  (peak: 09:00–12:00)
      Evening shift:15:00–23:00  (secondary peak: 17:00–19:00)
      Night shift:  23:00–07:00  (minimal usage)

    Different tiers have different patterns:
      Tier 1 (ICU/OT): Near-constant across all shifts — critically ill
                        patients require care 24/7. Modest night dip.
      Tier 2 (Ward):   Strong day peak, moderate evening, low night.
      Tier 3 (Lab):    Business-hours only — almost zero at night.
      Tier 4 (Lobby):  Visiting hours peak (10:00–12:00, 16:00–18:00),
                        very low outside visiting hours and after 20:00.
    """
    curves: dict[str, list[float]] = {
        # hour:  0    1    2    3    4    5    6    7    8    9   10   11   12   13   14   15   16   17   18   19   20   21   22   23
        "Tier 1": [
            0.40,0.35,0.30,0.30,0.35,0.45,0.65,0.85,1.00,1.00,0.90,0.85,0.80,0.80,0.85,0.90,0.85,0.80,0.75,0.65,0.55,0.50,0.45,0.40
        ],
        "Tier 2": [
            0.15,0.10,0.08,0.08,0.10,0.20,0.50,0.85,1.00,0.95,0.90,0.85,0.90,0.85,0.80,0.80,0.75,0.70,0.65,0.50,0.35,0.25,0.20,0.15
        ],
        "Tier 3": [
            0.05,0.02,0.02,0.02,0.02,0.05,0.20,0.60,0.90,1.00,0.95,0.90,0.85,0.90,0.85,0.70,0.50,0.30,0.15,0.08,0.05,0.05,0.05,0.05
        ],
        "Tier 4": [
            0.02,0.01,0.01,0.01,0.01,0.02,0.05,0.15,0.40,0.70,1.00,1.00,0.90,0.80,0.70,0.60,1.00,1.00,0.80,0.50,0.25,0.10,0.05,0.02
        ],
    }
    return curves.get(zone_tier, curves["Tier 2"])[hour % 24]


# Base uses-per-hour for each fixture type at full multiplier (1.0)
BASE_USES_PER_HOUR: dict[str, float] = {
    "faucet":      8.0,   # ~ every 7-8 min at peak in a shared restroom
    "flush_valve": 6.0,   # ~ every 10 min at peak
    "urinal":      8.0,
    "shower":      1.5,   # hospitals have fewer shower cycles
    "scrub_tap":   4.0,   # surgical scrubs are less frequent but longer
}
