# Review T-012 round 1 — Changes requested
Gates: ruff ✗ · format ✗ · mypy ✗ · pytest ✗ (all blocked: `uv` could not start `backend/.venv/Scripts/python.exe`; no gates executed)

## Spec — findings

### Blocker — Reminder dispatch is not safe under concurrent triggers
`backend/src/app/routers/appointments.py:323-328` sends each reminder before attempting the conditional `reminder_sent_at IS NULL` update and commit. `backend/src/app/main.py:94-101` repeats the same order. Two schedulers/workers can both select the same null row, both send, then one or both conditional updates succeed. The row update is not a claim before delivery and its affected-row count is ignored. This violates R-17's no-duplicate behavior and ADR 0002's requirement for atomic claiming or row locking so simultaneous triggers cannot double-send. Claim eligible rows atomically before delivery (for example with an atomic claim/row lock strategy), and dispatch only claimed rows.

### Major — Confirmation tasks can run before the booking/reschedule transaction commits
`backend/src/app/services/appointment_service.py:215-218` and `:366-369` create fire-and-forget tasks directly from the service. The request-scoped session commits later in `backend/src/app/api/deps.py:40-46`; a task can therefore send before that commit, and still send if the request transaction subsequently rolls back. Spec 06 §5 says confirmation dispatch occurs when booking/rescheduling commits; its §6 also requires event publication only after commit. Register confirmation work for post-commit execution, then schedule it asynchronously.

### Major — Reschedule confirmation omits the old slot time
The ticket acceptance criterion requires the confirmation to include old and new slot times. `backend/src/app/services/appointment_service.py:338-367` captures `old_start_time` for the audit record but passes only the updated appointment to `send_reschedule_confirmation`. The protocol and logging adapter in `backend/src/app/services/notification_service.py:38-40,78-90` consequently have access only to the new time. Pass both values (or an immutable reschedule payload) through the notification port and assert both in the test.

## Standards — findings

- **Concurrency/idempotency:** The reminder code performs external I/O before establishing the database claim. This conflicts with ADR 0002 and the FastAPI architecture's concurrency and shared-state requirements for multi-worker execution.
- **Post-commit side effects:** Confirmation delivery bypasses the existing `after_commit_callbacks` mechanism in `backend/src/app/api/deps.py:40-53`; the service schedules work before the transaction boundary.

## Tests — findings

- `backend/tests/unit/test_appointment_service.py:686-728` does not verify post-commit dispatch or rollback behavior; it waits with `asyncio.sleep(0.1)`. The reschedule test at `:731-782` checks only the new slot and also sleeps, so it does not cover the ticket's old-and-new payload criterion. Use deterministic task synchronization and assert both times.
- The reminder integration test covers sequential retries only. It does not exercise two concurrent dispatches, so it misses the duplicate-send race above. Add a concurrent dispatcher test proving one notification is emitted.
- Quality gates could not execute because the configured `backend/.venv/Scripts/python.exe` is inaccessible to `uv`; results are unverified.

## Summary

| Severity | Count | Key |
|---|---:|---|
| Blocker | 1 | Concurrent reminder dispatch can send duplicates |
| Major | 2 | Confirmations may send before commit; reschedule payload omits old slot |
| Minor | 0 | — |
| Nit | 0 | — |

Worst issue: the reminder dispatcher's conditional update happens after notification delivery and does not prevent multiple workers from sending the same reminder.

Verdict: **Changes requested**. Quality gates remain unverified because the environment could not start the configured Python interpreter.
