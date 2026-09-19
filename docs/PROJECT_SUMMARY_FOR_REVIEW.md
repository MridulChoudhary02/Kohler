# Kohler Smart Facility & Sustainability Manager (Hospital Deployment Edition)
## Comprehensive Technical Summary for External AI Review & Critique

**Repository:** `MridulChoudhary02/Kohler`  
**Current Branch:** `docs/project-summary-review`  
**Latest Main Commit:** `8212979`  
**Evaluation Date:** September 19, 2026  

---

## 1. Project Goal & Scope

> *Excerpted directly from `PRD_Kohler_Track2_Hospital.md` (Sections 1–3):*

Hospitals run water and sanitary fixtures continuously, at high volume, across zones with very different risk profiles — an ICU restroom, an operating theatre scrub station, and a visitor lobby restroom are not interchangeable in either water-criticality or hygiene-criticality. Today, leaks are caught by chance (a nurse notices, a bill spikes) and cleaning is scheduled on a fixed calendar rather than actual usage. Both waste water and staff time, and in a hospital, hygiene lapses carry infection-control risk, not just inconvenience.

This system continuously ingests fixture-level telemetry, distinguishes real anomalies from sensor noise and normal usage variance, and turns high-confidence detections into prioritized, explainable maintenance tickets — before the facility team would otherwise notice.

**Core Quantitative Goals:**
- **Leak Detection Accuracy:** Precision $\ge 90\%$, Recall $\ge 85\%$ on synthetic leak-injection test set.
- **Predictive Hygiene:** Median lead time $\ge 30\text{ min}$ before threshold breach.
- **Sensor Health Isolation:** Sensor-health false-attribution rate $< 5\%$.
- **SLA Routing:** Priority scoring aligned to 4 hospital zone criticality tiers with auto-escalation on SLA breach.
- **Sustainability Accounting:** Live-running counter tracking estimated litres wasted, cost at risk (₹), and carbon footprint ($\text{kg CO}_2\text{e}$).

**Non-Goals (v1):**
- No physical hardware integration (telemetry is simulated but strictly schema-compatible with standard IoT payloads).
- No patient-data / EHR integration (touches only facility plumbing telemetry).
- No native mobile app (responsive web dashboard).
- No billing/procurement workflows (lifecycle stops at ticket dispatch and resolution tracking).

---

## 2. Architecture Overview

### Technology Stack (Verified via Repository Manifests)

| Component | Technology | Version | Purpose |
|---|---|---|---|
| **API Framework** | FastAPI | `0.111.0` | Async REST endpoints, Pydantic schemas, dependency injection |
| **ASGI Server** | Uvicorn (standard) | `0.29.0` | Async HTTP runtime |
| **Database** | PostgreSQL | `16` / Local Docker | Relational store for facility, telemetry, events, tickets |
| **ORM** | SQLAlchemy (asyncio) | `2.0.30` | Async session management and declarative relational models |
| **DB Drivers** | `asyncpg` / `psycopg2-binary` | `0.29.0` / `2.9.9` | Async API queries and sync migration driver |
| **Migrations** | Alembic | `1.13.1` | Schema versioning (5 revision migrations applied) |
| **Data Validation** | Pydantic / Pydantic-Settings | `2.7.1` / `2.2.1` | Request/response DTOs, strictly typed application config |
| **Scientific / Math**| NumPy / SciPy | `1.26.4` / `1.13.0` | Statistical baselining, EWMA calculations |
| **LLM Gateway** | LiteLLM | `1.40.0` | Unified provider interface to Groq free-tier models |
| **Testing** | Pytest / Pytest-Asyncio | `8.2.0` / `0.23.6` | 20 unit/integration tests with async HTTP test client |
| **Frontend Framework**| Next.js (App Router) | `14.2.5` | React Server Components & client UI |
| **Frontend UI/CSS** | Tailwind CSS / Radix UI | `3.4.19` / Slot `1.3.3` | Linear/Vercel dark theme, custom CSS variables |
| **Icons** | Lucide React | `0.424.0` | SVG iconography |
| **Language Runtime**| TypeScript / Python | `5.5.4` / `3.14.0` | Strict static typing on frontend and backend |

