# Kohler Water Intelligence — Detection Accuracy Report

**Date:** 2026-09-20  
**Test Corpus:** 3-day multi-tier combined dataset (`simulator/output/test_set/combined_telemetry.jsonl`)  
**Baseline Profile:** 14-day prewarm baseline (`simulator/output/prewarm/baseline_profiles.json`)  
**Ground Truth Labels:** `simulator/output/test_set/combined_anomaly_labels.json`  

---

## 1. Executive Summary

With the introduction of the independent trend-based gradual leak detector alongside the EWMA/UCL control chart engine and sensor health diagnostics, the Kohler Detection Engine achieves **perfect 1.000 Recall and 1.000 Precision** against the benchmark dataset.

> [!IMPORTANT]
> **Denominator Clarification on Test Set Size:**  
> The total ground-truth labeled anomaly count across the 3-day test set is **15** (not 14). Previously, under EWMA/UCL alone, 14 True Positives were detected alongside 1 False Negative ($\text{TP} + \text{FN} = 14 + 1 = 15$). The number "14" represented the historical TP count, not the dataset size. With the trend detector now active, all 15 injected anomalies are successfully detected ($\text{TP} = 15, \text{FN} = 0$).

### Headline Performance Metrics

| Metric | EWMA/UCL Only (Phase 2) | With Trend Detector (Current) | PRD §2 Target | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Precision** | **1.000** | **1.000** | $\ge 0.90$ | **PASS** |
| **Recall** | **0.933** | **1.000** | $\ge 0.85$ | **PASS** |
| **F1-Score** | **0.966** | **1.000** | — | **OPTIMAL** |
| **True Positives (TP)** | 14 / 15 | **15 / 15** | — | **All 15 caught** |
| **False Negatives (FN)** | 1 | **0** | — | **Zero missed** |
| **False Positives (FP)** | 0 | **0** | — | **Zero false alarms** |
| **Ordinary Flush FP** | 0 | **0** | — | **0 FP across 403,200 readings** |

---

## 2. Injected Anomaly Breakdown (Total Labeled Anomalies: 15)

The benchmark test set injects 15 distinct anomaly events spanning 5 anomaly categories across 20 hospital fixtures:

| Anomaly Category | Total Ground Truth | Detected (TP) | Missed (FN) | Recall | Mean Latency (s) | Median Latency (s) | Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`gradual_leak`** | 3 | 3 | 0 | **1.000** | 1610.0 | 1200.0 | Previously 2/3 (0.667). Creeping leak on `fix-ot-001` now caught by trend detector. |
| **`sudden_leak`** | 3 | 3 | 0 | **1.000** | 60.0 | 60.0 | Rapid UCL breach detection. |
| **`stuck_valve`** | 3 | 3 | 0 | **1.000** | 220.0 | 180.0 | Extended post-flush continuous flow detection. |
| **`sensor_flatline`** | 3 | 3 | 0 | **1.000** | 0.0 | 0.0 | Diagnostic payload / variance collapse detection. |
| **`sensor_dropout`** | 3 | 3 | 0 | **1.000** | 90.0 | 90.0 | Ingestion gap detection after 120s timeout. |
| **Total** | **15** | **15** | **0** | **1.000** | **396.0** | **90.0** | **15 / 15 Anomalies Detected** |

---

## 3. Ordinary Usage & Noise Rejection (Prewarm Corpus Validation)

To ensure high sensitivity does not induce false alarms during normal hospital operations, the combined detection engine was evaluated across the full 14-day prewarm telemetry dataset:

- **Total Telemetry Readings Processed:** 403,200 readings (20 fixtures $\times$ 14 days $\times$ 1,440 min/day)
- **Total Legitimate Ordinary Flushes:** 3,662 flush cycles
- **Dispatched False Positive Leaks:** **0**
- **Dispatched False Positive Gradual Leak Warnings:** **0**
- **False Positive Rate:** **0.0%**

---

## 4. Detection Architecture Details

1. **EWMA Control Chart (`detection/engine.py`):**
   - Smoothing factor $\lambda = 0.20$.
   - Dynamic thresholding via Upper Control Limit: $\text{UCL} = \mu_{\text{idle}} + k \cdot \sigma_{\text{idle}}$ ($k=3.0$).
2. **Trend-Based Gradual Leak Detector (`detection/trend_detector.py`):**
   - Rolling 120-minute window of idle flow readings.
   - Analytical linear regression slope calculation ($\text{threshold} = 0.001\text{ LPM/min}$).
   - Sub-window mean delta check: recent 25 min vs. reference 35 min ($\Delta\mu \ge 0.08\text{ LPM}$ for warning, $\ge 0.20\text{ LPM}$ for confirmed leak).
   - 15-minute persistence filter before warning dispatch.
   - **Baseline Freeze Protection:** When `is_suspicious` is flagged, the EWMA adaptation loop in `engine.py` freezes adaptation, preventing the creeping micro-leak from being absorbed into the baseline profile.
3. **Sensor Health Tracker (`detection/sensor_health.py`):**
   - Isolates sensor anomalies (dropout, flatline, drift, out-of-range) from plumbing leaks.

---

## 5. Known Limitations

- **Nocturnal Anomaly Coverage on Specific Fixtures (`fix-ot-002` & `fix-ot-003`):**  
  While `fix-ot-001` contains a daytime gradual leak evaluated in the benchmark corpus (`anom-fix-ot-001-gradual_leak-0800`, detected at 48.5 min latency matching pre-shrinkage), the labeled anomaly corpus (`combined_anomaly_labels.json`) contains no injected anomaly events for `fix-ot-002` or `fix-ot-003`. Consequently, empirical detection latency and sensitivity for leaks occurring specifically during the night window (22:00–06:00 UTC) on `fix-ot-002` and `fix-ot-003` cannot be directly scored against ground truth in this benchmark corpus and rely on statistical safety bounds established by empirical Bayes shrinkage ($k = 6,720$).
