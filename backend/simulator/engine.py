"""
simulator/engine.py — Core simulation engine.

Generates per-fixture, per-second telemetry (TelemetryReading schema) for a
given time window. Supports:
  - Realistic flow signatures per fixture type (profiles.py)
  - Time-of-day / shift-pattern usage curves (profiles.py)
  - Stochastic use-event scheduling (Poisson arrivals)
  - Flush event generation for flush_valve and urinal types
  - Occupancy signal tracking
  - All 5 anomaly types (anomaly.py)

Output is a list of dicts matching the telemetry_readings table schema,
plus a ground-truth labels list.
"""
from __future__ import annotations

import math
import random
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from simulator.anomaly import AnomalySpec, AnomalyType, is_in_window
from simulator.profiles import (
    BASE_USES_PER_HOUR,
    FIXTURE_PROFILES,
    FixtureTypeProfile,
    usage_multiplier,
)


# Reading interval (seconds) — how often the sensor emits a reading
READING_INTERVAL_S: int = 30


class FixtureSimulator:
    """
    Simulates one fixture's telemetry for a given time window.

    State machine:
      IDLE        → occupancy=0, flow ≈ idle_flow (with noise)
      IN_USE      → occupancy=1, flow ≈ active_flow (with noise)
      FLUSHING    → occupancy may be 0 (person has left), flow spike then decay
      ANOMALY     → modifies flow / diagnostic_status per injected spec
    """

    def __init__(
        self,
        fixture_id:  str,
        sensor_id:   str,
        fixture_type: str,
        zone_tier:   str,
        rng:         random.Random,
        anomaly_specs: list[AnomalySpec] | None = None,
    ):
        self.fixture_id   = fixture_id
        self.sensor_id    = sensor_id
        self.fixture_type = fixture_type
        self.zone_tier    = zone_tier
        self.rng          = rng
        self.anomaly_specs = anomaly_specs or []
        self.profile: FixtureTypeProfile = FIXTURE_PROFILES[fixture_type]

        # Internal state
        self._use_end_ts:    Optional[datetime] = None   # when current use event ends
        self._flush_end_ts:  Optional[datetime] = None   # when current flush ends
        self._flush_volume_l: float = 0.0                # L/min during flush
        self._post_flush_end_ts: Optional[datetime] = None  # decay period end
        self._occupancy:     int = 0
        # EWMA of flow for this fixture (for gradual-leak ramp tracking)
        self._flow_ewma:     float = 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # READING GENERATION
    # ─────────────────────────────────────────────────────────────────────────

    def reading_at(self, ts: datetime) -> Optional[dict[str, Any]]:
        """
        Return a telemetry_readings-schema dict for timestamp ts.
        Returns None if the anomaly type is sensor_dropout (gap in readings).
        """
        # Check for active anomalies
        active_anomalies = [s for s in self.anomaly_specs if is_in_window(ts, s)]

        # Sensor dropout — emit nothing (no reading row)
        if any(s.anomaly_type == AnomalyType.SENSOR_DROPOUT for s in active_anomalies):
            return None

        # Sensor flatline — repeat a fixed value, flag diagnostic
        flatline_spec = next(
            (s for s in active_anomalies if s.anomaly_type == AnomalyType.SENSOR_FLATLINE),
            None,
        )
        if flatline_spec is not None:
            return self._make_reading(
                ts             = ts,
                flow_rate_lpm  = flatline_spec.flatline_value,
                flush_event    = 0,
                occupancy_state= 0,
                diagnostic_status = "flatline",
            )

        # Normal flow path (with potential leak overlay)
        flow, flush_event, occupancy = self._compute_normal_flow(ts)

        # Stuck-valve anomaly — override post-flush return behavior
        stuck_spec = next(
            (s for s in active_anomalies if s.anomaly_type == AnomalyType.STUCK_VALVE),
            None,
        )
        if stuck_spec is not None and self.profile.generates_flush_event:
            # During a stuck-valve window, keep flow elevated post-flush
            # Use the fixture's mean flush-rate flow throughout the window
            flow_rate_lpm = self.rng.gauss(
                self.profile.flush_volume_mean_l / max(self.profile.flush_duration_mean_s / 60, 0.1),
                0.3,
            )
            flow = max(0.0, flow_rate_lpm)
            flush_event = 0  # the "flush" already fired; now stuck open
            return self._make_reading(ts, flow, flush_event, occupancy, "ok")

        # Sudden leak — add constant leak flow on top of normal idle behavior
        sudden_spec = next(
            (s for s in active_anomalies if s.anomaly_type == AnomalyType.SUDDEN_LEAK),
            None,
        )
        if sudden_spec is not None and occupancy == 0:
            leak_noise = self.rng.gauss(0, 0.05)
            flow = max(0.0, sudden_spec.leak_flow_lpm + leak_noise)
            return self._make_reading(ts, flow, flush_event, occupancy, "ok")

        # Gradual leak — linearly ramp up from 0 to leak_flow_lpm over window
        gradual_spec = next(
            (s for s in active_anomalies if s.anomaly_type == AnomalyType.GRADUAL_LEAK),
            None,
        )
        if gradual_spec is not None and occupancy == 0:
            window_s = (gradual_spec.end_ts - gradual_spec.start_ts).total_seconds()
            elapsed_s = (ts - gradual_spec.start_ts).total_seconds()
            ramp_fraction = min(elapsed_s / max(window_s, 1.0), 1.0)
            leak_component = gradual_spec.leak_flow_lpm * ramp_fraction
            leak_noise = self.rng.gauss(0, 0.03)
            flow = max(0.0, flow + leak_component + leak_noise)
            return self._make_reading(ts, flow, flush_event, occupancy, "ok")

        return self._make_reading(ts, flow, flush_event, occupancy, "ok")

    def _compute_normal_flow(self, ts: datetime) -> tuple[float, int, int]:
        """
        Returns (flow_rate_lpm, flush_event_flag, occupancy_state) for ts
        under normal (non-anomalous) conditions.

        Uses a simple state machine:
        - Stochastically start a use event based on the Poisson arrival rate
          derived from BASE_USES_PER_HOUR × usage_multiplier(hour, tier).
        - Track use event duration.
        - For flush fixtures: fire a flush event at end of use.
        """
        hour = ts.hour
        base_rate = BASE_USES_PER_HOUR.get(self.fixture_type, 4.0)
        rate_per_second = (base_rate * usage_multiplier(hour, self.zone_tier)) / 3600.0

        # --- Start a new use event stochastically ---
        if self._use_end_ts is None or ts >= self._use_end_ts:
            if ts >= (self._post_flush_end_ts or ts):   # don't start during post-flush decay
                # Poisson: P(event in this interval) = rate × interval
                if self.rng.random() < rate_per_second * READING_INTERVAL_S:
                    duration_s = max(
                        2.0,
                        self.rng.gauss(
                            self.profile.use_duration_mean_s,
                            self.profile.use_duration_std_s,
                        ),
                    )
                    self._use_end_ts = ts + timedelta(seconds=duration_s)
                    self._occupancy  = 1 if self.profile.has_occupancy_signal else 0
                    # Schedule flush at end of use (for flush fixtures)
                    if self.profile.generates_flush_event:
                        flush_dur = max(
                            3.0,
                            self.rng.gauss(
                                self.profile.flush_duration_mean_s,
                                self.profile.flush_duration_std_s,
                            ),
                        )
                        self._flush_end_ts = self._use_end_ts + timedelta(seconds=flush_dur)
                        flush_vol = max(
                            1.0,
                            self.rng.gauss(
                                self.profile.flush_volume_mean_l,
                                self.profile.flush_volume_std_l,
                            ),
                        )
                        # L/min during flush
                        self._flush_volume_l = flush_vol / (flush_dur / 60.0)
                        self._post_flush_end_ts = self._flush_end_ts + timedelta(
                            seconds=self.profile.post_flush_decay_s
                        )

        # --- Determine current state ---
        in_use     = self._use_end_ts is not None and ts < self._use_end_ts
        in_flush   = (self.profile.generates_flush_event and
                      self._flush_end_ts is not None and
                      self._use_end_ts is not None and
                      ts >= self._use_end_ts and ts < self._flush_end_ts)
        post_flush = (self.profile.generates_flush_event and
                      self._flush_end_ts is not None and
                      self._post_flush_end_ts is not None and
                      ts >= self._flush_end_ts and ts < self._post_flush_end_ts)

        flush_event = 0
        if in_use:
            occupancy = 1 if self.profile.has_occupancy_signal else 0
            if self.profile.generates_flush_event:
                # In-use for flush fixture: occupancy present, zero flow (waiting)
                flow = max(0.0, self.rng.gauss(0.0, self.profile.idle_flow_std))
            else:
                flow = max(0.0, self.rng.gauss(
                    self.profile.active_flow_mean, self.profile.active_flow_std
                ))
        elif in_flush:
            occupancy = 0  # person has left, valve is flushing
            flush_event = 1
            flow = max(0.0, self.rng.gauss(self._flush_volume_l, 0.2))
        elif post_flush:
            # Exponential decay back to idle — uses fraction of remaining decay time
            occupancy = 0
            flush_event = 0
            decay_total = self.profile.post_flush_decay_s
            elapsed = (ts - self._flush_end_ts).total_seconds()
            decay_frac = max(0.0, 1.0 - elapsed / decay_total)
            residual = self._flush_volume_l * decay_frac * 0.15  # small residual
            flow = max(0.0, residual + self.rng.gauss(0, self.profile.idle_flow_std))
        else:
            # Idle
            occupancy = 0
            flush_event = 0
            flow = max(0.0, self.rng.gauss(
                self.profile.idle_flow_mean, self.profile.idle_flow_std
            ))

        return flow, flush_event, occupancy

    def _make_reading(
        self,
        ts:                datetime,
        flow_rate_lpm:     float,
        flush_event:       int,
        occupancy_state:   int,
        diagnostic_status: str,
    ) -> dict[str, Any]:
        return {
            "reading_id":        str(uuid.uuid4()),
            "sensor_id":         self.sensor_id,
            "fixture_id":        self.fixture_id,   # denormalised for output convenience
            "timestamp":         ts.isoformat(),
            "flow_rate_lpm":     round(flow_rate_lpm, 4),
            "flush_event":       flush_event,
            "occupancy_state":   occupancy_state,
            "diagnostic_status": diagnostic_status,
        }


