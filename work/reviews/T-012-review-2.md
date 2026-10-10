# Review T-012 round 2 — Changes requested
Gates: ruff ✓ · format ✗ (61 files formatted; invalid UTF-8 in `work/TRACKER.md`) · mypy ✓ · pytest ✓ (149 passed, 2 skipped)

## Spec — findings

### Blocker — Failed reminder delivery is permanently marked as sent
`backend/src/app/db/repository.py:589-599` sets `reminder_sent_at` as part of the claim before delivery. Both dispatch paths then catch notification failures and commit the claim (`backend/src/app/routers/appointments.py:323-333`, `backend/src/app/main.py:93-101`). The PRD says, “Upon sending, updates `reminder_sent_at` timestamp to prevent duplicate notifications” (`work/prd.md:225`), and R-17 acceptance requires the reminder to be dispatched and the timestamp populated (`work/prd.md:227`). If a provider raises, the timestamp remains populated while no reminder was sent, so all later runs skip the appointment. Keep concurrency-safe claiming while ensuring failed deliveries remain retryable (for example, use a separate claim state or clear/release failed claims).

### Major — Confirmation delivery still delays the booking/reschedule response
The registered callbacks are awaited inline after commit by `get_db_session` (`backend/src/app/api/deps.py:45-51`), and each callback awaits the notification provider (`backend/src/app/services/appointment_service.py:215-226,379-392`). R-16 requires an asynchronous confirmation dispatch task after commit (`work/prd.md:215,218`), and the T-012 outcome says notifications are dispatched asynchronously. A slow provider therefore holds the request open after commit. Schedule the post-commit delivery as a managed background task, and test that the response does not wait for provider completion.

## Standards — findings

### Blocker — A credential is committed in the Codex config
`.codex/config.toml:6` contains a hard-coded credential in the T-012 diff. This violates the architecture's configuration/secrets rule (`work/specs/00-architecture.md:4`) and exposes the credential to anyone with repository access. Remove the credential from version control, load it from an environment secret, and revoke/rotate the exposed credential.

### Minor — Reminder orchestration is duplicated in bootstrap and router
`backend/src/app/main.py:77-101` and `backend/src/app/routers/appointments.py:295-333` each implement window calculation, claiming, delivery, and persistence. The FastAPI architecture calls for `main.py` to remain thin bootstrap with no business logic and routers to delegate through services. Put the shared dispatch operation behind a service and have both entry points call it.

## Tests — findings

### Major — The required CONFIRMED status is not tested
The query criterion includes both `SCHEDULED` and `CONFIRMED` appointments (`work/tickets/T-012-confirmations-reminder-dispatcher.md`, “What to build”), but the reminder repository test only inserts a `SCHEDULED` appointment (`backend/tests/unit/test_appointment_repository.py:373-470`). Add an eligible `CONFIRMED` row and assert it is returned.

### Major — API success test does not assert actual delivery or persisted timestamp
`backend/tests/api/test_appointments.py:1397-1415` checks only the response count and window fields; it does not verify the notification fake received the reminder or that `reminder_sent_at` was persisted. The idempotency test also does not assert that timestamp is non-null after the first successful delivery. Assert both effects to catch a response that reports success without sending or recording it.

### Major — No test covers provider failure and later retry
The code logs and suppresses `send_reminder` exceptions, then commits the claim (`backend/src/app/routers/appointments.py:323-333`; same behavior in `backend/src/app/main.py:93-101`). No test exercises a failing notification provider followed by a retry. Add a failure-then-success test proving an unsuccessful attempt does not permanently suppress the reminder.

## Summary

| Severity | Count | Key |
|---|---:|---|
| Blocker | 2 | Failed reminders are permanently suppressed; committed config contains a credential |
| Major | 4 | Confirmation dispatch blocks the request; three acceptance/test coverage gaps |
| Minor | 1 | Reminder orchestration is duplicated |
| Nit | 0 | — |

Worst issue: the repository contains an exposed credential; revoke it and remove it from version control. The functional blocker is that notification failures are committed as completed reminders and cannot be retried.

Verdict: **Changes requested**. Ruff, mypy, and pytest passed. Format check exited nonzero because `work/TRACKER.md` is not valid UTF-8; Ruff reported 61 files already formatted.