### Alembic Migration History (`backend/alembic/versions/`)
1. `0001_initial_schema.py` — Core domain tables (`facilities`, `zones`, `fixtures`, `sensors`, `telemetry_readings`, `baseline_profiles`, `detection_events`, `hygiene_counters`, `tickets`, `technicians`, `sla_policies`).
2. `0002_baseline_warmup_flag.py` — Added `warmup_complete` boolean to `baseline_profiles`.
3. `0003_ticket_timestamps.py` — Added SLA tracking fields (`acknowledged_at`, `resolved_at`, `summary_text`).
4. `0004_ticket_escalated_flag.py` — Added `escalated` boolean flag for SLA breach auto-escalation.
5. `0005_ticket_started_at.py` — Added `started_at` timestamp for `in_progress` transition.

### Directory Structure (`find . -maxdepth 3 -type d`)
```
.
├── backend
│   ├── alembic
│   │   └── versions
│   ├── app
│   │   ├── api
│   │   ├── core
│   │   ├── models
│   │   └── services
│   ├── detection
│   │   └── tests
│   ├── scripts
│   └── simulator
│       └── output
├── docs
└── frontend
    └── src
        ├── app
        ├── components
        └── lib
```

---

## 3. Detection Logic (Formulas & Constants)

All detection logic is encapsulated in `backend/detection/` and configuration constants in `backend/app/core/config.py`.

### 3.1. Baseline Profile Learning (`detection/baseline.py`)
Each fixture maintains a learned statistical profile across historical non-flush, unoccupied idle windows:
- $\mu_{\text{idle}}$, $\sigma_{\text{idle}}$: Mean and standard deviation of idle flow rate ($\text{LPM}$).
- $\mu_{\text{dur}}$, $\sigma_{\text{dur}}$: Mean and standard deviation of flush duration ($\text{seconds}$).
- $\mu_{\text{vol}}$, $\sigma_{\text{vol}}$: Mean and standard deviation of flush volume ($\text{Litres}$).
- **Upper Control Limit (UCL):**
  $$\text{UCL} = \mu_{\text{idle}} + L \times \sigma_{\text{idle}} \quad \text{where } L = 3.0 \text{ (`UCL_L_FACTOR`)}$$
- **Warmup Period:** `BASELINE_WARMUP_DAYS = 7` (10,080 readings at 30s intervals). Any detection during warmup is forced to `status = "logged"` and cannot dispatch a maintenance ticket.
- **Nightly Updating:** $\text{new\_param} = \alpha \times \text{observed} + (1 - \alpha) \times \text{old\_param}$ with $\alpha = 0.1$ (`BASELINE_ALPHA`).

### 3.2. Signal 1 — Idle-Flow EWMA Control Chart (`detection/engine.py`)
For every reading where $\text{flush\_event} == 0$ and $\text{occupancy\_state} == 0$:
$$\text{EWMA}_t = \lambda \times \text{flow}_t + (1 - \lambda) \times \text{EWMA}_{t-1} \quad \text{where } \lambda = 0.2 \text{ (`EWMA_LAMBDA`)}$$

- **Confirmation Windows by Criticality Tier:**
  Candidate leak timers are started when $\text{EWMA}_t > \text{UCL}$. The condition must persist continuously for:
  - **Tier 1 (Critical Care - ICU/OT):** $3\text{ minutes}$ ($180\text{ s}$)
  - **Tier 2 (Patient Care - Wards):** $5\text{ minutes}$ ($300\text{ s}$)
  - **Tier 3 (Clinical Support - Labs/Scrub):** $7\text{ minutes}$ ($420\text{ s}$)
  - **Tier 4 (Public/Admin - Lobbies):** $10\text{ minutes}$ ($600\text{ s}$)
