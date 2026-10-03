---
id: T-008
title: Appointment booking and atomic overlap guard
status: todo
mode: AFK
blocked_by: T-005, T-007
spec_refs: specs/05-appointments.md#2-layer-1, specs/05-appointments.md#3-layer-2, specs/05-appointments.md#4-layer-3, specs/05-appointments.md#5-layer-4
covers: R-10, NFR-1
updated: 2026-10-03
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

## Review history
