---
id: T-008
title: Appointment booking and atomic overlap guard
status: done
mode: AFK
blocked_by: T-005, T-007
spec_refs: specs/05-appointments.md#2-layer-1, specs/05-appointments.md#3-layer-2, specs/05-appointments.md#4-layer-3, specs/05-appointments.md#5-layer-4
covers: R-10, NFR-1
updated: 2026-10-07
---

## Outcome
Receptionists and Admins can book appointments for patients, with automatic end-time calculation based on procedure duration and atomic database overlap prevention guaranteeing zero double-booking (409 Conflict).

## What to build
- `src/app/models/appointment.py`: `Appointment` ORM model (`id`, `patient_id`, `dentist_id`, `service_id`, `start_time`, `end_time`, `status`, `cancellation_reason`, `reminder_sent_at`, timestamps).
- `src/app/db/repository.py`:
  - `check_appointment_overlap`: Query checking for intersecting non-cancelled appointments (`start_time < end_time AND end_time > start_time`) with row-locking support.
  - `create_appointment`: Saves new appointment in state `SCHEDULED`.
  - `get_appointment_detail`: Fetches appointment with `joinedload` on patient, dentist, and service.
  - `list_appointments`: Queries appointments with optional filters (`dentist_id`, `patient_id`, `status`, `start_date`, `end_date`).
- `src/app/services/appointment_service.py`: `AppointmentService` validating that the requested slot falls within the dentist's shift, does not intersect time-off blocks, and is strictly free of existing appointment overlaps.
- `src/app/routers/appointments.py`:
  - `POST /api/v1/appointments` (Admin, Receptionist)
  - `GET /api/v1/appointments` (All staff)
  - `GET /api/v1/appointments/{id}` (All staff)

## Acceptance criteria
- [ ] Given an open available slot, When `POST /api/v1/appointments` is submitted, Then an appointment is created in status `SCHEDULED`, end time is auto-calculated (`start_time + duration`), and `201 Created` is returned (R-10).
- [ ] Given an appointment request outside the dentist's active shift hours, When submitted, Then the system returns `400 Bad Request` with error code `OUTSIDE_SHIFT_HOURS`.
- [ ] Given an appointment request overlapping a dentist's time-off block, When submitted, Then the system returns `409 Conflict` with error code `TIME_OFF_CONFLICT`.
- [ ] Given two concurrent requests attempting to book the exact same or overlapping slot for the same dentist, Then exactly one request succeeds (`201 Created`) and the conflicting request is rejected with `409 Conflict` (NFR-1).
- [ ] Given `GET /api/v1/appointments`, When queried, Then appointments are returned with patient, dentist, and service details in a single query without N+1 query leaks.

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | `test_book_appointment_success_201` | API + Receptionist auth | status 201, status == "SCHEDULED", end_time == start_time + duration | PRD R-10 |
| 2 | `test_booking_outside_shift_rejected_400` | API + Receptionist auth | status 400, error == "OUTSIDE_SHIFT_HOURS" | Spec 05 §7 |
| 3 | `test_booking_overlapping_time_off_rejected_409` | API + Receptionist auth | status 409, error == "TIME_OFF_CONFLICT" | Spec 05 §7 |
| 4 | `test_concurrent_booking_overlap_prevention_409` | Concurrency seam (2 sessions) | 1 succeeds (201), 1 fails (409 APPOINTMENT_OVERLAP_CONFLICT) | NFR-1, ADR 0001 |
| 5 | `test_list_appointments_eager_loading_avoids_n_plus_one` | Repository + DB | assert exact query count with joins | Test Strategy §4 |

## Out of scope
Rescheduling, cancellation, state machine transitions, and audit logs (handled in T-009, T-010).

## Notes for the implementer
Follow ADR 0001 strictly: the overlap check must execute within the same database transaction as the insert.

