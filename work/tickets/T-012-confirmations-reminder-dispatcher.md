---
id: T-012
title: Booking confirmations and 24h reminder dispatcher
status: todo
mode: AFK
blocked_by: T-010
spec_refs: specs/06-notifications-events.md#2-layer-1, specs/06-notifications-events.md#3-layer-2, specs/06-notifications-events.md#4-layer-3, specs/06-notifications-events.md#6-layer-5
covers: R-16, R-17, NFR-5
updated: 2026-10-03
---

## Outcome
Patients automatically receive booking/reschedule confirmation messages (via pluggable `NotificationService`), and an automated dual-mode dispatcher identifies appointments within 23–25 hours to dispatch pre-visit reminders idempotently.

## What to build
- `src/app/services/notification_service.py`: `NotificationService` protocol and `LoggingNotificationService` adapter for dev/test environments.
- `src/app/db/repository.py`:
  - `list_pending_reminders`: Queries appointments in `SCHEDULED` or `CONFIRMED` status starting between 23 and 25 hours away with `reminder_sent_at IS NULL`.
  - `mark_reminder_sent`: Atomically sets `reminder_sent_at = utcnow()`.
- `src/app/routers/appointments.py`:
  - `POST /api/v1/appointments/reminders/dispatch`: Protected maintenance endpoint (Admin only or system key) triggering the reminder job per ADR 0002.
- `src/app/main.py`: Optional in-process lifespan background loop (active when `settings.ENABLE_IN_PROCESS_REMINDER_WORKER = True`) executing the reminder check every 15 minutes.
- Wire booking and reschedule confirmation calls into `AppointmentService`.

## Acceptance criteria
- [ ] Given a successful appointment booking, When the database transaction commits, Then a booking confirmation is dispatched asynchronously via `NotificationService` (R-16).
- [ ] Given a successful appointment reschedule, When committed, Then a reschedule confirmation is dispatched with old and new slot times (R-16).
- [ ] Given an appointment scheduled 24 hours in the future with `reminder_sent_at` as null, When the reminder job runs, Then a reminder notification is dispatched and `reminder_sent_at` is set (R-17).
- [ ] Given an appointment that already received a reminder, When the reminder job runs again, Then no duplicate reminder is sent (R-17, ADR 0002).
- [ ] Given an external scheduler calling `POST /api/v1/appointments/reminders/dispatch`, Then it returns `200 OK` with `dispatchedCount` and time window details.

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | `test_booking_dispatches_confirmation_asynchronously` | Service with fakes | `FakeNotificationService.dispatched_bookings` contains appointment | PRD R-16 |
| 2 | `test_reschedule_dispatches_reschedule_confirmation` | Service with fakes | `FakeNotificationService.dispatched_reschedules` contains old/new time | PRD R-16 |
| 3 | `test_reminder_query_selects_appointments_in_23_to_25h_window` | Repository + DB | 24h appointment included; 22h and 26h appointments excluded | PRD R-17 |
| 4 | `test_reminder_dispatch_is_idempotent` | Integration | second execution dispatches 0 reminders; reminder_sent_at unchanged | ADR 0002 |
| 5 | `test_reminder_maintenance_endpoint_admin_guard` | API + Admin auth | status 200, dispatchedCount >= 1; 403 for receptionist | Spec 06 §4 |

## Out of scope
Third-party Twilio/SendGrid production accounts (v1 uses `LoggingNotificationService` adapter).

## Notes for the implementer
Follow ADR 0002 dual-mode execution strategy: the maintenance endpoint supports stateless multi-worker production deployments (NFR-5), while the lifespan asyncio task provides zero-config local operation.

## Implementation log

## Review history
