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
    Any detection_event that cannot be matched to any ground-truth label
    AND is not a redundant detection (see below).

  False negative (FN):
    Any ground-truth label that has no matching detection_event within
    its window + grace_period.

  Redundant detection (RD):
    A detection_event that WOULD qualify as a TP (correct fixture, category,
    and timestamp window) but the matching label has already been absorbed by
    an earlier detection. Logged separately; excluded from TP, FP, FN counts
    so they cannot distort precision or recall.
    Use: a high redundant_detections count indicates an engine that re-fires
    on the same event (implementation smell, useful for Phase 2 diagnostics).

## De-duplication

  Two-pass inner loop per detection:
    Pass 1 — try unconsumed labels (yields TP if matched).
    Pass 2 — if pass 1 found no match, check already-consumed labels.
             If one matches → RD. If none match → FP.

  Each label absorbs at most ONE TP (greedy earliest-detected_at wins).
  Each detection contributes at most ONE outcome (TP | RD | FP).
  Precision denominator = TP + FP  (RD is excluded by design).

## anomaly_type → event_type category mapping

  sudden_leak, gradual_leak, stuck_valve  →  "leak"
  sensor_flatline, sensor_dropout         →  "sensor_fault"

  Rationale: the detection engine (Phase 2) emits DETECTION_EVENT.event_type
  from the PRD-specified enum {leak, hygiene, sensor_fault}. A single
  ground-truth label of type "sudden_leak" should be matched against a
  detection_event of type "leak" — we don't expect the engine to sub-classify
  the leak mechanism; that's the LLM summarisation layer's job (Phase 7).

## Grace period

  DETECTION_GRACE_PERIOD_MINUTES = 10 (mirrors config.py).
  Set equal to the worst-case (Tier 4) confirmation window so that a correct
  detection that fires at anomaly_start + full_confirmation_window is always
  credited as a TP, regardless of fixture tier.

## Time-to-detection latency

  For every TP: latency_s = detected_at − label.start_timestamp (seconds).
  ScoringResult exposes mean_detection_latency_s and median_detection_latency_s.
  Both are included in summary() and to_dict().
  Median is more robust when a single late detection (e.g. gradual_leak caught
  very late) would otherwise inflate the mean.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

# ─── Grace period ─────────────────────────────────────────────────────────────
# This value MUST stay in sync with config.py DETECTION_GRACE_PERIOD_MINUTES.
# Reproduced here (not imported) so this module works without pulling in the
# full app stack (SQLAlchemy, FastAPI, etc.).
# If you change this value, change it in config.py too and log in PROMPT_LOG.
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
    label:     dict[str, Any]   # ground-truth label dict
    detection: dict[str, Any]   # detection_event dict that matched
    latency_s: float            # detected_at − label.start_timestamp (seconds)


