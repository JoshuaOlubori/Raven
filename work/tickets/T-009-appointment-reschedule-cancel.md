---
id: T-009
title: Appointment reschedule and reasoned cancellation
status: todo
mode: AFK
blocked_by: T-008
spec_refs: specs/05-appointments.md#2-layer-1, specs/05-appointments.md#4-layer-3, specs/05-appointments.md#8-state-machine
covers: R-11, R-13
updated: 2026-10-03
---

## Outcome
Staff can reschedule active appointments (`SCHEDULED` or `CONFIRMED`) to new conflict-free slots, or cancel upcoming appointments by providing a mandatory non-empty cancellation reason, immediately freeing the slot for other bookings.

## What to build
- `src/app/services/appointment_service.py`:
  - `reschedule_appointment`: Verifies current state is `SCHEDULED` or `CONFIRMED`, validates that the new slot is within the dentist's shift, checks for overlaps excluding the current appointment ID, updates `start_time` and `end_time`, and resets status to `SCHEDULED`.
  - `cancel_appointment`: Verifies current state permits cancellation, requires non-empty `cancellation_reason`, sets status to `CANCELLED`.
- `src/app/routers/appointments.py`:
  - `POST /api/v1/appointments/{id}/reschedule` (Admin, Receptionist)
  - `POST /api/v1/appointments/{id}/cancel` (Admin, Receptionist)

## Acceptance criteria
- [ ] Given an appointment in `SCHEDULED` or `CONFIRMED` status, When `POST /api/v1/appointments/{id}/reschedule` is submitted with a valid open slot, Then the appointment slot is updated, status is reset to `SCHEDULED`, and `200 OK` is returned (R-11).
- [ ] Given an appointment in `COMPLETED` or `CANCELLED` status, When rescheduling is attempted, Then the system rejects the request with `400 Bad Request` ("Cannot reschedule a completed or cancelled appointment").
- [ ] Given an appointment reschedule to a slot that overlaps another appointment, Then the system returns `409 Conflict`.
- [ ] Given an appointment, When `POST /api/v1/appointments/{id}/cancel` is submitted with reason "Patient has flu", Then status transitions to `CANCELLED` and returns `200 OK` (R-13).
- [ ] Given a cancellation request with an empty reason, When submitted, Then the system rejects the request with `422 Unprocessable Entity` (R-13).
- [ ] Given a cancelled appointment, When availability slots are queried for that time interval, Then the freed slot is immediately available for new bookings.

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | `test_reschedule_appointment_success_200` | API + Receptionist auth | status 200, start_time matches new_slot, status == "SCHEDULED" | PRD R-11 |
| 2 | `test_reschedule_completed_appointment_rejected_400` | API + Receptionist auth | status 400, detail contains "Cannot reschedule" | PRD R-11 |
| 3 | `test_reschedule_to_conflicting_slot_returns_409` | API + Receptionist auth | status 409, error == "APPOINTMENT_OVERLAP_CONFLICT" | Spec 05 §7 |
| 4 | `test_cancel_appointment_with_reason_success_200` | API + Receptionist auth | status 200, status == "CANCELLED", cancellationReason saved | PRD R-13 |
| 5 | `test_cancel_appointment_without_reason_rejected_422` | API + Receptionist auth | status 422, ValidationError on cancellationReason | PRD R-13 |
| 6 | `test_cancelled_appointment_frees_slot_for_booking` | Integration | slot becomes available in availability query | PRD R-13 |

## Out of scope
FSM transitions to `IN_PROGRESS` or `COMPLETED` and audit logs (handled in T-010).

## Notes for the implementer
Ensure `exclude_id` is passed to the overlap check during reschedule so that the appointment does not detect a conflict with its own current slot if only the end time or dentist changes.

## Implementation log

## Review history
