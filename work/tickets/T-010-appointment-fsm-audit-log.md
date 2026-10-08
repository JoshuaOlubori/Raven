---
id: T-010
title: Appointment lifecycle FSM and immutable audit log
status: in-progress
mode: AFK
blocked_by: T-009
spec_refs: specs/05-appointments.md#2-layer-1, specs/05-appointments.md#3-layer-2, specs/05-appointments.md#4-layer-3, specs/05-appointments.md#8-state-machine
covers: R-12, R-14, NFR-4
updated: 2026-10-08
---

## Outcome
Appointments advance through deterministic lifecycle transitions (`CONFIRMED`, `CHECKED_IN`, `IN_PROGRESS`, `COMPLETED`, `NO_SHOW`), and every status change, reschedule, and cancellation produces an immutable, append-only audit record queryable by staff.

## What to build
- `src/app/models/audit.py`: `AppointmentAuditLog` ORM model (`id`, `appointment_id`, `actor_id`, `from_status`, `to_status`, `old_start_time`, `new_start_time`, `note`, `created_at`).
- `src/app/services/appointment_service.py`:
  - Pure FSM transition guard: enforces valid transitions per PRD §5.2 / Spec 05 §8.
  - Audit logging helper: records an immutable audit record for every reschedule, cancellation, and status transition with acting staff ID.
- `src/app/routers/appointments.py`:
  - `POST /api/v1/appointments/{id}/status`: Transitions status (`CONFIRMED`, `CHECKED_IN`, `IN_PROGRESS`, `COMPLETED`, `NO_SHOW`).
  - `GET /api/v1/appointments/{id}/audit-logs`: Lists chronological audit log entries with actor details.

## Acceptance criteria
- [ ] Given a `CHECKED_IN` appointment, When the dentist transitions status to `IN_PROGRESS`, Then the status updates to `IN_PROGRESS` and `200 OK` is returned (R-12).
- [ ] Given an appointment in `COMPLETED`, `CANCELLED`, or `NO_SHOW` status, When any transition is attempted, Then the system rejects the request with `400 Bad Request` and error code `INVALID_STATUS_TRANSITION` (R-12).
- [ ] Given any status change, reschedule, or cancellation, Then an append-only audit record is created capturing `actor_id`, `from_status`, `to_status`, timestamps, and note (R-14).
- [ ] Given `GET /api/v1/appointments/{id}/audit-logs`, When queried, Then the chronological history of transitions is returned with actor names (R-14).
- [ ] No API endpoint or database function exists to update or delete audit records (NFR-4).

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | `test_fsm_valid_lifecycle_transitions` | Pure domain unit / API | SCHEDULED -> CONFIRMED -> CHECKED_IN -> IN_PROGRESS -> COMPLETED | PRD R-12 |
| 2 | `test_fsm_terminal_state_rejects_transition` | API + Dentist auth | status 400, error == "INVALID_STATUS_TRANSITION" | PRD R-12 |
| 3 | `test_dentist_only_transitions_to_in_progress` | API + Receptionist auth | status 403 when receptionist attempts IN_PROGRESS | Spec 05 §4 |
| 4 | `test_status_transition_creates_audit_log_entry` | API + Staff auth | audit log row present with actor_id, from_status, to_status | PRD R-14 |
| 5 | `test_audit_logs_endpoint_returns_chronological_history` | API + Staff auth | status 200, items ordered by created_at | PRD R-14 |
| 6 | `test_audit_logs_are_immutable` | Repository test | no delete/update method exists on repository | NFR-4 |

## Out of scope
Real-time SSE event broadcast and patient notification dispatch (handled in T-011, T-012).

## Notes for the implementer
Ensure `AppointmentAuditLog` has foreign keys to `Appointment` and `Staff`, and uses `joinedload(AppointmentAuditLog.actor)` to prevent N+1 query overhead.

## Implementation log
- Created `AppointmentAuditLog` ORM model in `backend/src/app/models/audit.py` with fields: `id`, `appointment_id`, `actor_id`, `from_status`, `to_status`, `old_start_time`, `new_start_time`, `note`, `created_at`
- Added `audit_logs` relationship to `Appointment` model with cascade delete-orphan
- Added `AppointmentStatusUpdate` and `AuditLogRead` schemas to `backend/src/app/schemas.py`
- Added repository functions `create_audit_log` and `list_audit_logs_for_appointment` with eager-loading on actor relationship
- Implemented FSM transition logic in `AppointmentService.transition_status()` with validation:
  - Valid transitions per Spec 05 §8
  - Terminal state rejection (COMPLETED, CANCELLED, NO_SHOW)
  - Dentist-only transitions for IN_PROGRESS and COMPLETED
- Added audit logging helper `_create_audit_log()` for status transitions, reschedules, and cancellations
- Updated `reschedule_appointment()` and `cancel_appointment()` to create audit log entries
- Added API endpoints:
  - `POST /api/v1/appointments/{id}/status` for FSM transitions (Admin, Receptionist, Dentist)
  - `GET /api/v1/appointments/{id}/audit-logs` for chronological audit history (All staff)
- Added unit tests for FSM transitions (4 tests) and API tests for status transitions and audit logs (6 tests)
- All 121 tests pass, quality gates green (ruff, format, mypy, pytest)
- Addressed review round 1 findings:
  - Blocker (B1): Added `actor: StaffRead` binding to `AuditLogRead` schema; endpoint returns real `actorName` via eager-loaded `joinedload(AppointmentAuditLog.actor)`
  - Major (M2): Added `test_audit_logs_are_immutable` repository-level immutability test (no update/delete functions exist)
  - Major (actorName value assertion): Fixed `test_status_transition_creates_audit_log_entry` to assert `actorName == staff.full_name`
  - Minor: Replaced deprecated `datetime.utcnow()` with `utcnow()` (timezone-aware) in audit model
- Commit: T-010 review fixes

Files touched:
- `backend/src/app/models/audit.py` (new)
- `backend/src/app/models/appointment.py` (added audit_logs relationship)
- `backend/src/app/models/__init__.py` (export AppointmentAuditLog)
- `backend/src/app/schemas.py` (added AppointmentStatusUpdate, AuditLogRead)
- `backend/src/app/db/repository.py` (added create_audit_log, list_audit_logs_for_appointment)
- `backend/src/app/services/appointment_service.py` (FSM transitions, audit logging)
- `backend/src/app/routers/appointments.py` (status and audit-logs endpoints)
- `backend/tests/unit/test_appointment_service.py` (FSM unit tests)
- `backend/tests/api/test_appointments.py` (API tests)

## Review history

- Review round 1: [work/reviews/T-010-review-1.md](work/reviews/T-010-review-1.md) — changes-requested (B1/M2/m4/n1)
