---
name: frontend-tracker
description: The markdown issue tracker and work history for spec-driven frontend development. Use whenever a ticket is created, claimed, moved between statuses, reviewed or completed, whenever work history needs recording, and whenever the user asks "what's done", "what's next", "show the board" or "log this" for frontend work. Every other frontend-* skill reads and writes the tracker through this skill, so consult it before touching anything under work/frontend/.
---

# Frontend Tracker

All frontend project state lives as plain markdown under `work/frontend/`, so it survives `/clear`, new sessions, and model switches.

```
work/frontend/
  TRACKER.md         board (generated — never hand-edit)
  JOURNAL.md         append-only history of everything that happened
  specs/             00-frontend-architecture.md + one <domain>.md per module (frontend-tech-spec)
  tickets/           FT-001-<slug>.md ...
  reviews/           FT-001-review-1.md ..., final-review.md
```

## Operations

Run the bundled script from the repo root. It handles status changes, the ready-frontier, and the journal deterministically.

```bash
python .claude/skills/frontend-tracker/scripts/tracker.py init
python .claude/skills/frontend-tracker/scripts/tracker.py next                 # tickets whose blockers are all done
python .claude/skills/frontend-tracker/scripts/tracker.py set FT-003 in-progress
python .claude/skills/frontend-tracker/scripts/tracker.py log "decided to use react-day-picker for calendar" --phase spec
python .claude/skills/frontend-tracker/scripts/tracker.py board
```

`<skills-dir>` is the folder this skill was installed into (`.claude/skills`). The script handles frontend ticket prefixes (FT-).

## Ticket File Format

Front matter uses one `key: value` per line (the script parses these lines exactly):

```markdown
---
id: FT-004
title: Patient directory with search and pagination
status: todo            # todo | in-progress | in-review | changes-requested | blocked | done
mode: AFK               # AFK (agent alone) | HITL (needs a human decision/action)
blocked_by: FT-002, FT-003   # or "-"
spec_refs: specs/frontend/02-patients-ui.md, specs/frontend/07-shared-components.md
updated: 2026-10-03
---
```

## Status Lifecycle

`todo` → `in-progress` → `in-review` → `done`, with `changes-requested` looping back to `in-progress`. A ticket reaches `done` only after `frontend-ticket-review` approves it.

## Journal Discipline

Append one journal line at each of these moments: a phase starts or finishes, a ticket changes status, a design decision is made, a surprise or deviation from the spec occurs, a session ends. Lines stay short and factual and name the artifact touched. The status command logs transitions automatically; use `log` for everything else.

## Reading History

To resume or audit, read `work/frontend/TRACKER.md`, then the last ~30 lines of `work/frontend/JOURNAL.md`, then the specific ticket and its `reviews/` files. The journal is the source of truth for what happened; ticket files are the source of truth for what was asked.

## Ticket Prefix Convention

- Backend tickets: `T-XXX`
- Frontend tickets: `FT-XXX`

This keeps the two workstreams independently trackable while allowing cross-references in `blocked_by` (e.g., a frontend ticket can be blocked by a backend ticket).