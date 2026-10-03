---
name: sdd-tracker
description: The markdown issue tracker and work history for spec-driven backend development. Use whenever a ticket is created, claimed, moved between statuses, reviewed or completed, whenever work history needs recording, and whenever the user asks "what's done", "what's next", "show the board" or "log this". Every other sdd-* skill reads and writes the tracker through this skill, so consult it before touching anything under work/.
---

# SDD Tracker

All project state lives as plain markdown under `work/`, so it survives `/clear`, new sessions, and model switches.

```
work/
  TRACKER.md      board (generated — never hand-edit)
  JOURNAL.md      append-only history of everything that happened
  prd.md          output of sdd-grill-prd
  specs/          00-architecture.md + one <domain>.md per module (sdd-tech-spec)
  test-strategy.md
  tickets/        T-001-<slug>.md ...
  reviews/        T-001-review-1.md ..., final-review.md
```

## Operations

Run the bundled script from the repo root. It handles status changes, the ready-frontier, and the journal deterministically.

```
python <skills-dir>/sdd-tracker/scripts/tracker.py init
python <skills-dir>/sdd-tracker/scripts/tracker.py next                 # tickets whose blockers are all done
python <skills-dir>/sdd-tracker/scripts/tracker.py set T-003 in-progress
python <skills-dir>/sdd-tracker/scripts/tracker.py log "decided cursor pagination" --phase spec
python <skills-dir>/sdd-tracker/scripts/tracker.py board
```

`<skills-dir>` is the folder this skill was installed into (for example `.agents/skills` or `.claude/skills`). `install.sh` fills it in automatically.

## Ticket file format

Front matter uses one `key: value` per line (the script parses these lines exactly):

```
---
id: T-004
title: Approve a deal (RBAC + audit log)
status: todo            # todo | in-progress | in-review | changes-requested | blocked | done
mode: AFK               # AFK (agent alone) | HITL (needs a human decision/action)
blocked_by: T-002, T-003   # or "-"
spec_refs: specs/deals.md#approval, prd.md#R-7
updated: 2026-10-03
---
```

The body sections are defined in `sdd-tickets/references/ticket-template.md`.

## Status lifecycle

`todo` → `in-progress` → `in-review` → `done`, with `changes-requested` looping back to `in-progress`. A ticket reaches `done` only after `sdd-ticket-review` approves it.

## Journal discipline

Append one journal line at each of these moments: a phase starts or finishes, a ticket changes status, a design decision is made, a surprise or deviation from the spec occurs, a session ends. Lines stay short and factual and name the artifact touched. The status command logs transitions automatically; use `log` for everything else.

## Reading history

To resume or audit, read `work/TRACKER.md`, then the last ~30 lines of `work/JOURNAL.md`, then the specific ticket and its `reviews/` files. The journal is the source of truth for what happened; ticket files are the source of truth for what was asked.
