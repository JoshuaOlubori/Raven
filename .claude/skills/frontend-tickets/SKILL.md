---
name: frontend-tickets
description: Generate the frontend backlog from the approved screen manifest and frontend specs, with a mock UI phase, a user sign-off gate, and a backend wiring phase. Use after the frontend specifications are approved or when the user asks to create the frontend backlog.
---

# Frontend Tickets

Generate the backlog from `work/frontend/screens.md` and approved `work/frontend/specs/`. No fixed screen names, roles, routes, or domain map belong in this skill.

## Preconditions

- Every `kind: screen` row points to local design/code assets in the manifest's `Local export folder` column, has an API audit, a proposed route, and known roles or an explicit public/role-free disposition.
- Reference rows are identified as references and do not become routes or tickets.
- API gaps are resolved or explicitly kept out of scope in the manifest.
- Frontend specs are approved and trace each screen to the API contract or `n/a`.
- `frontend-tracker` is initialized.

If these conditions fail, report the exact gap and route the work to `frontend-screens` or `frontend-tech-spec` before generating tickets.

## Phase model

Create a shared foundation ticket, then make one mock UI ticket for each screen row. Mock tickets use MSW fixtures and the final API client/hooks shape, so the UI exercises contract-shaped data without connecting to the live backend. Each ticket includes the audit-approved screen changes, interaction states, route, roles, and responsive behavior.

After all mock tickets, add one mock-phase gate in `HITL` mode, blocked by every mock ticket. Its final review must leave it `awaiting-signoff`. The user reviews the screenshots and requests changes or approves the mock phase. Only after approval does the gate move to `done` and release Phase B.

Create a backend wiring ticket for each screen whose audit lists backend operations. Each depends on the phase gate and the relevant backend `T-*` tickets. Screens with no API dependency have no wiring ticket; record `n/a` in the manifest. Do not infer a screen or create tickets for open gaps.

Split any screen ticket that exceeds one reviewable behavior or needs more than one session. Preserve the mock-before-live phase and make backend wiring depend on the phase gate in every slice.

## Ticket fields

Each ticket includes:

- unique `FT-NNN` ID, title, status, phase (`foundation`, `mock`, `mock-gate`, or `backend`), mode, exact `blocked_by`, spec references, screen slug, and update date
- outcome and explicit in-scope behavior
- acceptance criteria with observable UI outcomes
- test plan naming the seam and contract source of truth
- responsive browser evidence at 375, 768, 1024, and 1440 CSS-pixel widths for visual screen tickets
- implementation log section

Phase A tickets must keep mocks behind MSW in development and tests. Their mock fixtures match the API schemas and omit unsupported design data. Phase B tickets enable the real API transport through the same hooks/client, handle API errors, and keep MSW available for tests.

## Generation process

1. Read the manifest, audits, approved specs, backend ticket tracker, and ticket template conventions from `frontend-tracker`.
2. Show a proposed coverage/dependency table: foundation, one mock slice per screen, global sign-off gate, and API wiring slices. Include reference rows as design inputs only and list unresolved scope gaps separately.
3. Resolve user decisions on scope and granularity before writing the backlog.
4. Write the test strategy to `work/frontend/test-strategy.md` and tickets to `work/frontend/tickets/`.
5. Update the ticket ID columns in `work/frontend/screens.md`.
6. Run `tracker.py init`, `tracker.py board`, `tracker.py next`, and `tracker.py validate`. Confirm the ready frontier and that all screen rows and API operations have traceable tickets or an explicit `n/a`.
7. Log ticket generation in `work/frontend/JOURNAL.md`.

## Ticket template

```markdown
---
id: FT-002
title: <screen slug> mock UI
status: todo
phase: mock
mode: AFK
blocked_by: FT-001
spec_refs: specs/<domain>.md#<section>
covers: screen <slug>
updated: YYYY-MM-DD
---

## Outcome
<Observable user outcome from the approved spec and audit.>

## What to build
- <route and components>
- <supported fields and interactions>
- <loading, empty, error, and permission states>
- <responsive behavior>

## Acceptance criteria
- [ ] <observable behavior tied to a source>

## Test plan
| Test | Seam | Assertion source |
|---|---|---|

## Browser evidence
Capture and inspect the screen at 375, 768, 1024, and 1440 CSS-pixel widths with the Playwright MCP. Save screenshots under `work/frontend/evidence/<ticket-id>/`.

## Implementation log
<Files, decisions, deviations, commands, and evidence.>
```

## Completion

The tracker has no missing blocker references or cycles. Every audited screen is covered by a mock ticket and, if it has API operations, a backend ticket blocked by the global sign-off gate. The manifest contains the generated IDs, and excluded references and unresolved scope gaps did not become implementation tickets.
