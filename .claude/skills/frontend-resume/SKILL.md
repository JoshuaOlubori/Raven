---
name: frontend-resume
description: Orient a fresh session in the frontend spec-driven workflow — read the work/frontend/ tracker, work out which phase the project is in, and name the exact next skill to run — or wrap up a session by checkpointing state before the user clears context. Use at the START of every new session or after /clear, and at the END of a session when the user says "wrap up", "checkpoint", "I'm stopping", or "what's next" for frontend work. Also use when the user asks "where are we with the frontend?".
---

# Frontend Resume

Start every frontend session here. It reads the tracker and tells you exactly what to do next.

## Quick Start (run these commands)

```bash
# 1. Show the board
python .claude/skills/frontend-tracker/scripts/tracker.py board

# 2. Show ready tickets (blockers all done)
python .claude/skills/frontend-tracker/scripts/tracker.py next

# 3. Read the last ~30 lines of journal
tail -30 work/frontend/JOURNAL.md
```

## Phase Detection

The frontend project moves through these phases. Check `work/frontend/TRACKER.md` and `work/frontend/specs/` to determine current phase.

| Phase | Signal | Next Skill |
|---|---|---|
| **Not started** | No `work/frontend/` dir, or empty | `frontend-setup` |
| **Setup done, no spec** | `frontend/` exists, no `work/frontend/specs/` | `frontend-tech-spec` |
| **Spec done, no tickets** | Specs exist, `work/frontend/tickets/` empty | `frontend-tickets` |
| **Tickets exist, none in-progress** | `tracker.py next` shows ready tickets | `frontend-implement` (on first ready) |
| **Ticket in-progress** | `tracker.py board` shows `in-progress` | `frontend-implement` (continue) |
| **Ticket in-review** | `tracker.py board` shows `in-review` | `frontend-ticket-review` |
| **All tickets done** | `tracker.py board` shows all `done` | `frontend-final-review` (if exists) or wrap up |

## Session Start Protocol

1. **Run the Quick Start commands above**
2. **Read the current ticket** (if any `in-progress` or `in-review`)
3. **Announce the phase and next action** to the user:
   - "Frontend is in **<phase>**. The next step is **<skill>** because <reason>."
4. **If implementing**: Confirm the ticket with the user, then invoke `frontend-implement`.
5. **If reviewing**: Invoke `frontend-ticket-review`.

## Session End Protocol

When the user says "wrap up", "checkpoint", "I'm stopping", or at a natural stopping point:

1. **Log the checkpoint**:
   ```bash
   python .claude/skills/frontend-tracker/scripts/tracker.py log "Session end: <what was done, what's next>" --phase <current-phase>
   ```
2. **Summarize for the user**:
   - Current phase
   - Ticket status (in-progress, in-review, done)
   - Next skill to run when they return
   - Any blockers or decisions needed

## Common Questions

**"Where are we?"** → Run this skill. It prints the board and next action.

**"What's next?"** → `tracker.py next` shows ready tickets. If none, check blockers.

**"I want to work on <specific screen>"** → Find the ticket in `work/frontend/tickets/`, check its `blocked_by`. If ready, `tracker.py set FT-NNN in-progress` then `frontend-implement`. If blocked, explain what needs to complete first.

**"The backend changed, do we need to update?"** → Check if the backend ticket is in `blocked_by` for any frontend ticket. If so, that frontend ticket may need updates. Run `tracker.py board` to see dependencies.

## Cross-Workstream Dependencies

Frontend tickets can `blocked_by` backend tickets (T-XXX). The tracker script understands both prefixes. When a backend ticket completes, dependent frontend tickets may become ready.

Example:
```
FT-007: Booking wizard  blocked_by: FT-003, FT-004, T-008
```
FT-007 won't appear in `tracker.py next` until T-008 (backend appointment booking) is `done`.

## Emergency Commands

If the tracker script fails or is missing:
- `cat work/frontend/TRACKER.md` — read board directly
- `ls work/frontend/tickets/` — list tickets
- `grep "^status:" work/frontend/tickets/*.md` — see all statuses