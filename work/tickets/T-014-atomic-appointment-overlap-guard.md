---
id: T-014
title: Enforce atomic cross-worker appointment overlap prevention
status: in-review
mode: AFK
blocked_by: -
spec_refs: specs/05-appointments.md#5-concurrency, reviews/final-review.md#f-002-appointment-overlap-protection-does-not-serialize-empty-range-checks
covers: R-10, R-11, NFR-1
updated: 2026-10-10
---

## Outcome
Concurrent booking and rescheduling requests for overlapping dentist time cannot both commit, across independent application workers.

## What to build
Replace the empty-result `SELECT FOR UPDATE` guard with a database-enforced or otherwise correctly serialized strategy for PostgreSQL. Apply it consistently to booking and rescheduling. Add a true concurrency integration test using two independent PostgreSQL sessions and verify the API maps the losing transaction to `409 Conflict`.

## Acceptance criteria
- [x] Given two independent transactions booking overlapping windows for the same dentist at the same time, When both attempt to commit, Then exactly one succeeds and the other receives a conflict.
- [x] Given concurrent overlapping reschedules, When both attempt to commit, Then at most one succeeds.
- [x] Given non-overlapping or adjacent half-open appointment windows, When booked concurrently, Then both can succeed.
- [x] The concurrency guarantee is enforced by PostgreSQL and does not depend on process-local locks.
- [x] The test is genuinely concurrent and runs against PostgreSQL; a sequential SQLite test is not used as proof.

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | `test_concurrent_postgres_bookings_allow_only_one` | PostgreSQL integration, two API sessions | one commit and one 409 with `APPOINTMENT_OVERLAP_CONFLICT` | PRD NFR-1 |
| 2 | `test_concurrent_postgres_reschedules_allow_only_one` | PostgreSQL integration, two API sessions | no overlapping committed rows; one request succeeds | PRD NFR-1 |
| 3 | `test_adjacent_appointments_can_both_commit` | PostgreSQL integration, two API sessions | both commits succeed | interval semantics in spec 05 |
| 4 | Included in `test_concurrent_postgres_bookings_allow_only_one` | API + PostgreSQL | losing request returns 409 | PRD R-10/NFR-1 |

## Out of scope
Availability query performance tuning unrelated to the overlap constraint.

## Notes for the implementer
PostgreSQL `SELECT ... FOR UPDATE` cannot lock a row that does not yet exist. Consider an exclusion constraint over dentist and time range, or a stable dentist-row/advisory lock held through transaction commit. Account for SQLite unit-test limitations.

## Implementation log

- Replaced the empty-result appointment-row lock with a `SELECT ... FOR UPDATE` on the stable dentist row. Booking and rescheduling use the same lock before overlap checks, which remains held until the request transaction commits.
- Added synchronized PostgreSQL API integration tests for overlapping concurrent bookings (including 409 mapping), overlapping concurrent reschedules, and adjacent half-open bookings. The test creates a disposable schema per case and is configured through `TEST_POSTGRES_DATABASE_URL`.
- Renamed SQLite checks to state that they cover sequential conflict mapping only. Updated Spec 05 and ADR 0001 to specify the stable-row locking strategy.
- Validation: `uv run --directory backend ruff check` passed; `uv run --directory backend ruff format --check` passed (67 files); `uv run --directory backend mypy src` passed (39 files); `uv run --directory backend pytest -q` passed (161 passed, 5 skipped). PostgreSQL integration cases were skipped because `TEST_POSTGRES_DATABASE_URL` is not configured in this environment.
- Assumption: the approved overlap-guard spec's appointment-row `FOR UPDATE` description was incomplete for empty result sets. T-014 explicitly calls for a database-enforced or correctly serialized strategy; the implementation uses the stable dentist-row lock and updates Spec 05 accordingly.
- Implementation commit: `794da4c`.

## Review history