@dataclass
class ScoringResult:
    """
    Full precision/recall result for one evaluation run.
    Includes every TP, FP, FN, and RD for downstream analysis.
    """
    true_positives:      list[MatchedPair]    = field(default_factory=list)
    false_positives:     list[dict[str, Any]] = field(default_factory=list)
    false_negatives:     list[dict[str, Any]] = field(default_factory=list)
    redundant_detections: list[dict[str, Any]] = field(default_factory=list)
    grace_period_minutes: int                  = DETECTION_GRACE_PERIOD_MINUTES

    # ── Counts ────────────────────────────────────────────────────────────────
    @property
    def tp(self) -> int: return len(self.true_positives)
    @property
    def fp(self) -> int: return len(self.false_positives)
    @property
    def fn(self) -> int: return len(self.false_negatives)
    @property
    def rd(self) -> int: return len(self.redundant_detections)

    # ── Metrics ───────────────────────────────────────────────────────────────
    @property
    def precision(self) -> float:
        # Denominator = TP + FP only; RD excluded by design (see module docstring)
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

    # ── Latency ───────────────────────────────────────────────────────────────
    @property
    def mean_detection_latency_s(self) -> float:
        if not self.true_positives:
            return float("nan")
        return sum(p.latency_s for p in self.true_positives) / self.tp

    @property
    def median_detection_latency_s(self) -> float:
        if not self.true_positives:
            return float("nan")
        latencies = sorted(p.latency_s for p in self.true_positives)
        n = len(latencies)
        mid = n // 2
        return latencies[mid] if n % 2 else (latencies[mid - 1] + latencies[mid]) / 2.0

    # ── Reporting ─────────────────────────────────────────────────────────────
    def summary(self) -> str:
        lines = [
            f"  Precision  : {self.precision:.3f}  (target ≥ 0.90, PRD §2)",
            f"  Recall     : {self.recall:.3f}  (target ≥ 0.85, PRD §2)",
            f"  F1         : {self.f1:.3f}",
            f"  TP={self.tp}  FP={self.fp}  FN={self.fn}  RD={self.rd}",
            f"  Mean latency  : {self.mean_detection_latency_s:.1f}s",
            f"  Median latency: {self.median_detection_latency_s:.1f}s",
            f"  Grace period  : {self.grace_period_minutes} min",
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialisable form for writing to JSON reports."""
        return {
            "precision":              self.precision,
            "recall":                 self.recall,
            "f1":                     self.f1,
            "tp":                     self.tp,
            "fp":                     self.fp,
            "fn":                     self.fn,
            "rd":                     self.rd,
            "mean_detection_latency_s":   self.mean_detection_latency_s,
            "median_detection_latency_s": self.median_detection_latency_s,
            "grace_period_minutes":   self.grace_period_minutes,
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
            "redundant_detections": [
                {
                    "event_id":    d.get("event_id", ""),
                    "fixture_id":  d.get("fixture_id", ""),
                    "event_type":  d.get("event_type", ""),
                    "detected_at": d.get("detected_at", ""),
                    "confidence":  d.get("confidence_score", 0.0),
                }
                for d in self.redundant_detections
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


def _label_window(lbl: dict, grace: timedelta) -> tuple[datetime, datetime]:
    return (_parse_ts(lbl["start_timestamp"]),
            _parse_ts(lbl["end_timestamp"]) + grace)


def _category_matches(lbl: dict, det_type: str) -> bool:
    return ANOMALY_TYPE_TO_EVENT_TYPE.get(lbl["anomaly_type"], "") == det_type


def match_detections_to_labels(
    detection_events:    list[dict[str, Any]],
    ground_truth_labels: list[dict[str, Any]],
    grace_period_minutes: int | None = None,
) -> ScoringResult:
    """
    Match detection_events against ground_truth_labels and compute
    precision, recall, F1, latency, and redundant-detection count.

    Args:
        detection_events:    List of detection_event dicts. Required keys:
                             fixture_id, event_type, detected_at, event_id,
                             confidence_score.
        ground_truth_labels: List of anomaly label dicts (from anomaly_labels.json).
                             Required keys: anomaly_id, fixture_id, anomaly_type,
                             start_timestamp, end_timestamp.
        grace_period_minutes: Override for DETECTION_GRACE_PERIOD_MINUTES.

    Returns:
        ScoringResult with TP, FP, FN, RD lists, precision, recall, F1,
        mean and median latency.
    """
    grace_min = grace_period_minutes if grace_period_minutes is not None \
                else DETECTION_GRACE_PERIOD_MINUTES
    grace = timedelta(minutes=grace_min)

    result = ScoringResult(grace_period_minutes=grace_min)

    # Index labels by fixture_id for fast lookup
    labels_by_fixture: dict[str, list[dict]] = {}
    for lbl in ground_truth_labels:
        labels_by_fixture.setdefault(lbl["fixture_id"], []).append(lbl)

    # Sort detections chronologically: greedy earliest-match requires this
    detections_sorted = sorted(detection_events, key=lambda d: d.get("detected_at", ""))

    # Track consumed labels
    matched_label_ids: set[str] = set()

    # ── TP / RD / FP pass ────────────────────────────────────────────────────
    for det in detections_sorted:
        det_fixture = det.get("fixture_id", "")
        det_type    = det.get("event_type", "")
        det_ts      = _parse_ts(det.get("detected_at", "1970-01-01T00:00:00Z"))

        candidate_labels = labels_by_fixture.get(det_fixture, [])

        # ── Pass 1: try to match an unconsumed label ──────────────────────────
        tp_found = False
        for lbl in candidate_labels:
            lbl_id = lbl["anomaly_id"]
            if lbl_id in matched_label_ids:
                continue                          # already absorbed — skip in pass 1
            if not _category_matches(lbl, det_type):
                continue
            win_start, win_end = _label_window(lbl, grace)
            if win_start <= det_ts <= win_end:
                latency_s = (det_ts - win_start).total_seconds()
                result.true_positives.append(MatchedPair(
                    label=lbl, detection=det, latency_s=latency_s
                ))
                matched_label_ids.add(lbl_id)
                tp_found = True
                break   # greedy: first unconsumed match wins

        if tp_found:
            continue

        # ── Pass 2: check if it would match a consumed label (→ RD, not FP) ──
        rd_found = False
        for lbl in candidate_labels:
            lbl_id = lbl["anomaly_id"]
            if lbl_id not in matched_label_ids:
                continue                          # unconsumed — already tried in pass 1
            if not _category_matches(lbl, det_type):
                continue
            win_start, win_end = _label_window(lbl, grace)
            if win_start <= det_ts <= win_end:
                result.redundant_detections.append(det)
                rd_found = True
                break

        if not rd_found:
            result.false_positives.append(det)

    # ── FN pass: labels with no matching detection ────────────────────────────
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
    Convenience wrapper: loads detections and labels from files and returns
    a ScoringResult. Handles both JSONL (one dict per line) and JSON list
    for detections; JSON with {"anomalies": [...]} wrapper or plain list for labels.
    """
    import json

    with open(labels_path) as f:
        raw = json.load(f)
    labels = raw["anomalies"] if isinstance(raw, dict) and "anomalies" in raw else raw

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
