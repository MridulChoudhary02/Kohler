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