- **Post-Flush Grace:** `POST_FLUSH_GRACE_S = 60` seconds. For 60 seconds after any flush event, EWMA is frozen and candidate timers are not started to absorb valve seating transients.
- **Occupancy Suppression:** If $\text{occupancy\_state} == 1$, candidate timers are reset to 0 to prevent active water draws from being misidentified as continuous leaks.
- **Debounce / Re-arm:** After a leak event is emitted, repeat events are suppressed until $N = 4$ consecutive readings ($2\text{ minutes}$) measure $\le \text{UCL}$ (`DEBOUNCE_BELOW_UCL_READINGS = 4`).

### 3.3. Signal 2 — Stuck-Valve Fast-Path (`detection/engine.py`)
Flush valves that fail to seat after actuation do not wait for the multi-minute EWMA confirmation window:
$$\text{stuck\_window\_s} = \max(\mu_{\text{dur}} + 2.0 \times \sigma_{\text{dur}},\, 10.0\text{ s})$$
If flow does not return to $\le \mu_{\text{idle}} + 3.0 \times \sigma_{\text{idle}}$ within `stuck_window_s`, a high-confidence leak event is emitted immediately with:
$$\text{confidence} = 0.95, \quad \text{sub\_type} = \text{"stuck\_valve"}$$

### 3.4. Confidence Scoring Formula (`detection/engine.py`)
When a candidate window completes:
$$\text{dev\_norm} = \text{clamp}\left(\frac{\text{EWMA}_t - \text{UCL}}{\max(\text{UCL} - \mu_{\text{idle}},\, 10^{-6})},\, 0.0,\, 1.0\right)$$
$$\text{confidence} = (W_1 \times \text{dev\_norm}) + (W_2 \times 1.0) + (W_3 \times 1.0)$$
Where:
- $W_1 = 0.40$ (`CONFIDENCE_W1` — EWMA deviation magnitude)
- $W_2 = 0.35$ (`CONFIDENCE_W2` — Occupancy cross-check boost; evaluates to 1.0 because $\text{occupancy} == 0$ is a precondition)
- $W_3 = 0.25$ (`CONFIDENCE_W3` — Post-flush pattern check; evaluates to 1.0 because outside grace period is a precondition)

**Dispatch Rules:**
- $\text{confidence} < 0.50$ (`CONFIDENCE_LOG_ONLY`): Discarded as transient jitter.
- $0.50 \le \text{confidence} < 0.80$: `status = "logged"`.
- $\text{confidence} \ge 0.80$ (`CONFIDENCE_ESCALATE`) **and** $\text{warmup\_complete}$ **and** $\text{sensor\_health} \ge 0.60$: `status = "dispatched"`.

### 3.5. Sensor Health Scoring (`detection/sensor_health.py`)
Evaluated across a rolling 60-minute window ($120$ expected readings at 30s intervals):
$$\text{penalty} = 0.30 \times r_{\text{missing}} + 0.30 \times f_{\text{flatline}} + 0.20 \times r_{\text{out\_of\_range}} + 0.20 \times f_{\text{drift}}$$
$$\text{sensor\_health\_score} = \text{clamp}(1.0 - \text{penalty},\, 0.0,\, 1.0)$$
- $r_{\text{missing}}$: Ratio of missing readings plus gap penalty if reading gap $> 60\text{ s}$.
- $f_{\text{flatline}}$: $1.0$ if diagnostic payload reports `"flatline"` or 15 consecutive non-zero readings are identical.
- $r_{\text{out\_of\_range}}$: Fraction of readings with flow $< 0\text{ LPM}$ or $> 100\text{ LPM}$.
- $f_{\text{drift}}$: $1.0$ if diagnostic payload reports `"drift"`.

**Isolation Action:**
If $\text{sensor\_health\_score} < 0.60$ (`DEGRADED_THRESHOLD`):
1. Any leak/hygiene event from that fixture is downgraded to `status = "logged"`.
2. Emits an independent `sensor_fault` event (`sub_type = "sensor_maintenance"`, `status = "dispatched"`).
3. If reading gap $> 120\text{ s}$ (`SENSOR_DROPOUT_GAP_S`), emits `sensor_fault` (`sub_type = "sensor_dropout"`).

