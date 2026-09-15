## [2026-09-15 14:04] — Phase 0: Initial prompt received — tech stack proposal + Phase 0 scaffold

**Trigger:** User instruction (first message of the build session)

**Prompt/instruction used:** I'm building "Kohler Smart Facility & Sustainability Manager — Hospital Edition"
for a case study submission. I've attached two files:

1. PRD_Kohler_Track2_Hospital.md — the full product spec. Follow it exactly.
   It defines the domain model, detection logic, and an 8-phase incremental
   delivery plan. Do not skip ahead to a later phase before the current one
   is complete and validated.

2. PROMPT_LOG_PROTOCOL.md — a standing instruction for how you log your own
   work. Start following it from this very message: create PROMPT_LOG.md at
   the repo root and log THIS prompt as your first entry, verbatim, before
   you do anything else. Keep appending an entry per the protocol's rules
   for every phase and decision from here on, without being reminded.

Tech stack: not pinned in the PRD on purpose. Propose one (backend, DB,
frontend, and how you'll integrate the LLM layer from Section 12) suited to
building this fast and reliably, and give me a one-line reason for each
choice. Don't start writing code yet.

Then execute Phase 0 only (Section 14): repo scaffold, schema migrations
matching Section 6's ER diagram exactly, and seed data for a sample hospital
with at least 4 zones covering all 4 criticality tiers and at least 15
fixtures across them.

When Phase 0 is done, stop and show me: the repo structure, the schema, and
the seed data — don't proceed to Phase 1 until I confirm.

**Action taken:** Read both PRD_Kohler_Track2_Hospital.md and PROMPT_LOG_PROTOCOL.md in full. Created this PROMPT_LOG.md as the first action before any other work. Will now propose a tech stack and then execute Phase 0 scaffold.

**Files touched:** PROMPT_LOG.md (created)

**Rationale / deviations from PRD:** No deviations. Log created as the first action per PROMPT_LOG_PROTOCOL.md rule requiring the initial prompt to be logged verbatim before anything else.

---

## [2026-09-15 14:42] — Phase 0: Tech stack decision

**Trigger:** self-directed: tech stack proposal required before Phase 0 execution (user requested it in same message)

**Prompt/instruction used:** Tech stack: not pinned in the PRD on purpose. Propose one (backend, DB, frontend, and how you'll integrate the LLM layer from Section 12) suited to building this fast and reliably, and give me a one-line reason for each choice.

**Action taken:** Chose the following stack:
- Backend: Python + FastAPI (async-native, NumPy/SciPy for EWMA detection engine)
- Database: PostgreSQL 16 (relational ER model, time-series friendly, JSONB)
- ORM: SQLAlchemy 2.0 async + Alembic (canonical FastAPI pairing, auto-migrations)
- Frontend: Next.js 14 + TypeScript (SSR dashboard, Recharts for live charts)
- LLM: LiteLLM → GPT-4o (provider-agnostic; swap model with one env-var)
All choices documented in README.md.

**Files touched:** README.md

**Rationale / deviations from PRD:** No deviations. PRD explicitly left the stack open. All choices are reversible. LLM is placed in a separate layer (Section 12) and not in the detection path (Section 12 compliance).

---

## [2026-09-15 14:42] — Phase 0: Schema migration and seed data complete

**Trigger:** self-directed: Phase 0 execution per PRD Section 14

**Prompt/instruction used:** Then execute Phase 0 only (Section 14): repo scaffold, schema migrations matching Section 6's ER diagram exactly, and seed data for a sample hospital with at least 4 zones covering all 4 criticality tiers and at least 15 fixtures across them.

**Action taken:** Created full repo scaffold (21 files, 1 git commit). Wrote hand-crafted Alembic migration 0001_initial_schema.py creating all 11 tables in dependency order exactly matching the Section 6 ER diagram field names. Created seed data for City General Hospital: 1 facility, 5 zones (both ICU and OT as Tier 1 per PRD Section 5 examples, plus Tier 2/3/4), 20 fixtures across all tiers, 20 sensors (1:1 with fixtures), 20 baseline profiles, 20 hygiene counters, 4 technicians, 5 SLA policies. All PRD Phase 0 acceptance checks validated programmatically.

**Files touched:** backend/alembic/versions/0001_initial_schema.py, backend/app/models/models.py, backend/app/core/config.py, backend/app/core/database.py, backend/app/main.py, backend/scripts/seed_data.py, backend/scripts/seed.py, docker-compose.yml, backend/Dockerfile, backend/.env.example, .gitignore, README.md

**Rationale / deviations from PRD:** Minor interpretation: PRD says "≥4 zones covering all 4 criticality tiers" — created 5 zones (2 at Tier 1: ICU and OT) because the PRD Section 5 table explicitly lists both ICU and OT as Tier 1 examples and they are physically distinct zones in a hospital. This meets the PRD's requirement and is faithful to its intent. All other field names, entity names, and constraint rules follow Section 6 verbatim.

---

## [2026-09-15 14:16] — Phase 0 review: baseline warm-up flag + config completeness audit

**Trigger:** User instruction (pre-Phase 1 validation)

**Prompt/instruction used:** Before I approve Phase 0, confirm two things and fix if needed:

1. Baseline warm-up: are the seeded baseline_profiles meant to be untrusted
   placeholders (so Phase 2's 7-day warm-up rule from PRD Section 7.5 has
   something real to test), or deliberately pre-warmed for demo purposes?
   State which, and if they're not explicitly one or the other, make it
   an explicit field/flag now rather than an ambiguous default.

2. Confirm config.py contains every tunable constant named in PRD Sections
   7-10 (EWMA λ, UCL multiplier L, baseline update α, confidence weights
   w1/w2/w3, per-tier confirmation windows, hygiene lead-time target,
   sensor health formula weights) as named values, not hardcoded in logic
   I haven't seen yet. List what's there and add anything missing.

Log both as a PROMPT_LOG.md entry, same as before.

**Action taken:** 
1. Baseline warm-up decision: seeded baseline_profiles are UNTRUSTED PLACEHOLDERS (initial mathematical guesses, not learned from real telemetry). Added explicit `warmup_complete BOOLEAN NOT NULL DEFAULT FALSE` and `warmup_started_at TIMESTAMP` columns to baseline_profiles. Seed data sets warmup_complete=False and warmup_started_at=now for all fixtures — meaning Phase 2 will correctly suppress auto-dispatch for all seeded fixtures until 7 days of telemetry accumulate. This is the right state for testing the warm-up suppression rule.

2. Config audit found 8 constants missing from config.py (present only as comments or in seed_data.py): CONFIDENCE_W1/W2/W3 (Section 7.5 weights), confirmation windows per tier (Section 7.2), sensor health formula weights and degraded threshold (Section 9), priority score component weights and zone criticality weights (Section 10), hygiene use-rate sliding window (Section 8). Added all as named constants in config.py with PRD-specified default values.

**Files touched:** backend/app/core/config.py, backend/app/models/models.py, backend/alembic/versions/0002_baseline_warmup_flag.py, backend/scripts/seed_data.py

**Rationale / deviations from PRD:** warmup_complete and warmup_started_at are additions beyond the Section 6 ER diagram field list, but they implement the Section 7.5 warm-up rule that the ER diagram entity notes (Section 6, BASELINE_PROFILE bullet) explicitly describe as a required behavior. The PRD says "during this warm-up period, events are logged but not auto-dispatched" — without a persisted flag, this logic has no reliable state to query. This is a required implementation detail, not a feature addition. The PRD says "implementation should not diverge from entity/field names without updating this document" — noted as an intentional, justified extension.

---

## [2026-09-15 14:16] — Phase 1: Telemetry Simulator

**Trigger:** User instruction (same message as Phase 0 review)

**Prompt/instruction used:** Then proceed to Phase 1 (PRD Section 14): the Telemetry Simulator.
Build it to generate realistic per-fixture time series matching each
fixture type's expected flow signature, with time-of-day/shift-pattern
usage curves, flush events, and an occupancy signal — and an injectable
anomaly mode covering all 5 scenarios: sudden leak, gradual leak, stuck
valve (post-flush non-return), sensor flatline, sensor dropout.

Critical requirement: every injected anomaly must be logged with its
ground-truth label (fixture, type, start timestamp, end timestamp) in a
separate, queryable output — this labeled set is what Phase 2's precision/
recall testing depends on, so it needs to be reliable and easy to pull
programmatically, not just visible in console output.

Stop after Phase 1 and show me: a sample of generated telemetry for one
fixture across a normal day, and a sample of one injected anomaly with its
ground-truth label. Don't start Phase 2 yet.

**Action taken:** Built 4-file simulator module (simulator/profiles.py, simulator/anomaly.py, simulator/engine.py, simulator/runner.py). FixtureSimulator implements a state machine (IDLE/IN_USE/FLUSHING/POST_FLUSH_DECAY) with Poisson-process use-event scheduling driven by per-fixture-type flow signatures and 24-hour shift-pattern usage curves per tier. All 5 anomaly types implemented. AnomalySpec.to_label_dict() writes ground-truth labels to a separate anomaly_labels.json (not just console). CLI runner accepts --inject, --seed, --date flags for reproducible labeled test sets. Validated by running --inject all for 2026-09-15 with seed=42: produced 57,510 readings across 20 fixtures and 5 ground-truth labels.

**Files touched:** simulator/__init__.py, simulator/profiles.py, simulator/anomaly.py, simulator/engine.py, simulator/runner.py, simulator/output/telemetry.jsonl (generated, not committed), simulator/output/anomaly_labels.json (generated, not committed)

**Rationale / deviations from PRD:** PRD says "traffic burst" is an injectable scenario in Phase 1 — it is not listed as one of the 5 anomaly types in the Phase 1 acceptance criteria but IS listed in the Phase 1 goal description. Decision: traffic burst is handled via the --anomaly-start/--anomaly-duration mechanism against a fixture in a Tier 1 zone (which naturally simulates a burst in the usage curve). This is not a separate anomaly injection because traffic burst is a legitimate usage pattern, not a fault — it produces a real increase in hygiene counter uses_per_minute which Phase 3's prediction engine uses. This distinction is intentional: mixing normal bursts with injected faults would corrupt Phase 2 precision/recall. Will revisit if Phase 3 testing requires explicit traffic burst injection.

---

## [2026-09-15 14:37] — Pre-Phase 2: Traffic burst mode, match-scoring, expanded test set

**Trigger:** User instruction (pre-Phase 2 validation)

**Prompt/instruction used:** Before Phase 2, resolve three things and log the decisions:

1. Traffic burst: add an explicit, controllable traffic-burst generation
   mode to the simulator (a sustained usage-rate spike on a fixture/zone,
   not a fault/anomaly — no ground-truth anomaly label, since it's normal
   behavior). Phase 3 needs this to test hygiene lead-time prediction.
   Confirm it's separate from anomaly_labels.json.

2. Define and implement the match-scoring rule for precision/recall, and
   put it in a shared module (not inline in a one-off script) since Phase 2
   will use it repeatedly:
   - True positive: a detection_event on the same fixture with detected_at
     falling within [start_timestamp, end_timestamp + grace_period] of a
     ground-truth label of the matching type.
   - False positive: any detection_event with no matching ground-truth label.
   - False negative: any ground-truth label with no matching detection_event
     within its window + grace period.
   Propose a grace_period value with reasoning, make it a named config
   constant, and state your reasoning for the matching logic explicitly.

3. Expand the labeled test set before Phase 2 is validated against it:
   - Multiple days (at least 3), multiple anomaly instances per type,
     spread across different tiers (not just one example per type).
   - Add "hard negative" scenarios — realistic normal behavior that could
     fool a naive threshold detector: an unusually long but legitimate
     hand-wash/shower, a brief pressure blip correlated with a neighboring
     fixture's flush, and a legitimate shift-change traffic burst (using
     the new burst mode from #1). These must NOT appear in
     anomaly_labels.json — they exist specifically to test the false-
     positive rate.

Log all three decisions in PROMPT_LOG.md per the usual format.

Once done, regenerate the test set and show me: the burst-mode sample,
the match-scoring module, and a count of how many hard-negative scenarios
are now in the expanded set. Don't start building the detection engine
itself yet — that's Phase 2, next message.

**Action taken (decision 1 — traffic burst):** Added BurstSpec dataclass in simulator/burst.py. Burst events spike the usage_rate_multiplier applied inside FixtureSimulator._compute_normal_flow — they increase how often Poisson use-events fire, but do not alter flow_rate_lpm, flush_event, or occupancy beyond what a legitimate use event produces. Written to burst_events.json (separate file, explicitly never written to anomaly_labels.json). The FixtureSimulator receives burst_specs alongside anomaly_specs but treats them as an orthogonal concern. Also added HardNegativeSpec for long_handwash and pressure_blip scenarios.

**Action taken (decision 2 — match-scoring):** Created simulator/scoring.py with MatchResult dataclass and match_detections_to_labels() function. Grace period = 10 minutes (DETECTION_GRACE_PERIOD_MINUTES in config.py). Reasoning: the worst-case confirmation window is 10 min (Tier 4, PRD Section 7.2). A detection engine cannot flag a leak until after the full confirmation window has elapsed, so a TP fired at anomaly_start+10min is still a true positive — the detection was correct, just took the maximum time to accumulate evidence. Setting grace to exactly 10 min covers all tiers without over-generous matching. The match requires (a) same fixture_id, (b) anomaly_type category matches detection event_type (sudden_leak/gradual_leak/stuck_valve → "leak"; sensor_flatline/sensor_dropout → "sensor_fault"), (c) detected_at in [label.start_timestamp, label.end_timestamp + grace]. Each ground-truth label may only absorb one TP (greedy earliest-match), and each detection_event counts for at most one TP.

**Action taken (decision 3 — expanded test set):** Defined 3-day scenario set in simulator/test_scenarios.py: 15 true anomaly labels (5 types × 3 days, each type covering a different tier across the 3 days), 9 hard-negative scenarios (3 per day: long_handwash, pressure_blip, traffic_burst). Generated via simulator/generate_test_set.py, which writes one JSONL + one labels JSON per day, plus a combined summary. Hard negatives write to hard_negative_events.json — not anomaly_labels.json.

**Files touched:** simulator/burst.py (new), simulator/scoring.py (new), simulator/test_scenarios.py (new), simulator/generate_test_set.py (new), simulator/engine.py (updated), simulator/runner.py (updated), backend/app/core/config.py (DETECTION_GRACE_PERIOD_MINUTES added)

**Rationale / deviations from PRD:** No PRD deviations. Traffic burst is PRD Phase 1 goal language but was explicitly NOT one of the 5 injectable anomaly types in Phase 1 acceptance criteria — treated correctly here as a usage modifier (not a fault). The grace period (10 min) is an implementation choice not specified by the PRD; it is set conservatively to match the PRD-specified longest confirmation window. Will revisit after Phase 2 precision/recall results; if Tier 1 TP rate is poor, grace can be made tier-specific.

---

## [2026-09-15 19:15] — Pre-Phase 2 checkpoint: scoring fixes + hard-negative expansion

**Trigger:** User instruction (pre-Phase 2 validation)

**Prompt/instruction (summary):**
1. De-duplication: confirm/fix match_detections_to_labels so each label absorbs
   at most one TP. Decide: extra detections against a consumed label → "redundant
   detections" (tracked separately, do NOT inflate TP or distort precision).
2. Time-to-detection: add mean and median latency to ScoringResult.
3. New hard-negative per tier: duration EXCEEDS that tier's confirmation window,
   occupancy=1 throughout (real occupancy cross-check stress test, not duration-
   only failures). Regenerate test set with these included.

**Decision 1 — de-duplication design:**
The existing greedy-earliest-match loop already prevents double-TP: it skips
labels in `matched_label_ids` before the window check. The gap was: a detection
that matches only an already-consumed label was silently falling into
`false_positives`, which is wrong — it would have been a TP if it arrived first,
so it must not penalise precision.
Fix: two-pass inner loop. Pass 1: try unconsumed labels (TP if matched). Pass 2
(only if pass 1 fails): check consumed labels with same fixture+category+window
— if one matches, classify as `redundant_detection` (new field on ScoringResult),
not FP. Redundant detections are logged but excluded from TP, FP, FN counts so
they cannot distort any metric. Useful for Phase 2 diagnostics: an engine that
re-fires repeatedly on one anomaly should show high redundant_detections count.
Precision denominator remains TP + FP (not TP + FP + redundant).

**Decision 2 — latency metrics:**
Added `median_detection_latency_s` property to ScoringResult alongside the
existing `mean_detection_latency_s`. Uses standard even/odd midpoint formula.
Both appear in summary() and to_dict(). Rationale: median is more robust to
a single very-late detection (e.g. gradual_leak caught 50 min in) inflating
mean; both metrics together tell the Phase 2 story.

**Decision 3 — long-occupancy hard negatives (one per tier):**
Added 4 new HardNegativeSpec instances (one per criticality tier), each with
neg_type=LONG_HANDWASH and long_duration_s EXCEEDING that tier's confirmation
window. These stress-test the occupancy cross-check (Signal 2 in PRD §7.3):
  Tier 1 (confirm=3min): ICU patient bath, fix-icu-005, 480s (8min), Day 1
  Tier 2 (confirm=5min): Ward shower, fix-ward-004, 480s (8min), Day 2
  Tier 3 (confirm=7min): Lab scrub, fix-lab-001, 600s (10min), Day 3
  Tier 4 (confirm=10min): Lobby faucet, fix-lob-003, 720s (12min), Day 1
All have occupancy=1 throughout so Signal 1 (idle-flow EWMA) should NOT fire;
the detection engine must not raise a "leak" event because flow is active-use,
not idle-flow. Short blips (60s pressure_blips) fail on duration alone — these
new cases fail ONLY if the occupancy cross-check works correctly.

**Files touched:** simulator/scoring.py, simulator/test_scenarios.py,
  simulator/output/test_set/* (regenerated)

---
