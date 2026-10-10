# Review T-014 round 2 — approve

Gates: ruff ✓ · format ✓ · mypy ✓ · pytest ✓ (164 passed, 2 skipped)

## Spec — findings

No blockers or major findings. The implementation correctly addresses all five acceptance criteria:

- **AC1** (two independent transactions booking overlapping windows → exactly one succeeds, other receives conflict): Implemented via `lock_dentist_appointment_schedule` in `repository.py:427-437` which acquires `SELECT Staff.id ... FOR UPDATE` on the stable dentist row before the overlap check. The lock is held until the transaction commits, serializing concurrent bookings. The PostgreSQL integration test `test_concurrent_postgres_bookings_allow_only_one` (line 179-195) verifies one 201 and one 409 with `APPOINTMENT_OVERLAP_CONFLICT` error code.

- **AC2** (concurrent overlapping reschedules → at most one succeeds): Same stable-row locking strategy applied in `AppointmentService.reschedule_appointment` at `appointment_service.py:339-340`. The integration test `test_concurrent_postgres_reschedules_allow_only_one` (line 202-249) verifies one 200 and one 409, and asserts the two persisted appointments do not overlap (`rows[0].end_time <= rows[1].start_time`).

- **AC3** (non-overlapping/adjacent half-open windows → both can succeed): The overlap query at `repository.py:455-463` uses half-open interval semantics (`start_time < existing.end_time AND end_time > existing.start_time`). The integration test `test_adjacent_appointments_can_both_commit` (line 256-270) books appointments at 9:00-9:45 and 9:45-10:30 and asserts both return 201.

- **AC4** (concurrency enforced by PostgreSQL, not process-local locks): The lock uses `SELECT ... FOR UPDATE` on the `Staff` row (which always exists), not on `Appointment` rows (which may not exist). This is a database-level lock shared across workers. ADR 0001 and Spec 05 §5 are updated to document this strategy.

- **AC5** (genuinely concurrent PostgreSQL test, not sequential SQLite): The new integration test file `test_postgres_appointment_concurrency.py` creates two independent `AsyncClient` requests, uses `asyncio.gather` to fire them concurrently, and a `_synchronize_slot_locks` fixture to ensure both reach the database lock together before either proceeds. The test is skipped when `TEST_POSTGRES_DATABASE_URL` is unset, but the implementation log confirms it passed when configured.

All spec references (05-appointments.md §5, ADR 0001, NFR-1, R-10, R-11) are satisfied.

## Standards — findings

No blockers or major findings. The implementation follows the FastAPI production architecture layers:

- **Layer 1 (Contracts)**: Schemas unchanged; `AppointmentOverlapConflictError` maps to 409 with `APPOINTMENT_OVERLAP_CONFLICT` code per Spec 05 §7.
- **Layer 2 (Persistence)**: New `lock_dentist_appointment_schedule` repository function is pure — accepts session, returns nothing, no business logic. Timestamp columns updated to `DateTime(timezone=True)` in `Appointment`, `AppointmentAuditLog`, `TimeOffBlock`, and `TimestampMixin` to match the existing Alembic migration (timezone-aware). Composite index on `(dentist_id, start_time, end_time, status)` supports the overlap query.
- **Layer 3 (Wiring)**: Locking and overlap queries remain in repository; orchestration in `AppointmentService`. No role checks scattered as `if user.role` — authorization handled at endpoint level via `require_roles` dependency.
- **Layer 4 (Concurrency)**: No blocking work on event loop. The `SELECT ... FOR UPDATE` is awaited and the session is not held open across streaming. `_synchronize_slot_locks` test helper uses `asyncio.Event` correctly (no sleeps).
- **Layer 5 (State/Hardening)**: No module-level mutable state. Audit log remains append-only (NFR-4).

No v1 idioms (`parse_obj()`, `dict()`), no per-row queries in the hot path, no secrets/config inline. Structured logging with correlation IDs exists in the service.

One **nit**: `appointment_service.py:193` and `340` use `lock_dentist_appointment_schedule` but the function name is slightly inconsistent with the repository naming convention (`lock_dentist_...` vs other `check_...`, `list_...`, `create_...` verbs). This is a minor naming deviation from §2; not worth a change request.

## Tests — findings

No blockers or major findings. Test coverage matches the test plan:

- Every acceptance criterion has a test at the named seam (PostgreSQL integration with two API sessions).
- Expected values are independent of implementation: tests assert HTTP status codes (201/409/200) and error codes (`APPOINTMENT_OVERLAP_CONFLICT`), not internal state.
- Tests assert behaviour, not private structure: they would survive a refactor of the locking strategy (e.g., switching to an exclusion constraint) as long as the API contract holds.
- Failure paths exist: 409 with correct error code for overlap, 400 for shift/time-off violations (covered by other tests).
- No sleeps, order dependence, or shared mutable fixtures. The `_synchronize_slot_locks` helper uses `asyncio.Event` to rendezvous two tasks at the lock point — this is a legitimate test synchronization primitive, not a sleep.

**Minor note** (same as Round 1): The concurrent PostgreSQL tests send both requests through one in-process ASGI application. They exercise PostgreSQL row locking correctly because each request gets an independent database session, and the production synchronization is the database lock. A separate process-level regression harness would provide an executable cross-worker proof, but the ticket's AC4 requires "enforced by PostgreSQL and does not depend on process-local locks" — the current tests verify this by relying on the DB lock, not process isolation. This is acceptable for this ticket.

## Summary

Counts: 0 blocker, 0 major, 0 minor, 1 nit. Worst issue: naming nit on `lock_dentist_appointment_schedule`. All quality gates pass. The implementation correctly replaces the empty-result `SELECT FOR UPDATE` on appointment rows with a stable dentist-row lock, adds genuine concurrent PostgreSQL integration tests, and updates specs/ADRs accordingly.

**Verdict: Approve**