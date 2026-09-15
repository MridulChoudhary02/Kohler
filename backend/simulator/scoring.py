"""
simulator/scoring.py — Precision/recall match-scoring for Phase 2 validation.

This module is the single source of truth for how detection events are matched
against ground-truth anomaly labels. It is imported by the Phase 2 detection
engine test harness and must not be changed without a PROMPT_LOG entry.

## Matching rules (verbatim from user spec)

  True positive (TP):
    A detection_event on the SAME fixture_id whose detected_at falls within
    [label.start_timestamp, label.end_timestamp + grace_period], AND whose
    event_type category matches the label's anomaly_type category.

  False positive (FP):
    Any detection_event that cannot be matched to any ground-truth label.

  False negative (FN):
    Any ground-truth label that has no matching detection_event within
    its window + grace_period.

## anomaly_type → event_type category mapping

  sudden_leak, gradual_leak, stuck_valve  →  "leak"
  sensor_flatline, sensor_dropout         →  "sensor_fault"

  Rationale: the detection engine (Phase 2) emits DETECTION_EVENT.event_type
  from the PRD-specified enum {leak, hygiene, sensor_fault}. A single
  ground-truth label of type "sudden_leak" should be matched against a
  detection_event of type "leak" — we don't expect the engine to sub-classify
  the leak mechanism; that's the LLM summarisation layer's job (Phase 7).

## Grace period

  DETECTION_GRACE_PERIOD_MINUTES = 10 (from config.py).
  Set equal to the worst-case (Tier 4) confirmation window so that a correct
  detection that fires at anomaly_start + full_confirmation_window is always
  credited as a TP, regardless of fixture tier.

## Greedy matching

  Each ground-truth label absorbs at most one TP (the detection_event with
  the earliest detected_at inside the window).
  Each detection_event contributes at most one TP.
  This prevents a single continuous anomaly from inflating the TP count.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

# ─── Grace period ─────────────────────────────────────────────────────────────
# This value MUST stay in sync with config.py DETECTION_GRACE_PERIOD_MINUTES.
# It is reproduced here (not imported) so this module can be used as a
# standalone analysis tool without pulling in SQLAlchemy / the app stack.
# If you change this value, change it in config.py too and log it in PROMPT_LOG.
DETECTION_GRACE_PERIOD_MINUTES: int = 10

# ─── Category mapping ─────────────────────────────────────────────────────────
ANOMALY_TYPE_TO_EVENT_TYPE: dict[str, str] = {
    "sudden_leak":     "leak",
    "gradual_leak":    "leak",
    "stuck_valve":     "leak",
    "sensor_flatline": "sensor_fault",
    "sensor_dropout":  "sensor_fault",
}


# ─────────────────────────────────────────────────────────────────────────────
# RESULT DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MatchedPair:
    label:     dict[str, Any]    # ground-truth label dict
    detection: dict[str, Any]    # detection_event dict that matched
    latency_s: float             # detected_at - label.start_timestamp (seconds)


@dataclass
class ScoringResult:
    """
    Full precision/recall result for one evaluation run.
    Includes every TP, FP, FN for downstream analysis.
    """
    true_positives:  list[MatchedPair]        = field(default_factory=list)
    false_positives: list[dict[str, Any]]     = field(default_factory=list)
    false_negatives: list[dict[str, Any]]     = field(default_factory=list)
    grace_period_minutes: int                 = DETECTION_GRACE_PERIOD_MINUTES

    @property
    def tp(self) -> int: return len(self.true_positives)
    @property
    def fp(self) -> int: return len(self.false_positives)
    @property
    def fn(self) -> int: return len(self.false_negatives)

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        denom = self.precision + self.recall
        return 2 * self.precision * self.recall / denom if denom > 0 else 0.0

    @property
    def mean_detection_latency_s(self) -> float:
        if not self.true_positives:
            return float("nan")
        return sum(p.latency_s for p in self.true_positives) / len(self.true_positives)

    def summary(self) -> str:
        lines = [
            f"  Precision : {self.precision:.3f}  (target ≥ 0.90, PRD §2)",
            f"  Recall    : {self.recall:.3f}  (target ≥ 0.85, PRD §2)",
            f"  F1        : {self.f1:.3f}",
            f"  TP={self.tp}  FP={self.fp}  FN={self.fn}",
            f"  Mean detection latency: {self.mean_detection_latency_s:.1f}s",
            f"  Grace period applied: {self.grace_period_minutes} min",
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialisable form for writing to JSON reports."""
        return {
            "precision":   self.precision,
            "recall":      self.recall,
            "f1":          self.f1,
            "tp":          self.tp,
            "fp":          self.fp,
            "fn":          self.fn,
            "mean_detection_latency_s": self.mean_detection_latency_s,
            "grace_period_minutes": self.grace_period_minutes,
            "true_positives": [
                {
                    "anomaly_id":   p.label["anomaly_id"],
                    "fixture_id":   p.label["fixture_id"],
                    "anomaly_type": p.label["anomaly_type"],
                    "detection_id": p.detection.get("event_id", ""),
                    "detected_at":  p.detection.get("detected_at", ""),
                    "latency_s":    p.latency_s,
                }
                for p in self.true_positives
            ],
            "false_positives": [
                {
                    "event_id":    d.get("event_id", ""),
                    "fixture_id":  d.get("fixture_id", ""),
                    "event_type":  d.get("event_type", ""),
                    "detected_at": d.get("detected_at", ""),
                    "confidence":  d.get("confidence_score", 0.0),
                }
                for d in self.false_positives
            ],
            "false_negatives": [
                {
                    "anomaly_id":   lbl["anomaly_id"],
                    "fixture_id":   lbl["fixture_id"],
                    "anomaly_type": lbl["anomaly_type"],
                    "start":        lbl["start_timestamp"],
                    "end":          lbl["end_timestamp"],
                }
                for lbl in self.false_negatives
            ],
        }


