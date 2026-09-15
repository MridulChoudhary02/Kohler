"""
detection/engine.py — Phase 2 detection engine (PRD §§7.1–7.6).

Processes telemetry readings in chronological order.
Maintains one FixtureDetectionState per fixture.
Emits detection_event dicts when anomalies are confirmed.

## Signal pipeline (per reading)

  1. Sensor flatline (§7.6a): diagnostic_status == "flatline"
     → Emit "sensor_fault" immediately (no confirmation window).
     → Suppress further processing for this reading.

  2. Dropout detection (§7.6b): gap in readings > SENSOR_DROPOUT_GAP_S
     → Emitted by process_reading() when it detects a gap vs last_reading_ts.

  3. Flush suppression: flush_event == 1
     → Record last_flush_ts. Skip EWMA update.
     → Post-flush grace window: readings within POST_FLUSH_GRACE_S seconds of
        last_flush_ts are excluded from EWMA updates and candidate starts.

  4. Occupancy cross-check (§7.3): occupancy_state == 1
     → Reset candidate timer. Skip EWMA update.
     → The leak must be detectable as idle flow; active use masks it.

  5. Idle-flow EWMA update (§7.2):
     → ewma = λ × flow + (1−λ) × ewma
     → If ewma > UCL: start/extend candidate timer.
     → If ewma ≤ UCL: reset candidate timer.

  6. Confirmation + dispatch (§7.2, §7.5):
     → When candidate has been active ≥ confirmation_window[tier]:
        compute confidence, emit detection_event if ≥ CONFIDENCE_LOG_ONLY.

## Confidence formula (§7.5)

  dev_norm  = clamp((ewma − ucl) / max(ucl − mean, ε), 0, 1)
  confidence = W1 × dev_norm + W2 × 1.0 + W3 × 1.0
  (W2 and W3 are always 1.0 at dispatch time because occupancy=0 and
  not-in-post-flush are preconditions for reaching the dispatch check.)

## Dispatch rules

  confidence < CONFIDENCE_LOG_ONLY  → discard (noise)
  CONFIDENCE_LOG_ONLY ≤ c < 0.80   → status="logged"  (warmup_complete may be False)
  confidence ≥ 0.80 AND warmup_complete → status="dispatched"
  confidence ≥ 0.80 AND NOT warmup_complete → status="logged"  (suppressed per §7.1)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from detection.baseline import BaselineProfile
from detection.state import FixtureDetectionState
from detection.sensor_health import SensorHealthTracker
from detection.hygiene import HygieneTracker

# ── Config constants (mirrored; keep in sync with app/core/config.py) ─────────
EWMA_LAMBDA                 = 0.2
UCL_L_FACTOR                = 3.0
W1, W2, W3                  = 0.40, 0.35, 0.25
CONFIDENCE_LOG_ONLY         = 0.50
CONFIDENCE_ESCALATE         = 0.80
POST_FLUSH_GRACE_S          = 60
SENSOR_DROPOUT_GAP_S        = 120
DEBOUNCE_BELOW_UCL_READINGS = 4    # N=4 consecutive readings (2 min) at/below UCL to re-arm suppression
CONFIRMATION_WINDOWS        = {    # tier → seconds
    "Tier 1": 3  * 60,
    "Tier 2": 5  * 60,
    "Tier 3": 7  * 60,
    "Tier 4": 10 * 60,
}


def _parse_ts(s: str | datetime) -> datetime:
    if isinstance(s, datetime):
        dt = s
    else:
        dt = datetime.fromisoformat(str(s))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _make_event(
    fixture_id:     str,
    sensor_id:      str,
    zone_tier:      str,
    event_type:     str,         # "leak" | "sensor_fault" | "hygiene"
    detected_at:    datetime,
    candidate_start: Optional[datetime],
    confidence:     float,
    ewma:           float,
    ucl:            float,
    warmup_complete: bool,
    status:         str,         # "logged" | "dispatched"
    extra:          dict | None = None,
) -> dict[str, Any]:
    return {
        "event_id":          str(uuid.uuid4()),
        "fixture_id":        fixture_id,
        "sensor_id":         sensor_id,
        "zone_tier":         zone_tier,
        "event_type":        event_type,
        "detected_at":       detected_at.isoformat(),
        "candidate_start":   candidate_start.isoformat() if candidate_start else None,
        "confidence_score":  round(confidence, 4),
        "ewma_at_detection": round(ewma, 6),
        "ucl":               round(ucl, 6),
        "status":            status,
        "warmup_complete":   warmup_complete,
        **(extra or {}),
    }


class DetectionEngine:
    """
    Stateful detection engine for all fixtures.
    Call process_reading() for each telemetry reading (must be in timestamp order).
    Call finalize(end_ts) after the last reading to flush any trailing dropout events.
    """

    def __init__(
        self,
        baseline_profiles: dict[str, BaselineProfile],
        fixture_info:      list[dict[str, str]],   # [{fixture_id, sensor_id, fixture_type, zone_tier}]
    ):
        self._baselines: dict[str, BaselineProfile] = baseline_profiles
        self._fixture_meta: dict[str, dict] = {f["fixture_id"]: f for f in fixture_info}

        # Initialise per-fixture state, sensor health trackers, and hygiene trackers
        self._states: dict[str, FixtureDetectionState] = {}
        self._sensor_health: dict[str, SensorHealthTracker] = {}
        self._hygiene: dict[str, HygieneTracker] = {}

        for fid, meta in self._fixture_meta.items():
            bp   = baseline_profiles.get(fid)
            sid  = meta.get("sensor_id", fid)
            tier = meta.get("zone_tier", "Tier 4")

            self._states[fid] = FixtureDetectionState(
                fixture_id   = fid,
                zone_tier    = tier,
                fixture_type = meta.get("fixture_type", "faucet"),
                ewma         = bp.initial_ewma if bp else 0.0,
            )
            self._sensor_health[sid] = SensorHealthTracker(sensor_id=sid, fixture_id=fid, zone_tier=tier)
            self._hygiene[fid]       = HygieneTracker(fixture_id=fid, zone_tier=tier)

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────────────

    def process_reading(self, reading: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Process one telemetry reading. Returns a (possibly empty) list of
        detection_event dicts produced by this reading.
        """
        events: list[dict[str, Any]] = []

        fid = reading.get("fixture_id", "")
        if fid not in self._states:
            return events

        state = self._states[fid]
        bp    = self._baselines.get(fid)
        if bp is None:
            return events

        ts             = _parse_ts(reading["timestamp"])
        flow           = float(reading.get("flow_rate_lpm", 0.0))
        occupancy      = int(reading.get("occupancy_state", 0))
        flush_evt      = int(reading.get("flush_event", 0))
        diag_status    = reading.get("diagnostic_status", "ok")
        sensor_id      = reading.get("sensor_id", "")

        # ── Sensor Health Scoring & Maintenance Ticket (§9) ───────────────────
        health_tracker = self._sensor_health.get(sensor_id)
        health_score   = 1.0
        if health_tracker:
            health_score, maint_event = health_tracker.process_reading(reading)
            if maint_event:
                events.append(maint_event)

        # ── Hygiene Threshold Prediction (§8) ─────────────────────────────────
        hygiene_tracker = self._hygiene.get(fid)
        if hygiene_tracker:
            hyg_event = hygiene_tracker.process_reading(reading, warmup_complete=bp.warmup_complete)
            if hyg_event:
                events.append(hyg_event)

        # ── 0. Dropout check: gap vs. previous reading ────────────────────────
        if state.last_reading_ts is not None:
            gap_s = (ts - state.last_reading_ts).total_seconds()
            if gap_s > SENSOR_DROPOUT_GAP_S and not state.in_dropout_episode:
                dropout_at = state.last_reading_ts + timedelta(seconds=SENSOR_DROPOUT_GAP_S)
                ev = self._make_sensor_fault(
                    state, sensor_id, dropout_at,
                    sub_type="sensor_dropout", bp=bp, health_score=health_score,
                )
                events.append(ev)
                state.in_dropout_episode = True
        if state.in_dropout_episode and (state.last_reading_ts is None
                                          or (ts - state.last_reading_ts).total_seconds()
                                          <= SENSOR_DROPOUT_GAP_S):
            state.in_dropout_episode = False   # readings resumed

        state.last_reading_ts = ts

        # ── 1. Sensor flatline ────────────────────────────────────────────────
        if diag_status == "flatline":
            if not state.in_flatline_episode:
                ev = self._make_sensor_fault(state, sensor_id, ts, "sensor_flatline", bp, health_score=health_score)
                events.append(ev)
                state.in_flatline_episode = True
            state.candidate_start_ts = None   # reset any pending leak candidate
            return events
        else:
            state.in_flatline_episode = False

        # ── 2. Record flush event (§7.4) ──────────────────────────────────────
        if flush_evt == 1:
            state.last_flush_ts          = ts
            state.pending_flush_start_ts = ts
            state.stuck_valve_dispatched = False
            state.candidate_start_ts     = None   # flush resets any candidate
            return events

        # ── 2b. Section 7.4 Stuck-valve fast-path check ───────────────────────
        if state.pending_flush_start_ts is not None:
            is_near_idle = (flow <= (bp.mean_idle_flow + 3.0 * bp.std_idle_flow)) or (flow <= 0.10)
            if is_near_idle:
                state.pending_flush_start_ts = None   # returned to baseline normally
            else:
                elapsed_flush_s = (ts - state.pending_flush_start_ts).total_seconds()
                stuck_window_s  = max(bp.mean_flush_duration_s + 2.0 * bp.std_flush_duration_s, 10.0)
                if elapsed_flush_s >= stuck_window_s:
                    if not state.stuck_valve_dispatched:
                        # Flow failed to return to baseline after flush within learned window
                        confidence = 0.95   # high-confidence leak event (§7.4 fast path)
                        status     = "dispatched" if (bp.warmup_complete and health_score >= 0.60) else "logged"
                        ev = _make_event(
                            fixture_id      = fid,
                            sensor_id       = sensor_id,
                            zone_tier       = state.zone_tier,
                            event_type      = "leak",
                            detected_at     = ts,
                            candidate_start = state.pending_flush_start_ts,
                            confidence      = confidence,
                            ewma            = flow,
                            ucl             = bp.ucl,
                            warmup_complete = bp.warmup_complete,
                            status          = status,
                            extra           = {"sub_type": "stuck_valve"},
                        )
                        events.append(ev)
                        state.stuck_valve_dispatched = True
                    state.pending_flush_start_ts = None

        # ── 3. Post-flush suppression (for Signal 1 normal EWMA path) ─────────
        in_post_flush = (
            state.last_flush_ts is not None
            and (ts - state.last_flush_ts).total_seconds() < POST_FLUSH_GRACE_S
        )
        if in_post_flush:
            state.candidate_start_ts = None
            return events

        # ── 4. Occupancy cross-check (§7.3) ───────────────────────────────────
        if occupancy == 1:
            # Signal 2: active use masks leak (Note: in high-traffic zones where
            # occupancy is continuously 1, candidate timer will be repeatedly reset,
            # creating a potential recall risk in non-stop occupied areas;
            # noted design tradeoff for future refinement).
            state.candidate_start_ts = None
            return events

        # ── 5. Idle-flow EWMA update ──────────────────────────────────────────
        if diag_status != "ok":
            return events   # other diagnostic states: skip

        state.ewma = EWMA_LAMBDA * flow + (1.0 - EWMA_LAMBDA) * state.ewma

        ucl = bp.ucl
        if state.ewma <= ucl:
            state.candidate_start_ts = None
            state.consecutive_below_ucl_readings += 1
            if state.consecutive_below_ucl_readings >= DEBOUNCE_BELOW_UCL_READINGS:
                state.suppress_until_below_ucl = False
            return events

        state.consecutive_below_ucl_readings = 0

        if state.suppress_until_below_ucl:
            return events   # already emitted for this breach episode

        # ── 6. Candidate timer ────────────────────────────────────────────────
        if state.candidate_start_ts is None:
            state.candidate_start_ts = ts

        elapsed_s = (ts - state.candidate_start_ts).total_seconds()
        confirm_s = CONFIRMATION_WINDOWS.get(state.zone_tier, 600)

        if elapsed_s < confirm_s:
            return events   # not confirmed yet

        # ── 7. Confirmed: compute confidence and emit ─────────────────────────
        dev_norm = (state.ewma - ucl) / max(ucl - bp.mean_idle_flow, 1e-6)
        dev_norm = max(0.0, min(dev_norm, 1.0))
        # occ_score = 1.0 (we are here only when occupancy=0)
        # pf_score  = 1.0 (we are here only when not in_post_flush)
        confidence = W1 * dev_norm + W2 * 1.0 + W3 * 1.0

        if confidence < CONFIDENCE_LOG_ONLY:
            state.candidate_start_ts = None
            return events

        if confidence >= CONFIDENCE_ESCALATE and bp.warmup_complete and health_score >= 0.60:
            status = "dispatched"
        else:
            status = "logged"

        ev = _make_event(
            fixture_id      = fid,
            sensor_id       = sensor_id,
            zone_tier       = state.zone_tier,
            event_type      = "leak",
            detected_at     = ts,
            candidate_start = state.candidate_start_ts,
            confidence      = confidence,
            ewma            = state.ewma,
            ucl             = ucl,
            warmup_complete = bp.warmup_complete,
            status          = status,
        )
        events.append(ev)
        state.candidate_start_ts = None   # reset so next confirmation is independent
        state.suppress_until_below_ucl = True

        return events

    def process_batch(self, readings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Process a sorted list of readings; return all emitted events."""
        all_events: list[dict[str, Any]] = []
        for reading in readings:
            all_events.extend(self.process_reading(reading))
        return all_events

    def finalize(self, end_ts: datetime) -> list[dict[str, Any]]:
        """
        Called after the last reading to emit any trailing dropout events
        (fixtures that went silent before end_ts).
        """
        events: list[dict[str, Any]] = []
        for fid, state in self._states.items():
            if state.last_reading_ts is None:
                continue
            gap_s = (end_ts - state.last_reading_ts).total_seconds()
            if gap_s > SENSOR_DROPOUT_GAP_S and not state.in_dropout_episode:
                bp        = self._baselines.get(fid)
                sensor_id = self._fixture_meta.get(fid, {}).get("sensor_id", "")
                dropout_at = state.last_reading_ts + timedelta(seconds=SENSOR_DROPOUT_GAP_S)
                ev = self._make_sensor_fault(state, sensor_id, dropout_at,
                                             "sensor_dropout", bp)
                events.append(ev)
        return events

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _make_sensor_fault(
        self,
        state:     FixtureDetectionState,
        sensor_id: str,
        detected_at: datetime,
        sub_type:  str,
        bp:        Optional[BaselineProfile],
        health_score: float = 0.0,
    ) -> dict[str, Any]:
        warmup = bp.warmup_complete if bp else False
        # Sensor faults are dispatched regardless of warmup (a dead sensor is
        # always critical) but we still log the warmup flag for transparency.
        status = "dispatched"
        return _make_event(
            fixture_id      = state.fixture_id,
            sensor_id       = sensor_id,
            zone_tier       = state.zone_tier,
            event_type      = "sensor_fault",
            detected_at     = detected_at,
            candidate_start = None,
            confidence      = 1.0,   # sensor faults are binary
            ewma            = state.ewma,
            ucl             = bp.ucl if bp else 0.0,
            warmup_complete = warmup,
            status          = status,
            extra           = {"sub_type": sub_type, "sensor_health_score": round(health_score, 4)},
        )
