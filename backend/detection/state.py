"""
detection/state.py — Per-fixture mutable state for the detection engine.

One FixtureDetectionState instance is created per fixture at engine start-up
and mutated in-place as readings are processed in timestamp order.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class FixtureDetectionState:
    """
    Running state machine for one fixture's anomaly detection.

    Fields are set/cleared by DetectionEngine.process_reading().
    """
    fixture_id:   str
    zone_tier:    str
    fixture_type: str

    # ── EWMA state ────────────────────────────────────────────────────────────
    # Current idle-flow EWMA value (L/min).
    # Initialised to baseline.initial_ewma (= baseline.mean_idle_flow).
    # Only updated when occupancy=0, flush_event=0, status="ok", not post-flush.
    ewma: float = 0.0

    # ── Candidate event state ─────────────────────────────────────────────────
    # Timestamp when the EWMA first exceeded UCL in the current run.
    # None = not currently above UCL.
    candidate_start_ts: Optional[datetime] = None

    # ── Post-flush suppression & Stuck-valve check (§7.4) ─────────────────────
    # Timestamp of the most recent flush_event=1 reading.
    # None = no flush seen yet.
    last_flush_ts: Optional[datetime] = None
    pending_flush_start_ts: Optional[datetime] = None
    stuck_valve_dispatched: bool = False

    # ── Dropout detection ─────────────────────────────────────────────────────
    # Timestamp of the most recent reading (any type) for this fixture.
    # Used by the engine to detect gaps > SENSOR_DROPOUT_GAP_S.
    last_reading_ts: Optional[datetime] = None

    # ── Flatline suppression ──────────────────────────────────────────────────
    # True while the fixture is in a flatline episode (to avoid re-firing per reading).
    in_flatline_episode: bool = False

    # ── Dropout suppression ───────────────────────────────────────────────────
    # True while the fixture is in a dropout episode.
    in_dropout_episode: bool = False

    # ── Dispatch deduplication ────────────────────────────────────────────────
    # Suppress re-emitting while EWMA remains continuously above UCL.
    # Set True on event emission; reset False when EWMA drops <= UCL.
    suppress_until_below_ucl: bool = False
