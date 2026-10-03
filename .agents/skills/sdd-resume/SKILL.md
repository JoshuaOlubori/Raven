---
name: sdd-resume
description: Orient a fresh session in the spec-driven workflow — read the work/ tracker, work out which phase the project is in, and name the exact next skill to run — or wrap up a session by checkpointing state before the user clears context. Use at the START of every new session or after /clear, and at the END of a session when the user says "wrap up", "checkpoint", "I'm stopping", or "what's next". Also use when the user asks "where are we?".
---

# SDD Resume / Checkpoint

The workflow depends on clean context windows. This skill makes starting over cheap, because everything that matters is already in `work/`.

## Mode A — Resume (start of a session)

1. Read `work/TRACKER.md` and the last ~30 lines of `work/JOURNAL.md`. If `work/` is missing, say so and point to `sdd-setup`.
2. Detect the phase from the artifacts:

| What exists | Phase | Next skill |
|---|---|---|
| no `prd.md` | idea | `sdd-grill-prd` |
| `prd.md`, no `specs/` | PRD done | `sdd-tech-spec` |
| `specs/`, no tickets | specs done | `sdd-tickets` |
| a ticket `in-review` | build loop | `sdd-ticket-review` for that ticket |
| a ticket `changes-requested` | build loop | `sdd-implement` for that ticket |
| a ticket `in-progress` | build loop (interrupted) | `sdd-implement`, continuing from its Implementation log and `git status` |
| ready tickets (`tracker.py next`) | build loop | `sdd-implement` for the first ready ticket |
| all tickets `done`, no `final-review.md` | build done | `sdd-final-review` |
| `final-review.md` verdict ship, no `retro.md` | shipped | `sdd-retro` |

3. Verify against git: `git status` and `git log -5` should agree with the tracker. Report any mismatch (uncommitted work on a ticket marked done, etc.) before proceeding.
4. Tell the user in ≤6 lines: current phase, progress (n/N done), what is blocked, the one next action, and the suggested model tier (strong for grill/spec/tickets/final-review, cheaper for implement, strong-or-different-model for reviews).
5. On the user's go-ahead, invoke the named skill.

## Mode B — Checkpoint (end of a session)

1. Ensure code is committed or stashed; note anything uncommitted.
2. For any in-flight ticket, make sure its *Implementation log* states: done so far, what remains, failing tests, assumptions.
3. Run `tracker.py log "checkpoint: <what's done> / <what's next>" --phase <phase>`.
4. Tell the user the single command to run in the next session (`sdd-resume`), and that it is safe to clear context now.
