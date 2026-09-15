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