### 3.6. Predictive Hygiene Threshold Forecasting (`detection/hygiene.py`)
- **Thresholds by Tier:** Tier 1: $20\text{ uses}$, Tier 2: $30\text{ uses}$, Tier 3: $40\text{ uses}$, Tier 4: $60\text{ uses}$.
- **Lead Time Targets:** Tier 1: $15\text{ minutes}$, Tiers 2–4: $30\text{ minutes}$.
- **Forecast Formula (60-minute sliding window):**
  $$r_{\text{use}} = \frac{\text{uses in observed window}}{\text{window span in minutes}} \quad (\text{uses/minute})$$
  $$\text{uses\_remaining} = \max(0,\, \text{threshold} - \text{uses\_since\_clean})$$
  $$\text{minutes\_to\_breach} = \frac{\text{uses\_remaining}}{r_{\text{use}}}$$
- If $\text{minutes\_to\_breach} \le \text{lead\_time\_target}$, dispatches `predictive_hygiene` ticket with confidence $0.90$.

---

## 4. Ticket Dispatch & Priority Scoring Logic

Implemented in `backend/app/services/ticket_service.py` per PRD Section 10:

### Priority Formula
$$\text{priority\_score} = 100 \times \left(0.40 \times W_{\text{zone}} + 0.30 \times C + 0.20 \times E_{\text{norm}} + 0.10 \times U_{\text{SLA}}\right)$$

### Factor Breakdown
1. **Zone Criticality Weight ($W_{\text{zone}}$):**
   - Tier 1: $1.00$
   - Tier 2: $0.75$
   - Tier 3: $0.50$
   - Tier 4: $0.25$
2. **Confidence ($C$):** Detection confidence float $[0.0, 1.0]$.
3. **Normalized Evidence / Waste ($E_{\text{norm}}$):**
   - For `leak`: $\text{clamp}(\text{flow\_lph} / 60.0,\, 0.0,\, 1.0)$ ($60\text{ L/hr} \rightarrow 1.0$).
   - For `hygiene`: $\text{clamp}(1.0 - (\text{minutes\_to\_breach} / 30.0),\, 0.0,\, 1.0)$ ($0\text{ min} \rightarrow 1.0$).
   - For `sensor_fault`: $1.0 - \text{clamp}(\text{sensor\_health\_score},\, 0.0,\, 1.0)$ ($0.0\text{ health} \rightarrow 1.0$).
4. **SLA Urgency Factor ($U_{\text{SLA}}$):**
   - $$U_{\text{SLA}} = \max\left(0.0,\, 1.0 - \frac{\text{response\_minutes}}{120.0}\right)$$
   - Tier 1 ($15\text{ min}$ SLA) $\rightarrow 0.875$
   - Tier 2 ($30\text{ min}$ SLA) $\rightarrow 0.750$
   - Tier 3 ($60\text{ min}$ SLA) $\rightarrow 0.500$
   - Tier 4 ($120\text{ min}$ SLA) $\rightarrow 0.000$

### Team Routing & Auto-Escalation
- **Target Teams:**
  - Tier 1: `Critical Care Maintenance`
  - Tier 2: `Patient Care Support`
  - Tier 3: `Clinical Plumbing`
  - Tier 4: `General Facilities`
- **Auto-Escalation:**
  If an open ticket passes `sla_due` without acknowledgment:
  $$\text{escalated} = \text{True}, \quad \text{priority\_score} = \min(100.0,\, \text{priority\_score} + 25.0)$$
- **Dashboard Queue Sort Order:**
  Tickets are sorted with **unresolved tickets first** (`open`, `acknowledged`, `in_progress`), ordered descending by `priority_score`. Resolved tickets are strictly sorted to the bottom.

---

## 5. LLM Usage & Constraints

Implemented in `backend/app/services/llm_service.py`.

### What the LLM Does
1. **Incident Summarization:** When a ticket is created or regenerated, an async task passes deterministic fields (`fixture_type`, `zone_name`, `criticality_tier`, `event_type`, `detected_at`, `confidence_score`, `evidence_value`, `priority_score`) to LiteLLM, generating a single concise paragraph in plain English for facility staff.
2. **Chat-Over-Data Copilot (`/api/v1/chat/query`):** Answers natural language queries regarding the facility (e.g., *"Which zone has the highest water waste right now?"*, *"Summarize the ICU scrub area status"*). Formulates answers grounded strictly in active PostgreSQL database records.