# ─────────────────────────────────────────────────────────────────────────────
# TOP-LEVEL ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class SimulatorEngine:
    """
    Orchestrates simulation across all fixtures for a given time window.

    Usage:
        engine = SimulatorEngine(fixtures, anomaly_specs, seed=42)
        readings, labels = engine.run(start_ts, end_ts)

    Args:
        fixtures:      list of dicts with fixture_id, sensor_id, fixture_type, zone_tier
        anomaly_specs: list of AnomalySpec (injected anomalies)
        seed:          RNG seed for reproducibility (required for labeled test sets)
    """

    def __init__(
        self,
        fixtures:      list[dict[str, str]],
        anomaly_specs: list[AnomalySpec] | None = None,
        seed:          int = 42,
    ):
        self.anomaly_specs = anomaly_specs or []
        self._rng = random.Random(seed)

        self._fixture_sims: list[FixtureSimulator] = []
        for fx in fixtures:
            # Give each fixture its own Random sub-stream to keep them independent
            fx_seed = self._rng.randint(0, 2**31)
            per_fixture_anomalies = [
                s for s in self.anomaly_specs if s.fixture_id == fx["fixture_id"]
            ]
            self._fixture_sims.append(
                FixtureSimulator(
                    fixture_id   = fx["fixture_id"],
                    sensor_id    = fx["sensor_id"],
                    fixture_type = fx["fixture_type"],
                    zone_tier    = fx["zone_tier"],
                    rng          = random.Random(fx_seed),
                    anomaly_specs= per_fixture_anomalies,
                )
            )

    def run(
        self,
        start_ts: datetime,
        end_ts:   datetime,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Run the simulation from start_ts to end_ts (exclusive), emitting one
        reading every READING_INTERVAL_S seconds per fixture.

        Returns:
            readings: list of telemetry_reading dicts (sorted by timestamp)
            labels:   list of ground-truth anomaly label dicts
        """
        readings: list[dict[str, Any]] = []

        ts = start_ts
        while ts < end_ts:
            for sim in self._fixture_sims:
                reading = sim.reading_at(ts)
                if reading is not None:   # None = dropout (no row emitted)
                    readings.append(reading)
            ts += timedelta(seconds=READING_INTERVAL_S)

        # Sort readings by timestamp (mixed fixture outputs are interleaved)
        readings.sort(key=lambda r: r["timestamp"])

        # Ground-truth labels
        labels = [spec.to_label_dict() for spec in self.anomaly_specs]

        return readings, labels
