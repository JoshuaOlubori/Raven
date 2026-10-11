---
name: frontend-tickets
description: Break approved frontend technical specs into vertical-slice tickets with acceptance criteria and test plans, written as markdown files in the work/frontend/ tracker. Use after the frontend tech specs are approved, or whenever the user says "break this into frontend tickets", "create the frontend backlog", "plan the frontend work". Produces no production code.
---

# Frontend Tickets + Test Suites

Convert `work/specs/frontend/*` into the backlog the frontend implementation loop will consume. One ticket = one reviewable, independently verifiable unit of behaviour.

## Inputs
`work/prd.md`, `work/specs/frontend/00-frontend-architecture.md`, `work/specs/frontend/<domain>.md`, `docs/ui/stitch-prompts.md`, `CONTEXT.md`. Read the `frontend-tracker` skill for the ticket format.

## Slicing Rules

1. **Vertical slices (tracer bullets).** Each ticket cuts through every layer it needs (component → hook → API call → test) and delivers observable behaviour through the UI. Horizontal tickets such as "create all patient components" strand work that cannot be verified.

2. **Ticket FT-001 is the walking skeleton:** App bootstrap, providers, routing, auth flow, layout shell, theme, quality gates green. Everything else builds on it.

3. **Size:** one session of work, ~300-500 changed lines, 3-8 acceptance criteria. Split anything bigger along a behaviour boundary (list → detail → create → edit → delete).

4. **Dependencies:** declare `blocked_by` edges explicitly. Keep the graph shallow so several tickets stay ready at once. Frontend tickets can depend on backend tickets (e.g., `blocked_by: T-008, FT-002`).

5. **Mode:** mark a ticket `HITL` when a human must decide or act (design review, Stitch asset export, UX decision). Mark everything else `AFK`.

6. **Cross-cutting concerns become tickets of their own** when they carry risk: authorization guards, SSE connection, optimistic updates, responsive breakpoints, accessibility audit. Place each right after the first screen that needs it.

7. **Trace everything.** Every PRD requirement and Stitch screen is covered by ≥1 ticket; every ticket cites `spec_refs` and requirement ids.

## Screen-to-Ticket Mapping (from Stitch)

| Stitch Screen | Frontend Ticket(s) | Backend Dependency |
|---|---|---|
| Staff sign-in | FT-002: Auth sign-in flow | T-002 |
| Today operations dashboard | FT-005: Today dashboard | T-008, T-011 |
| Appointments calendar | FT-006: Calendar view | T-007, T-008 |
| New appointment booking flow | FT-007: Booking wizard | T-007, T-008 |
| Appointment detail & audit | FT-008: Appointment detail panel | T-010 |
| Patient directory | FT-009: Patient list & search | T-005 |
| Patient profile & visit history | FT-010: Patient profile | T-005, T-008 |
| Create/edit patient form | FT-011: Patient form (shared) | T-005 |
| Dental services catalog | FT-012: Services management | T-004 |
| Provider schedules & time off | FT-013: Admin schedules | T-006 |
| Dentist workspace | FT-014: Dentist day view | T-006, T-008 |
| Staff management | FT-015: Staff management | T-003 |

## Shared Component Tickets (Prerequisites)

| Ticket | Purpose | Blocked By |
|---|---|---|
| FT-001 | Walking skeleton (app, routing, providers, layout, theme) | - |
| FT-002 | Auth flow + route guards | FT-001 |
| FT-003 | Shared UI components (Table, Card, Badge, StatusBadge, FormField, DatePicker, Search, Pagination, EmptyState, LoadingSkeleton, ConfirmDialog, Toaster) | FT-001 |
| FT-004 | API client, types, TanStack Query setup, SSE hook | FT-001 |

## Process

1. **Draft the slice list** as a table (id, title, requirements, blocked_by, mode) and show it to the user. Ask: granularity right? dependencies right? anything to merge or split? Iterate until approved.

2. **Write the test strategy** `work/frontend/test-strategy.md`: component test patterns, MSW handlers, Playwright E2E scenarios, accessibility checks.

3. **Write each ticket** to `work/frontend/tickets/FT-NNN-<slug>.md` using the ticket template below. The *Test plan* lists tests by name, with the seam and the assertion's source of truth.

4. **Validate:** run `tracker.py board` and `tracker.py next`; confirm exactly the expected tickets are ready and no ticket is orphaned or cyclic. Check the coverage table (requirement → tickets) has no empty rows.

5. **Log:** `tracker.py log "N frontend tickets created, coverage complete" --phase tickets`.

## Ticket Template

```markdown
---
id: FT-004
title: Patient directory with search and pagination
status: todo
mode: AFK
blocked_by: FT-003, FT-004, T-005
spec_refs: specs/frontend/02-patients-ui.md#4, specs/frontend/07-shared-components.md#table
covers: PRD R-4, Stitch Screen 8
updated: 2026-10-03
---

## Outcome
A paginated, searchable patient directory table with role-aware actions (Add/Edit/Archive for Admin/Receptionist, read-only for Dentist).

## What to build
- `PatientDirectory` page component at `/patients`
- `PatientTable` with columns: Name, Phone, DOB/Age, Medical Alert indicator, Status
- Search input (debounced) with name/phone matching
- Pagination controls (page, size, total)
- "Add Patient" button (Admin/Receptionist only) → opens PatientForm in create mode
- Row click → navigate to `/patients/:id` (PatientProfile)
- Medical alert badge with tooltip preview
- Loading skeleton, empty state, error state

## Acceptance criteria
- [ ] Given authenticated Admin, When visiting `/patients`, Then table loads with pagination (AC1)
- [ ] Given search query, When typing in search, Then results filter debounced 300ms (AC2)
- [ ] Given Dentist role, When visiting `/patients`, Then "Add Patient" button is hidden (AC3)
- [ ] Given patient with medical alerts, When viewing row, Then alert badge shows with preview tooltip (AC4)
- [ ] Given page size change, When selecting new size, Then table updates with correct page size (AC5)
- [ ] Given network error, When fetch fails, Then error state shows with retry button (AC6)

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | `test_patient_directory_renders_table` | Component | Table headers present, rows match mock data | Spec §4 |
| 2 | `test_search_debounces_and_filters` | Component + MSW | Debounced request, results update | Spec §4 |
| 3 | `test_add_button_hidden_for_dentist` | Component | Button not in DOM for Dentist role | Spec §7 |
| 4 | `test_medical_alert_badge_tooltip` | Component | Badge renders, tooltip shows preview | Spec §4 |
| 5 | `test_pagination_controls_work` | Component | Page change triggers fetch with correct params | Spec §4 |
| 6 | `test_error_state_shows_retry` | Component + MSW | 500 response → error UI with retry | Spec §10 |

## Out of scope
Patient creation/edit (FT-011), patient profile detail (FT-010), appointment booking from patient row.

## Notes for the implementer
Use `PatientTable` from shared components. Reuse `usePatients` hook from `features/patients/hooks`. Medical alert preview truncates to 80 chars. Follow responsive patterns: table on desktop, card list on tablet/mobile.
```

## Hand-off

Tell the user: frontend backlog approved → **clear context** → start the implementation loop with `frontend-resume`, which picks the first ready ticket and hands it to `frontend-implement`.