### What the LLM Does NOT Do
- **Zero Detection Responsibility:** The LLM does **not** evaluate sensor streams, does **not** decide whether a leak or fault occurred, and does **not** compute priority scores. All detections are 100% deterministic mathematical calculations.
- **No Clinical Context:** No patient, clinical, or EHR data is ever accessible or passed to LLM prompts.

### Provider & Model Selection
- **Provider:** Groq (via LiteLLM).
- **Configured Model:** `openai/gpt-oss-120b` or `groq/llama-3.1-8b-instant`.
- **Rationale:** Free-tier operation with near-instant inference latency (~400–600ms).
- **Graceful Degradation:** If `GROQ_API_KEY` is absent or Groq returns a rate limit/error, the service immediately returns `[LLM Summary Unavailable - API Key Missing or Service Error]` without throwing unhandled exceptions.

---

## 6. Live Validation Results

Re-evaluated directly on the 3-day synthetic test set (`simulator/output/test_set/combined_telemetry.jsonl`) against ground-truth labels (`simulator/output/test_set/combined_anomaly_labels.json`):

### Precision, Recall, and Latency
```
================================================================
SCORING (dispatched leak & sensor fault events)
================================================================
  Precision  : 1.000  (PRD §2 Target: ≥ 0.90)  --> PASS
  Recall     : 1.000  (PRD §2 Target: ≥ 0.85)  --> PASS
  F1-Score   : 1.000
  TP = 15,  FP = 0,  FN = 0,  RD = 30
  Mean Latency   : 396.0 seconds
  Median Latency : 90.0 seconds
  Grace Period   : 10 minutes
  Predictive Hygiene Tickets Dispatched: 16
```
*(Note: Total ground-truth labeled anomalies is 15 across the 3-day test set. Previously under EWMA alone, TP+FN = 14+1 = 15, where 14 was the prior TP count rather than the dataset size. With the trend detector active, all 15 anomalies are detected.)*

### Breakdown by Injected Anomaly Type
| Anomaly Type | True Positives | False Negatives | Recall | Mean Latency (s) | Median Latency (s) | Notes |
|---|---|---|---|---|---|---|
| `sudden_leak` | 3 | 0 | **1.000** | 60.0 | 60.0 | Rapid UCL breach detection |
| `stuck_valve` | 3 | 0 | **1.000** | 220.0 | 180.0 | Caught via post-flush fast path |
| `sensor_flatline`| 3 | 0 | **1.000** | 0.0 | 0.0 | Instant diagnostic dispatch |
| `sensor_dropout` | 3 | 0 | **1.000** | 90.0 | 90.0 | Triggered after 120s reading gap |
| `gradual_leak` | 3 | 0 | **1.000** | 1610.0 | 1200.0 | All 3 creeping leaks caught via TrendDetector |

- **False Positive Rate:** $0.0\%$ ($0$ false alarms triggered across normal diurnal flushes; 0 FP on 403,200-reading ordinary corpus).
- **Unit & Integration Tests:** 23/23 tests passing (`pytest`).

---

## 7. What's Built vs. PRD Phase 0–8 Checklist

