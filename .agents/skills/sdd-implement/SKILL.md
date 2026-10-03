---
name: sdd-implement
description: Implement exactly one ticket from the work/ tracker test-first (red → green, one test at a time), following the technical spec and the fastapi-production-architecture standard, then run quality gates, commit, and hand the ticket to review. Use whenever the user says "implement T-00X", "build the next ticket", "start coding", "address the review comments", or after sdd-resume selects a ticket. Handles both first-time implementation and fixing a changes-requested review.
---

# SDD Implement (one ticket per session)

One ticket, one context window, one commit series. Finishing a ticket and clearing context keeps each review small and each session sharp.

## 0. Pick and claim
- If no ticket id was given, run `tracker.py next` and propose the first ready ticket; confirm with the user. A `HITL` ticket needs the human present for its decision points.
- Run `tracker.py set T-NNN in-progress`.

## 1. Load context (and only this)
Read, in order: the ticket; the spec sections named in `spec_refs`; `work/specs/00-architecture.md`; `work/test-strategy.md`; the `fastapi-production-architecture` skill sections for each layer the ticket touches (§3 contracts, §4 persistence, §5 wiring, §6 concurrency, §7 state); `CONTEXT.md`. Skim existing code for the modules involved and follow its patterns.

If the ticket is `changes-requested`, read the newest `work/reviews/T-NNN-review-N.md` and treat its blockers and majors as the task list.

## 2. Build test-first
For each row in the ticket's *Test plan*, in order:
1. **Red:** write one test at its named seam. Run it and watch it fail for the right reason.
2. **Green:** write the smallest code that passes it, in the correct layer per the standard. Run the whole suite.
3. Move to the next row.

Rules of the loop:
- Expected values come from the spec or PRD, never from calling the code under test again.
- Test through public seams (API via dependency overrides, repository against the real test DB, schema validators) rather than private helpers.
- Handlers stay thin: each handler declares its dependencies and delegates to a service. Business rules live in schema validators or services.
- Use the naming conventions from standard §2.
- Add only what the ticket's acceptance criteria require. Spot an adjacent need? Write it under *Notes* as a proposed follow-up ticket and continue.

## 3. Deviations
When the spec turns out wrong or incomplete, stop, state the conflict, and ask the user (or, for a small clarification, record your assumption in the ticket's *Implementation log* and `tracker.py log`). The spec stays the source of truth; propose a spec edit rather than silently diverging.

## 4. Finish
1. Walk the ticket's acceptance criteria and tick each with the test that proves it.
2. Run the standard's **§9 Generation checklist** against your diff and fix gaps.
3. Run every quality gate from `CLAUDE.md` (ruff, format check, mypy, full pytest). All green.
4. Fill the ticket's *Implementation log*: what was built, files touched, decisions, deviations, commands run.
5. Commit: `T-NNN: <title>` (conventional-commit prefix welcome). Record the sha in the log.
6. `tracker.py set T-NNN in-review`.

## 5. Hand-off
Tell the user: ticket built → **clear context** → run `sdd-ticket-review` for T-NNN in a fresh session, because a reviewer who did not write the code reads it more honestly.