## Implementation log
- Created `src/app/models/appointment.py` with Appointment ORM model (UUID PK, FKs to patient/dentist/service, start/end time, status, cancellation_reason, reminder_sent_at, timestamps, composite index on dentist_id/start_time/end_time/status)
- Updated `src/app/models/__init__.py` to export Appointment
- Added `appointments` relationship to `Patient`, `Staff`, and `DentalService` models with `back_populates`
- Added appointment repository functions to `src/app/db/repository.py`:
  - `get_appointment`, `get_appointment_detail` (with joinedload on patient/dentist/service)
  - `list_appointments` (with filters and eager loading)
  - `check_appointment_overlap` (atomic overlap guard per ADR 0001)
  - `create_appointment`
- Added appointment exceptions to `src/app/exceptions.py`: `AppointmentOverlapConflictError`, `OutsideShiftHoursError`, `TimeOffConflictError`, `AppointmentNotFoundError`, `InvalidStateTransitionError`, `CancellationReasonRequiredError`
- Created `src/app/services/appointment_service.py` with `AppointmentService`:
  - `book_appointment` validates service, shift coverage, time-off conflict, appointment overlap
  - Auto-calculates end_time from start_time + service duration
  - `get_appointment_detail`, `list_appointments` with eager loading
  - `_validate_shift_coverage`, `_validate_time_off_conflict` helpers
- Added `AppointmentServiceDep` to `src/app/api/deps.py`
- Added appointment schemas to `src/app/schemas.py`: `AppointmentCreate`, `AppointmentRead`, `AppointmentDetailRead`, `AppointmentStatus`
- Created `src/app/routers/appointments.py`:
  - `POST /api/v1/appointments` (Admin, Receptionist)
  - `GET /api/v1/appointments` (All staff, with filters)
  - `GET /api/v1/appointments/{id}` (All staff)
- Registered appointments router in `src/app/main.py`
- Updated `src/app/services/availability_engine.py` to include appointments in busy intervals
- Updated `src/app/routers/schedules.py` to fetch and pass appointments to availability engine
- Created unit tests:
  - `tests/unit/test_appointment_service.py` (booking validation, shift/time-off/overlap checks, concurrent booking)
  - `tests/unit/test_appointment_repository.py` (CRUD, eager loading N+1, overlap check variations)
  - Updated `tests/unit/test_availability.py` to test appointment subtraction (AC1 from T-007)
- Created API tests:
  - `tests/api/test_appointments.py` (all 5 ACs + RBAC)
  - Updated `tests/api/test_availability_api.py` to test appointment subtraction in availability query

## Round 2 fixes (2026-10-07)
- Added `.with_for_update(nowait=True)` to `check_appointment_overlap` in `src/app/db/repository.py` (blocker fix, ADR 0001 / NFR-1)
- Removed inner `from sqlalchemy import select` in same function (minor fix)
- Replaced `__import__("datetime").timedelta` with top-level imported `timedelta` in `src/app/services/appointment_service.py:102` (major fix)
- Removed redundant tzinfo re-attachment guards from `_validate_shift_coverage` and `_validate_time_off_conflict`; added precondition docstrings (major fix)
- All quality gates green: ruff ?, ruff format ?, mypy ?, pytest ? (103 passed)

## Review history
- **Round 1 (2026-10-07):** Changes requested — 1 blocker (missing `with_for_update()` in overlap check), 1 major (timezone handling inconsistency), 3 minor, 3 nit. Gates: ruff ✓, mypy ✓, pytest ✓ (103 passed). Report: `work/reviews/T-008-review-1.md`
- **Round 2 (2026-10-07):** Changes requested — 1 blocker (with_for_update still absent), 2 major, 2 minor. Gates: ruff ?, mypy ?, pytest ? (103 passed). Report: `work/reviews/T-008-review-2.md`
- **Round 3 (2026-10-07):** Approved — 0 blockers, 0 majors, 0 minors, 2 nits. Gates: ruff ✓, mypy ✓, pytest ✓ (103 passed). Report: `work/reviews/T-008-review-3.md`
