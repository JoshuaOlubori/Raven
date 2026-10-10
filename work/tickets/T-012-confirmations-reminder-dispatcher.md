---
id: T-012
title: Booking confirmations and 24h reminder dispatcher
status: in-progress
mode: AFK
blocked_by: T-010
spec_refs: specs/06-notifications-events.md#2-layer-1, specs/06-notifications-events.md#3-layer-2, specs/06-notifications-events.md#4-layer-3, specs/06-notifications-events.md#6-layer-5
covers: R-16, R-17, NFR-5
updated: 2026-10-10
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
- [x] Given a successful appointment booking, When the database transaction commits, Then a booking confirmation is dispatched asynchronously via `NotificationService` (R-16).
- [x] Given a successful appointment reschedule, When committed, Then a reschedule confirmation is dispatched with old and new slot times (R-16).
- [x] Given an appointment scheduled 24 hours in the future with `reminder_sent_at` as null, When the reminder job runs, Then a reminder notification is dispatched and `reminder_sent_at` is set (R-17).
- [x] Given an appointment that already received a reminder, When the reminder job runs again, Then no duplicate reminder is sent (R-17, ADR 0002).
- [x] Given an external scheduler calling `POST /api/v1/appointments/reminders/dispatch`, Then it returns `200 OK` with `dispatchedCount` and time window details.

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | `test_booking_dispatches_confirmation_asynchronously` | Service with fakes | `FakeNotificationService.dispatched_bookings` contains appointment | PRD R-16 |
| 2 | `test_reschedule_dispatches_reschedule_confirmation` | Service with fakes | `FakeNotificationService.dispatched_reschedules` contains old/new time | PRD R-16 |
| 3 | `test_reminder_query_selects_appointments_in_23_to_25h_window` | Repository + DB | 24h appointment included; 22h and 26h appointments excluded | PRD R-17 |
| 4 | `test_reminder_dispatch_is_idempotent` | Integration | second execution dispatches 0 reminders; reminder_sent_at unchanged | ADR 0002 |
| 5 | `test_reminder_maintenance_endpoint_admin_guard` | API + Admin auth | status 200, dispatchedCount >= 1; 403 for receptionist | Spec 06 §4 |
| 6 | `test_failed_reminder_delivery_can_be_retried` | API + notification fake | failed attempt leaves reminder pending; later success stamps delivery | PRD R-17 |
| 7 | `test_post_commit_callbacks_run_after_successful_commit` | DB dependency + BackgroundTasks | callback is queued after commit and runs after response work | PRD R-16, Spec 06 §6 |

## Out of scope
Third-party Twilio/SendGrid production accounts (v1 uses `LoggingNotificationService` adapter).

## Notes for the implementer
Follow ADR 0002 dual-mode execution strategy: the maintenance endpoint supports stateless multi-worker production deployments (NFR-5), while the lifespan asyncio task provides zero-config local operation.

## Implementation log
- Added `ReminderDispatchResult` schema to `src/app/schemas.py` (Spec 06 §2)
- Added `list_pending_reminders`, `mark_reminder_sent`, and `claim_pending_reminders` repository functions to `src/app/db/repository.py` with atomic claim via UPDATE ... WHERE reminder_sent_at IS NULL RETURNING
- Added reminder dispatch endpoint `POST /api/v1/appointments/reminders/dispatch` to `src/app/routers/appointments.py` with Admin-only RBAC guard (uses atomic claim)
- Added in-process reminder worker loop in `src/app/main.py` lifespan (controlled by `ENABLE_IN_PROCESS_REMINDER_WORKER` setting, uses atomic claim)
- Wired booking confirmation dispatch in `AppointmentService.book_appointment()` via post-response background tasks after a successful commit (Spec 06 §6)
- Wired reschedule confirmation dispatch in `AppointmentService.reschedule_appointment()` via post-response background tasks, preserving old/new times (Spec 06 §6)
- Updated `NotificationService` protocol: `send_reschedule_confirmation` now accepts `old_start_time` and `new_start_time` parameters
- Updated `LoggingNotificationService` to log both old and new times
- Added `FakeNotificationService` test helper capturing dispatched notifications with old/new times
- Added tests:
  - `test_booking_dispatches_confirmation_asynchronously` (service + fakes, verifies post-commit dispatch)
  - `test_booking_confirmation_not_dispatched_on_rollback` (verifies no dispatch on rollback)
  - `test_reschedule_dispatches_reschedule_confirmation` (service + fakes, verifies old/new times)
  - `test_list_pending_reminders_selects_23_to_25h_window` (repository + DB)
  - `test_mark_reminder_sent_idempotent` (repository + DB)
  - `test_reminder_dispatch_endpoint_admin_200` (API + Admin auth)
  - `test_reminder_dispatch_endpoint_receptionist_403` (API + RBAC)
  - `test_reminder_dispatch_is_idempotent` (integration)
  - `test_reminder_dispatch_unauthenticated_401` (API auth)
  - `test_reminder_dispatch_concurrent_requests_no_duplicates` (concurrent dispatch race test)
- Initial implementation gates: Ruff check, formatting, and mypy passed; pytest 149 passed, 2 skipped.
- Review round 2 fixes:
  - Added `ReminderDispatcher` service shared by the HTTP endpoint and lifespan worker.
  - Kept atomic claims uncommitted until delivery; successful sends receive a delivery timestamp, failed sends release the claim so a later run can retry.
  - Registered post-commit callbacks as FastAPI `BackgroundTasks`, so confirmation and event work runs after the response instead of delaying it.
  - Added coverage for `CONFIRMED` reminders, actual endpoint delivery and persistence, provider failure/retry, and deferred callback execution.
  - Added `.codex/` to `.gitignore` and removed its config from the Git index while preserving the local file.
  - Kept SSE event callbacks on the post-commit path; only patient notifications are deferred until after the response.
- Round 2 validation: Ruff check passed; Ruff format check passed for source/tests when excluding generated `work/TRACKER.md`; mypy passed; pytest 151 passed, 2 skipped. The unfiltered format command still reports an invalid UTF-8 stream for the generated tracker.

## Review history

- [Review round 1 — Changes requested](../reviews/T-012-review-1.md): duplicate reminder race, pre-commit confirmation dispatch, and missing old reschedule time.
- **Implementation follow-up after round 1**: atomic claim via UPDATE ... RETURNING prevents duplicate reminders; confirmations use after_commit_callbacks for post-commit dispatch; reschedule confirmation includes old and new slot times.
- [Review round 2 — Changes requested](../reviews/T-012-review-2.md): failed reminder deliveries are committed as sent; confirmation delivery still blocks the response; credential is committed in `.codex/config.toml`; missing CONFIRMED-status and delivery-persistence assertions.
- **Implementation follow-up after round 2**: shared dispatcher releases failed claims and stamps only successful deliveries; confirmation notifications run as response background tasks; endpoint and worker use the same dispatcher; tests cover `CONFIRMED`, delivery persistence, retry after provider failure, and callback timing.
