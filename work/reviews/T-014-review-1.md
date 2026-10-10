# Review T-014 round 1 — changes requested

Gates: ruff ✓ · format ✓ · mypy ✓ · pytest ✓ (161 passed, 5 skipped) · PostgreSQL integration ✗ (3 setup errors)

## Spec — findings

No blockers or major findings. Booking and rescheduling acquire the stable dentist-row lock before checking overlaps, and the request transaction commits before releasing the session. This addresses T-014's requirement to serialize empty-range checks and the updated `work/specs/05-appointments.md` §5 strategy. The PostgreSQL tests cover overlapping bookings (201/409 and error code), competing reschedules (200/409 and persisted non-overlap), and adjacent half-open appointments (both 201).

## Standards — findings

No findings. Locking and overlap queries remain in repository functions, with orchestration in `AppointmentService`. The lock is database-backed and shared across workers, consistent with ADR 0001 and the FastAPI architecture layering.

## Tests — findings

- **Major — `backend/tests/integration/test_postgres_appointment_concurrency.py:31-32`:** the configured `TEST_POSTGRES_DATABASE_URL` cannot initialize its SQLAlchemy engine in this environment. The configured URL selects the `psycopg` driver, which is not a project dependency; retrying with the installed `asyncpg` driver also fails because its URL contains the unsupported `sslmode` argument. Normalize the integration URL/driver options for the installed async driver (or declare and install the matching driver) so the PostgreSQL tests can connect and exercise the concurrency behavior.
- **Minor — `backend/tests/integration/test_postgres_appointment_concurrency.py:143-227`:** the concurrent PostgreSQL cases use two request sessions, but send both requests through one in-process ASGI application. They exercise PostgreSQL row locking, though they would not independently detect a future replacement with process-local synchronization. Consider a two-process/two-app-instance integration test if this regression needs an executable cross-worker proof. The implementation itself uses PostgreSQL `SELECT ... FOR UPDATE` on the stable dentist row.

The regular suite initially skipped the PostgreSQL tests because the `.env` file was not loaded. With it explicitly loaded, all three PostgreSQL integration tests errored during engine setup before connecting or creating a schema. The credential value is not included here.

## Summary

Counts: 0 blocker, 1 major, 1 minor, 0 nit. Worst issue: the configured PostgreSQL integration suite cannot initialize a database connection, leaving the ticket's defining concurrency behavior unverified. Changes requested.
