---
name: frontend-tracker
description: Read and update the frontend backlog, ticket statuses, blocker graph, and journal. Use whenever frontend tickets are created, claimed, reviewed, completed, blocked, or when the user asks what is done or next. All frontend project state is under work/frontend/.
---

# Frontend Tracker

Keep the editable screen manifest, generated board, tickets, reviews, evidence, specs, and journal under `work/frontend/`. The tracker script is deterministic; ticket files remain the source of truth.

```text
work/frontend/
  screens.md          project-specific screen manifest
  TRACKER.md          generated board
  JOURNAL.md          append-only project history
  specs/              approved frontend specs
  tickets/            FT-* ticket files
  reviews/            ticket and final review reports
  evidence/           browser screenshots and review evidence
```

## Commands

Run from the repository root. Use `py -3` on Windows or `python3` where that is the configured Python command. The script lives inside the skill installation folder; use `.claude/skills` in Claude Code or `.agents/skills` in Codex.

```bash
py -3 .claude/skills/frontend-tracker/scripts/tracker.py init
py -3 .claude/skills/frontend-tracker/scripts/tracker.py board
py -3 .claude/skills/frontend-tracker/scripts/tracker.py next
py -3 .claude/skills/frontend-tracker/scripts/tracker.py validate
py -3 .claude/skills/frontend-tracker/scripts/tracker.py set FT-003 in-progress
py -3 .claude/skills/frontend-tracker/scripts/tracker.py log "screen manifest audited" --phase screens
```

On macOS/Linux or a setup without `py`, replace `py -3` with `python3`; in Codex, replace `.claude/skills` with `.agents/skills`.

`init` creates missing directories and files, then refreshes the board. `next` treats a frontend `FT-*` or backend `T-*` dependency as ready only when its ticket status is `done`. An unknown dependency stays blocked and is reported by `validate`. The board links to the actual ticket filename instead of reconstructing it from the title.

## Ticket format

Each ticket has one front-matter key per line. `blocked_by` accepts `FT-*`, `T-*`, or `-`.

```markdown
---
id: FT-003
title: Patient directory mock UI
status: todo
phase: mock
mode: AFK
blocked_by: FT-001
spec_refs: specs/02-patients-ui.md
covers: screen patient-directory
updated: YYYY-MM-DD
---
```

Statuses are `todo`, `in-progress`, `in-review`, `awaiting-signoff`, `changes-requested`, `blocked`, and `done`. For mock-phase sign-off, keep the phase gate in `awaiting-signoff` until the user approves it; only then set it to `done`, which releases backend tickets.

## Journal

Log phase changes, ticket status changes, scope decisions, design/API deviations, and session checkpoints. Status updates log themselves. Keep other entries short, factual, and tied to an artifact.

## Completion

After writing or editing tickets, `board` shows the correct file links, `next` respects all frontend and backend blockers, and `validate` reports no missing IDs, unknown blockers, or dependency cycles.
