---
name: frontend-resume
description: Determine the current frontend workflow phase, read its tracker and journal, and name the next frontend skill. Use at the start of every frontend session, after clearing context, or when the user asks where frontend work stands or asks to checkpoint it.
---

# Frontend Resume

Read the current project state before choosing work. Never infer a screen, backend capability, or completed sign-off from a skill example.

## Start

1. Read `work/frontend/screens.md` and check asset and audit status when present.
2. Read `work/frontend/TRACKER.md`, the last 30 lines of `work/frontend/JOURNAL.md`, and the active ticket or review report.
3. When Python is available, refresh the board and ready frontier with `tracker.py board`, `tracker.py next`, and `tracker.py validate`. On Windows use `py -3`; otherwise use the configured `python3` command. If execution is unavailable, read the Markdown files directly and report that limitation.
4. Tell the user the phase and the next skill with one reason.

## Phase routing

| State | Next skill |
|---|---|
| No `work/frontend/screens.md` or screen set changed | `frontend-screens` |
| Screen assets or contract audits are incomplete | `frontend-screens` |
| Screen audit has unresolved design/API questions | Present the documented decision to the user; keep dependent tickets out of the ready set |
| Screen set audited; no initialized frontend app | `frontend-setup` |
| App exists; no approved frontend specs | `frontend-tech-spec` |
| Specs approved; no tickets | `frontend-tickets` |
| A ticket is `in-progress` or changes were requested | `frontend-implement` |
| A ticket is `in-review` | `frontend-ticket-review` |
| Mock phase gate is `awaiting-signoff` | Show the mock phase evidence and ask for the user's sign-off or changes |
| All mock tickets are done; gate is ready | `frontend-final-review` with scope `mock phase` |
| A backend wiring ticket is ready | `frontend-implement` |
| All backend tickets are done | `frontend-final-review` with scope `release` |
| Final review is complete | `frontend-retro` when requested or at project close |

Use actual tracker statuses and the screen manifest to distinguish mock work from backend wiring. A mock phase is not approved merely because its code review passes; the user must approve the phase gate before any backend wiring ticket becomes ready.

## User requests

- For a named ticket, verify its blockers, then implement or review that ticket.
- If a backend contract changed, read the changed OpenAPI document/spec and update affected audits/specs before wiring UI.
- If the user asks to wrap up, append a short journal checkpoint with the current phase and next action, then report the exact next skill.

## Completion

The user receives the current phase, exact next skill, ticket/blocker state, screen audit gaps, and any sign-off decision needed. Do not report an unavailable tracker command as successful.