# ─────────────────────────────────────────────────────────────────────────────
# MATCHING ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _parse_ts(s: str) -> datetime:
    """Parse ISO-8601 string to UTC-aware datetime."""
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def match_detections_to_labels(
    detection_events: list[dict[str, Any]],
    ground_truth_labels: list[dict[str, Any]],
    grace_period_minutes: int | None = None,
) -> ScoringResult:
    """
    Match detection_events against ground_truth_labels and compute
    precision, recall, F1, and per-pair latency.

    Args:
        detection_events:    List of detection_event dicts (from the detection
                             engine). Required keys: fixture_id, event_type,
                             detected_at, event_id, confidence_score.
        ground_truth_labels: List of anomaly label dicts (from anomaly_labels.json).
                             Required keys: anomaly_id, fixture_id, anomaly_type,
                             start_timestamp, end_timestamp.
        grace_period_minutes: Override for DETECTION_GRACE_PERIOD_MINUTES.
                              Defaults to the config value.

    Returns:
        ScoringResult with TP list, FP list, FN list, precision, recall, F1.
    """
    grace_min = grace_period_minutes if grace_period_minutes is not None \
                else DETECTION_GRACE_PERIOD_MINUTES
    grace = timedelta(minutes=grace_min)

    result = ScoringResult(grace_period_minutes=grace_min)

    # Index labels by fixture_id for fast lookup
    labels_by_fixture: dict[str, list[dict]] = {}
    for lbl in ground_truth_labels:
        labels_by_fixture.setdefault(lbl["fixture_id"], []).append(lbl)

    # Sort detections chronologically so greedy earliest-match is correct
    detections_sorted = sorted(detection_events, key=lambda d: d.get("detected_at", ""))

    # Track which labels and detections have been consumed
    matched_label_ids:     set[str] = set()
    matched_detection_ids: set[str] = set()

    # --- TP / FP pass ---
    for det in detections_sorted:
        det_fixture   = det.get("fixture_id", "")
        det_type      = det.get("event_type", "")       # "leak" | "sensor_fault" | "hygiene"
        det_ts        = _parse_ts(det.get("detected_at", "1970-01-01T00:00:00Z"))
        det_id        = det.get("event_id", id(det))    # fallback to object id

        candidate_labels = labels_by_fixture.get(det_fixture, [])
        matched = False

        for lbl in candidate_labels:
            lbl_id = lbl["anomaly_id"]
            if lbl_id in matched_label_ids:
                continue  # already absorbed

            # Category check
            expected_event_type = ANOMALY_TYPE_TO_EVENT_TYPE.get(lbl["anomaly_type"], "")
            if det_type != expected_event_type:
                continue

            # Window check: detected_at ∈ [start, end + grace]
            window_start = _parse_ts(lbl["start_timestamp"])
            window_end   = _parse_ts(lbl["end_timestamp"]) + grace

            if window_start <= det_ts <= window_end:
                latency_s = (det_ts - window_start).total_seconds()
                result.true_positives.append(MatchedPair(
                    label=lbl, detection=det, latency_s=latency_s
                ))
                matched_label_ids.add(lbl_id)
                matched_detection_ids.add(str(det_id))
                matched = True
                break   # greedy: stop at first match

        if not matched:
            result.false_positives.append(det)

    # --- FN pass: labels with no matching detection ---
    for lbl in ground_truth_labels:
        if lbl["anomaly_id"] not in matched_label_ids:
            result.false_negatives.append(lbl)

    return result


def score_from_files(
    detections_path: str,
    labels_path: str,
    grace_period_minutes: int | None = None,
) -> ScoringResult:
    """
    Convenience wrapper: loads detections and labels from JSON files
    and returns a ScoringResult. Handles both JSONL (detections) and
    JSON (labels).
    """
    import json

    # Labels file: { "anomalies": [...] } or plain list
    with open(labels_path) as f:
        raw = json.load(f)
    labels = raw["anomalies"] if isinstance(raw, dict) and "anomalies" in raw else raw

    # Detections file: JSONL (one dict per line) or JSON list
    detections: list[dict] = []
    with open(detections_path) as f:
        content = f.read().strip()
    if content.startswith("["):
        detections = json.loads(content)
    else:
        for line in content.splitlines():
            line = line.strip()
            if line:
                detections.append(json.loads(line))

    return match_detections_to_labels(detections, labels, grace_period_minutes)
