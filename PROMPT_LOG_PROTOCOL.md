# Prompt Log Protocol — for Antigravity to follow during this build

This file is an instruction to you, the build agent (Antigravity), not part of the PRD. Follow it for the entire build, across every phase in `PRD_Kohler_Track2_Hospital.md`.

## What to do

Maintain a file at the repo root called `PROMPT_LOG.md`. Do not generate it retroactively at the end — append to it **live, as you work**, immediately after each meaningful unit of work (a prompt you received, a plan you formed, a non-trivial action you took). Treat this as part of the task itself, not an afterthought step.

## When to log an entry

Create a new entry whenever any of the following happens:
- You receive a new instruction or prompt from the user.
- You make a non-trivial design or implementation decision not fully specified by the PRD (e.g. choosing a specific library, picking a concrete default value the PRD left tunable, resolving an ambiguity).
- You complete a phase or sub-phase deliverable.
- You deviate from the PRD in any way, however small — log the deviation and the reason.
- You encounter and fix a bug or correct a prior approach.

Trivial mechanical steps (formatting a file, a typo fix) do not need an entry.

## Entry format

Append each entry to `PROMPT_LOG.md` in this exact structure:

```
## [YYYY-MM-DD HH:MM] — <Phase N: short title>

**Trigger:** <the user's instruction, or "self-directed: <reason>" if no new user input prompted this>

**Prompt/instruction used:** <the exact prompt or system instruction you acted on — verbatim, not summarized>

**Action taken:** <what you built/changed/decided, in 2-5 sentences>

**Files touched:** <list>

**Rationale / deviations from PRD:** <why this approach; note explicitly if it diverges from PRD_Kohler_Track2_Hospital.md and why>

---
```

## Rules

1. **Append-only.** Never edit or delete a prior entry, even if a later decision supersedes it — log the supersession as a new entry instead ("Revises entry from [timestamp]: ..."). The log is a history, not a living summary.
2. **Verbatim prompts.** The "Prompt/instruction used" field must be the actual text, not your paraphrase of it — this file is what gets converted into the submission's Prompts Documentation PDF, so paraphrasing defeats its purpose.
3. **One entry per unit of work**, in chronological order. Don't batch multiple unrelated decisions into a single entry.
4. **Keep it inside the repo**, committed alongside code — it should be visible in normal version history, not generated outside the repo and pasted in later.
5. At the end of the build (Phase 8), do not rewrite this file — it gets converted as-is (formatting only, no content changes) into the submission's Prompts Documentation PDF.

## Why this matters for this project specifically

The evaluation weighs "Approach & Innovation" (including prompt/architecture quality) at 45%. A log built live, in the order decisions actually happened, is what makes that documentation credible — it should read like a build history, not a reconstructed narrative.
