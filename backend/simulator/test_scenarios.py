"""
simulator/test_scenarios.py — Canonical 3-day labeled test set definition.

This is the single source of truth for Phase 2 precision/recall validation.
DO NOT modify without appending a PROMPT_LOG entry (PROMPT_LOG_PROTOCOL.md §Rules).

## Design

3 simulation days × 5 anomaly types per day = 15 ground-truth labels.
Each anomaly type covers a DIFFERENT criticality tier across the 3 days,
so tier-specific detection sensitivity is exercised:

  Type            Day 1 (Tier)    Day 2 (Tier)    Day 3 (Tier)
  ─────────────────────────────────────────────────────────────
  sudden_leak     Tier 1 (ICU)    Tier 2 (Ward)   Tier 3 (Lab)
  gradual_leak    Tier 2 (Ward)   Tier 1 (OT)     Tier 4 (Lobby)
  stuck_valve     Tier 1 (ICU)    Tier 2 (Ward)   Tier 1 (ICU)
  sensor_flatline Tier 3 (Lab)    Tier 4 (Lobby)  Tier 2 (Ward)
  sensor_dropout  Tier 4 (Lobby)  Tier 1 (ICU)    Tier 3 (Lab)

9 hard-negative scenarios (3 per day) — written only to hard_negative_events.json:
  Day 1: long_handwash (Tier 2 shower), pressure_blip (Tier 1 faucet),
         traffic_burst (Tier 2 ward zone — morning shift change)
  Day 2: long_handwash (Tier 1 OT faucet), pressure_blip (Tier 3 lab flush_valve),
         traffic_burst (Tier 1 ICU zone — clinical round)
  Day 3: long_handwash (Tier 2 ward faucet), pressure_blip (Tier 1 ICU faucet),
         traffic_burst (Tier 4 lobby — visiting hours)

## Why these hard negatives stress-test the detector

  long_handwash:  Produces a long continuous active-flow reading.
                  A naive "flow > threshold for N seconds" rule would flag it,
                  but the EWMA on idle-flow (Signal 1) should NOT fire because
                  occupancy=1 throughout — it's not idle-flow that's elevated.

  pressure_blip:  Produces a brief occupancy=0 flow pulse (0.25–0.35 L/min).
                  Its duration (60 s) is shorter than the Tier 1 confirmation
                  window (3 min), so the EWMA should not sustain above UCL
                  long enough to raise a candidate event.

  traffic_burst:  Legitimate high-usage spike drives up hygiene counter fast
                  (Phase 3 should predict a hygiene breach). The leak detector
                  must NOT fire because flow patterns are normal active-use
                  flows with occupancy=1, not anomalous idle flows.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from simulator.anomaly import AnomalySpec, AnomalyType
from simulator.burst import BurstSpec, HardNegativeSpec, HardNegativeType
from scripts.seed_data import SEED

# ─────────────────────────────────────────────────────────────────────────────
# Fixture / sensor lookup helpers
# ─────────────────────────────────────────────────────────────────────────────

_sensor_by_fixture = {s["fixture_id"]: s["sensor_id"] for s in SEED["sensors"]}
_zone_by_fixture   = {f["fixture_id"]: f["zone_id"]   for f in SEED["fixtures"]}
_type_by_fixture   = {f["fixture_id"]: f["fixture_type"] for f in SEED["fixtures"]}


def _sid(fid: str) -> str:
    return _sensor_by_fixture[fid]


def _day(date_str: str) -> datetime:
    """Return midnight UTC for a YYYY-MM-DD string."""
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _ts(date_str: str, hh: int, mm: int) -> datetime:
    return _day(date_str).replace(hour=hh, minute=mm)


# ─────────────────────────────────────────────────────────────────────────────
# DAY 1 — 2026-09-15
# ─────────────────────────────────────────────────────────────────────────────

DAY1 = "2026-09-15"

DAY1_ANOMALIES: list[AnomalySpec] = [
    # sudden_leak — Tier 1, ICU flush_valve
    AnomalySpec(
        anomaly_type  = AnomalyType.SUDDEN_LEAK,
        fixture_id    = "fix-icu-002",
        sensor_id     = _sid("fix-icu-002"),
        start_ts      = _ts(DAY1, 10, 30),
        end_ts        = _ts(DAY1, 11, 15),
        leak_flow_lpm = 0.85,
    ),
    # gradual_leak — Tier 2, Ward faucet
    AnomalySpec(
        anomaly_type  = AnomalyType.GRADUAL_LEAK,
        fixture_id    = "fix-ward-001",
        sensor_id     = _sid("fix-ward-001"),
        start_ts      = _ts(DAY1, 14,  0),
        end_ts        = _ts(DAY1, 15,  0),
        leak_flow_lpm = 0.60,
    ),
    # stuck_valve — Tier 1, ICU flush_valve
    AnomalySpec(
        anomaly_type      = AnomalyType.STUCK_VALVE,
        fixture_id        = "fix-icu-003",
        sensor_id         = _sid("fix-icu-003"),
        start_ts          = _ts(DAY1, 16, 30),
        end_ts            = _ts(DAY1, 17, 15),
        stuck_threshold_s = 30.0,
    ),
    # sensor_flatline — Tier 3, Lab faucet
    AnomalySpec(
        anomaly_type   = AnomalyType.SENSOR_FLATLINE,
        fixture_id     = "fix-lab-002",
        sensor_id      = _sid("fix-lab-002"),
        start_ts       = _ts(DAY1,  9,  0),
        end_ts         = _ts(DAY1,  9, 45),
        flatline_value = 0.0,
    ),
    # sensor_dropout — Tier 4, Lobby faucet
    AnomalySpec(
        anomaly_type = AnomalyType.SENSOR_DROPOUT,
        fixture_id   = "fix-lob-001",
        sensor_id    = _sid("fix-lob-001"),
        start_ts     = _ts(DAY1, 13,  0),
        end_ts       = _ts(DAY1, 13, 45),
    ),
]

# Hard negatives — Day 1
_D1_BURST_WARD = BurstSpec(
    zone_id               = "zone-ward",
    start_ts              = _ts(DAY1,  7, 30),
    end_ts                = _ts(DAY1,  9, 30),
    usage_rate_multiplier = 2.5,
    notes = "Day 1 hard-neg: morning shift-change surge in General Ward (Tier 2).",
)

DAY1_BURSTS: list[BurstSpec] = [_D1_BURST_WARD]

DAY1_HARD_NEGATIVES: list[HardNegativeSpec] = [
    # long_handwash — Tier 2 shower (3× normal shower duration)
    HardNegativeSpec(
        neg_type       = HardNegativeType.LONG_HANDWASH,
        fixture_id     = "fix-ward-004",
        sensor_id      = _sid("fix-ward-004"),
        start_ts       = _ts(DAY1, 11, 30),
        end_ts         = _ts(DAY1, 11, 42),
        long_duration_s = 600.0,  # 10 min shower; normal mean = 300 s
    ),
    # pressure_blip — Tier 1 ICU faucet (brief 60 s transient, occupancy=0)
    HardNegativeSpec(
        neg_type       = HardNegativeType.PRESSURE_BLIP,
        fixture_id     = "fix-icu-001",
        sensor_id      = _sid("fix-icu-001"),
        start_ts       = _ts(DAY1,  8,  0),
        end_ts         = _ts(DAY1,  8,  1),
        blip_flow_lpm  = 0.30,
        blip_duration_s = 60.0,
    ),
    # traffic_burst reference — Ward zone
    HardNegativeSpec(
        neg_type   = HardNegativeType.TRAFFIC_BURST,
        fixture_id = "zone-ward",
        sensor_id  = "",
        start_ts   = _D1_BURST_WARD.start_ts,
        end_ts     = _D1_BURST_WARD.end_ts,
        burst_id   = _D1_BURST_WARD.burst_id,
    ),
    # ── NEW: long-occupancy / occupancy cross-check stress tests ─────────────────
    # Tier 1 (ICU): confirm window = 3 min. Duration = 480 s (8 min) > 3 min.
    # Patient bath in ICU with sensor attached. Occupancy=1 throughout.
    # A correct engine must NOT fire a leak alert: Signal 1 (idle-flow EWMA)
    # should stay quiet because flow is legitimate active-use flow, not idle flow.
    HardNegativeSpec(
        neg_type        = HardNegativeType.LONG_HANDWASH,
        fixture_id      = "fix-icu-005",
        sensor_id       = _sid("fix-icu-005"),
        start_ts        = _ts(DAY1, 15,  0),
        end_ts          = _ts(DAY1, 15,  8),
        long_duration_s = 480.0,   # 8 min; Tier 1 confirm window = 3 min
        notes = ("Hard-neg (OCCUPANCY CROSS-CHECK, Tier 1): ICU patient bath, "
                 "480 s active flow, occupancy=1 throughout. Duration 8 min > "
                 "Tier 1 confirmation window (3 min). No leak alert expected."),
    ),
    # Tier 4 (Lobby): confirm window = 10 min. Duration = 720 s (12 min) > 10 min.
    # Cleaner running a tap while mopping. Occupancy=1 throughout.
    HardNegativeSpec(
        neg_type        = HardNegativeType.LONG_HANDWASH,
        fixture_id      = "fix-lob-003",
        sensor_id       = _sid("fix-lob-003"),
        start_ts        = _ts(DAY1, 16, 30),
        end_ts          = _ts(DAY1, 16, 42),
        long_duration_s = 720.0,   # 12 min; Tier 4 confirm window = 10 min
        notes = ("Hard-neg (OCCUPANCY CROSS-CHECK, Tier 4): Lobby cleaner "
                 "tap running, occupancy=1 for 720 s > Tier 4 confirmation "
                 "window (10 min). No leak alert expected."),
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# DAY 2 — 2026-09-16
# ─────────────────────────────────────────────────────────────────────────────

DAY2 = "2026-09-16"

DAY2_ANOMALIES: list[AnomalySpec] = [
    # sudden_leak — Tier 2, Ward flush_valve
    AnomalySpec(
        anomaly_type  = AnomalyType.SUDDEN_LEAK,
        fixture_id    = "fix-ward-002",
        sensor_id     = _sid("fix-ward-002"),
        start_ts      = _ts(DAY2, 11,  0),
        end_ts        = _ts(DAY2, 11, 45),
        leak_flow_lpm = 0.78,
    ),
    # gradual_leak — Tier 1, OT scrub_tap (slower ramp over 90 min)
    AnomalySpec(
        anomaly_type  = AnomalyType.GRADUAL_LEAK,
        fixture_id    = "fix-ot-001",
        sensor_id     = _sid("fix-ot-001"),
        start_ts      = _ts(DAY2,  8,  0),
        end_ts        = _ts(DAY2,  9, 30),
        leak_flow_lpm = 0.50,
    ),
    # stuck_valve — Tier 2, Ward urinal
    AnomalySpec(
        anomaly_type      = AnomalyType.STUCK_VALVE,
        fixture_id        = "fix-ward-003",
        sensor_id         = _sid("fix-ward-003"),
        start_ts          = _ts(DAY2, 15,  0),
        end_ts            = _ts(DAY2, 15, 45),
        stuck_threshold_s = 30.0,
    ),
    # sensor_flatline — Tier 4, Lobby flush_valve
    AnomalySpec(
        anomaly_type   = AnomalyType.SENSOR_FLATLINE,
        fixture_id     = "fix-lob-002",
        sensor_id      = _sid("fix-lob-002"),
        start_ts       = _ts(DAY2, 10,  0),
        end_ts         = _ts(DAY2, 10, 45),
        flatline_value = 0.0,
    ),
    # sensor_dropout — Tier 1, ICU shower
    AnomalySpec(
        anomaly_type = AnomalyType.SENSOR_DROPOUT,
        fixture_id   = "fix-icu-004",
        sensor_id    = _sid("fix-icu-004"),
        start_ts     = _ts(DAY2,  7, 30),
        end_ts       = _ts(DAY2,  8, 15),
    ),
]

# Hard negatives — Day 2
_D2_BURST_ICU = BurstSpec(
    zone_id               = "zone-icu",
    start_ts              = _ts(DAY2,  6,  0),
    end_ts                = _ts(DAY2,  8,  0),
    usage_rate_multiplier = 2.0,
    notes = "Day 2 hard-neg: early morning clinical-round surge in ICU (Tier 1).",
)

DAY2_BURSTS: list[BurstSpec] = [_D2_BURST_ICU]

DAY2_HARD_NEGATIVES: list[HardNegativeSpec] = [
    # long_handwash — Tier 1 OT faucet (2× normal faucet duration)
    HardNegativeSpec(
        neg_type        = HardNegativeType.LONG_HANDWASH,
        fixture_id      = "fix-ot-004",
        sensor_id       = _sid("fix-ot-004"),
        start_ts        = _ts(DAY2, 14,  0),
        end_ts          = _ts(DAY2, 14,  7),
        long_duration_s = 180.0,  # 3 min; normal faucet mean = 20 s, but surgeon = thorough
    ),
    # pressure_blip — Tier 3 Lab flush_valve (45 s transient)
    HardNegativeSpec(
        neg_type        = HardNegativeType.PRESSURE_BLIP,
        fixture_id      = "fix-lab-003",
        sensor_id       = _sid("fix-lab-003"),
        start_ts        = _ts(DAY2, 16,  0),
        end_ts          = _ts(DAY2, 16,  1),
        blip_flow_lpm   = 0.25,
        blip_duration_s = 45.0,
    ),
    # traffic_burst reference — ICU zone
    HardNegativeSpec(
        neg_type   = HardNegativeType.TRAFFIC_BURST,
        fixture_id = "zone-icu",
        sensor_id  = "",
        start_ts   = _D2_BURST_ICU.start_ts,
        end_ts     = _D2_BURST_ICU.end_ts,
        burst_id   = _D2_BURST_ICU.burst_id,
    ),
    # ── NEW: long-occupancy / occupancy cross-check stress test ─────────────────
    # Tier 2 (Ward): confirm window = 5 min. Duration = 480 s (8 min) > 5 min.
    # Ward patient shower. Occupancy=1 throughout.
    HardNegativeSpec(
        neg_type        = HardNegativeType.LONG_HANDWASH,
        fixture_id      = "fix-ward-004",
        sensor_id       = _sid("fix-ward-004"),
        start_ts        = _ts(DAY2, 10, 30),
        end_ts          = _ts(DAY2, 10, 38),
        long_duration_s = 480.0,   # 8 min; Tier 2 confirm window = 5 min
        notes = ("Hard-neg (OCCUPANCY CROSS-CHECK, Tier 2): Ward patient shower, "
                 "480 s active flow, occupancy=1 throughout. Duration 8 min > "
                 "Tier 2 confirmation window (5 min). No leak alert expected."),
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# DAY 3 — 2026-09-17
# ─────────────────────────────────────────────────────────────────────────────

DAY3 = "2026-09-17"

DAY3_ANOMALIES: list[AnomalySpec] = [
    # sudden_leak — Tier 3, Lab flush_valve
    AnomalySpec(
        anomaly_type  = AnomalyType.SUDDEN_LEAK,
        fixture_id    = "fix-lab-003",
        sensor_id     = _sid("fix-lab-003"),
        start_ts      = _ts(DAY3, 13, 30),
        end_ts        = _ts(DAY3, 14, 15),
        leak_flow_lpm = 0.72,
    ),
    # gradual_leak — Tier 4, Lobby flush_valve (slow 90-min ramp)
    AnomalySpec(
        anomaly_type  = AnomalyType.GRADUAL_LEAK,
        fixture_id    = "fix-lob-002",
        sensor_id     = _sid("fix-lob-002"),
        start_ts      = _ts(DAY3, 16,  0),
        end_ts        = _ts(DAY3, 17, 30),
        leak_flow_lpm = 0.55,
    ),
    # stuck_valve — Tier 1, ICU flush_valve (different fixture from Day 1)
    AnomalySpec(
        anomaly_type      = AnomalyType.STUCK_VALVE,
        fixture_id        = "fix-icu-002",
        sensor_id         = _sid("fix-icu-002"),
        start_ts          = _ts(DAY3, 10,  0),
        end_ts            = _ts(DAY3, 10, 45),
        stuck_threshold_s = 30.0,
    ),
    # sensor_flatline — Tier 2, Ward faucet (new fixture)
    AnomalySpec(
        anomaly_type   = AnomalyType.SENSOR_FLATLINE,
        fixture_id     = "fix-ward-005",
        sensor_id      = _sid("fix-ward-005"),
        start_ts       = _ts(DAY3, 11, 30),
        end_ts         = _ts(DAY3, 12, 15),
        flatline_value = 0.0,
    ),
    # sensor_dropout — Tier 3, Lab scrub_tap
    AnomalySpec(
        anomaly_type = AnomalyType.SENSOR_DROPOUT,
        fixture_id   = "fix-lab-001",
        sensor_id    = _sid("fix-lab-001"),
        start_ts     = _ts(DAY3,  9,  0),
        end_ts       = _ts(DAY3,  9, 45),
    ),
]

# Hard negatives — Day 3
_D3_BURST_LOBBY = BurstSpec(
    zone_id               = "zone-lobby",
    start_ts              = _ts(DAY3, 16,  0),
    end_ts                = _ts(DAY3, 18,  0),
    usage_rate_multiplier = 3.0,
    notes = "Day 3 hard-neg: visiting-hours surge in Lobby (Tier 4).",
)

DAY3_BURSTS: list[BurstSpec] = [_D3_BURST_LOBBY]

DAY3_HARD_NEGATIVES: list[HardNegativeSpec] = [
    # long_handwash — Tier 2 Ward faucet (2× normal)
    HardNegativeSpec(
        neg_type        = HardNegativeType.LONG_HANDWASH,
        fixture_id      = "fix-ward-001",
        sensor_id       = _sid("fix-ward-001"),
        start_ts        = _ts(DAY3, 13,  0),
        end_ts          = _ts(DAY3, 13,  6),
        long_duration_s = 120.0,   # 2 min; normal mean = 20 s
    ),
    # pressure_blip — Tier 1 ICU faucet (60 s, 0.35 L/min)
    HardNegativeSpec(
        neg_type        = HardNegativeType.PRESSURE_BLIP,
        fixture_id      = "fix-icu-005",
        sensor_id       = _sid("fix-icu-005"),
        start_ts        = _ts(DAY3, 10,  0),
        end_ts          = _ts(DAY3, 10,  1),
        blip_flow_lpm   = 0.35,
        blip_duration_s = 60.0,
    ),
    # traffic_burst reference — Lobby zone
    HardNegativeSpec(
        neg_type   = HardNegativeType.TRAFFIC_BURST,
        fixture_id = "zone-lobby",
        sensor_id  = "",
        start_ts   = _D3_BURST_LOBBY.start_ts,
        end_ts     = _D3_BURST_LOBBY.end_ts,
        burst_id   = _D3_BURST_LOBBY.burst_id,
    ),
    # ── NEW: long-occupancy / occupancy cross-check stress test ─────────────────
    # Tier 3 (Lab): confirm window = 7 min. Duration = 600 s (10 min) > 7 min.
    # Lab technician extended scrub / instrument rinse. Occupancy=1 throughout.
    HardNegativeSpec(
        neg_type        = HardNegativeType.LONG_HANDWASH,
        fixture_id      = "fix-lab-002",
        sensor_id       = _sid("fix-lab-002"),
        start_ts        = _ts(DAY3, 14,  0),
        end_ts          = _ts(DAY3, 14, 10),
        long_duration_s = 600.0,   # 10 min; Tier 3 confirm window = 7 min
        notes = ("Hard-neg (OCCUPANCY CROSS-CHECK, Tier 3): Lab instrument rinse, "
                 "600 s active flow, occupancy=1 throughout. Duration 10 min > "
                 "Tier 3 confirmation window (7 min). No leak alert expected."),
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# COMBINED ACCESSORS
# ─────────────────────────────────────────────────────────────────────────────

ALL_DAYS: list[tuple[str, list[AnomalySpec], list[BurstSpec], list[HardNegativeSpec]]] = [
    (DAY1, DAY1_ANOMALIES, DAY1_BURSTS, DAY1_HARD_NEGATIVES),
    (DAY2, DAY2_ANOMALIES, DAY2_BURSTS, DAY2_HARD_NEGATIVES),
    (DAY3, DAY3_ANOMALIES, DAY3_BURSTS, DAY3_HARD_NEGATIVES),
]

ALL_ANOMALIES: list[AnomalySpec] = DAY1_ANOMALIES + DAY2_ANOMALIES + DAY3_ANOMALIES
ALL_BURSTS:    list[BurstSpec]   = DAY1_BURSTS    + DAY2_BURSTS    + DAY3_BURSTS
ALL_HARD_NEGS: list[HardNegativeSpec] = (
    DAY1_HARD_NEGATIVES + DAY2_HARD_NEGATIVES + DAY3_HARD_NEGATIVES
)