| Phase | Description | Status | Verification Evidence |
|---|---|---|---|
| **Phase 0** | Foundation & Data Contracts | **COMPLETE** | 5 Alembic migrations; PostgreSQL schemas for 11 tables; seed data for 20 fixtures across 4 zones loaded. |
| **Phase 1** | Telemetry Simulator | **COMPLETE** | `backend/simulator/engine.py` generates multi-day diurnal Poisson flushes and 5 injectable anomaly types. |
| **Phase 2** | Detection Engine Core | **COMPLETE** | EWMA control chart, UCL calculation, post-flush grace, confirmation windows, debounce logic. |
| **Phase 3** | Sensor Health & Hygiene | **COMPLETE** | Composite sensor health scoring ($0.0–1.0$) with degraded isolation; predictive hygiene time-to-breach. |
| **Phase 4** | API & Persistence Layer | **COMPLETE** | FastAPI endpoints (`/api/v1/telemetry`, `/api/v1/events`, `/api/v1/tickets`, `/api/v1/facility/metrics`). |
| **Phase 5** | Ticket Dispatch Engine | **COMPLETE** | Priority score calculation ($0–100$), team routing, auto-escalation (+25 score boost on SLA breach). |
| **Phase 6** | Command Center Dashboard | **COMPLETE** | Next.js 14 frontend: Facility Criticality Matrix, Kanban board, Compact tickets/alerts feeds, drawer modals. |
| **Phase 6b**| UI System Refinement | **COMPLETE** | Tailwind CSS + Radix UI foundation migration; custom dark theme color variables. |
| **Phase 7** | LLM Summaries & Copilot | **COMPLETE** | Incident summarization via LiteLLM/Groq, chat-over-data with database-grounded query execution. |
| **Phase 8** | Sustainability & System Health | **COMPLETE** | Sustainability KPI counter row (litres, ₹, $\text{CO}_2\text{e}$, sensors online, health score, daily anomalies); ticket sort fix; `.next-dev`/`.next` distDir isolation. |
| **Phase 8b**| Presentation / Video Assets | **NOT STARTED** | 1–3 min video demo and 4-slide presentation deck referenced in PRD Section 15 are not yet created. |

---

## 8. Known Limitations, Gaps & Engineering Trade-offs

1. **Assumed Sustainability Conversion Constants:**
   - Water cost is configured as `WATER_COST_INR_PER_LITRE = 0.15` (approx. ₹150 per kL commercial water tariff in municipal India).
   - Carbon intensity is configured as `WATER_CO2_KG_PER_LITRE = 0.0004` ($0.4\text{ g CO}_2\text{e}/\text{L}$ for pumping and treatment).
   - *Gap:* These are regional heuristic defaults in `config.py`, not dynamically fetched hospital utility rate schedules.
2. **Gradual Leak False Negative ($1$ FN out of $3$ instances):**
   - A micro-leak that ramps very slowly ($< 0.01\text{ LPM}$ increase per hour) can be partially absorbed by the EWMA baseline calculation or delayed by intermittent legitimate flushes, resulting in prolonged detection latency ($960\text{ s}$) and an observed $66.7\%$ recall on that specific anomaly sub-type.
3. **Continuous Occupancy Masking:**
   - In high-traffic restrooms where `occupancy_state == 1` continuously (e.g. shift changes or peak visitor hours), the candidate leak timer is repeatedly reset to prevent false alarms. A real leak during continuous occupancy will not be dispatched until the room empties.
4. **Groq Free-Tier Rate Limiting (30 RPM):**
   - Groq's free-tier API enforces a 30 Requests Per Minute limit. When replaying synthetic bulk history (110 tickets), unthrottled concurrent calls encounter HTTP 429 rate limits. A 2.5-second sleep throttling loop was required to complete backfills.
5. **Simulated Telemetry vs. Physical Field Bus:**
   - Telemetry is generated via Python simulator scripts and HTTP JSON payloads. While schema-compatible with industrial IoT gateways, there is no direct BACnet, Modbus, or MQTT broker connected.
6. **Technician Assignment Granularity:**
   - Tickets route to one of four functional teams (e.g. `Critical Care Maintenance`), but individual technician shift scheduling and GPS dispatch are out of scope.

---

## 9. Explicit Ask to the Reviewing AI

> **Please critique this system for:**
> 1. **Technical soundness of the detection approach** (EWMA/UCL idle flow, stuck valve fast-path, sensor health penalty, and predictive hygiene lead time).
> 2. **Gaps that would concern a judge evaluating a hospital facility management system** (clinical risk, infection control, compliance, and reliability under adverse conditions).
> 3. **Anything that looks fabricated, inconsistent, or unverified** across the codebase, formulas, constants, or test outputs.
> 4. **What is missing for a strong competition submission** given the PRD requirements above.
