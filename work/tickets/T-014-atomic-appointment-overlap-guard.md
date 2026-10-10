---
id: T-014
title: Enforce atomic cross-worker appointment overlap prevention
status: todo
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
- [ ] Given two independent transactions booking overlapping windows for the same dentist at the same time, When both attempt to commit, Then exactly one succeeds and the other receives a conflict.
- [ ] Given concurrent overlapping reschedules, When both attempt to commit, Then at most one succeeds.
- [ ] Given non-overlapping or adjacent half-open appointment windows, When booked concurrently, Then both can succeed.
- [ ] The concurrency guarantee is enforced by PostgreSQL and does not depend on process-local locks.
- [ ] The test is genuinely concurrent and runs against PostgreSQL; a sequential SQLite test is not used as proof.

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | test_concurrent_postgres_bookings_allow_only_one | PostgreSQL integration, two sessions | one commit and one 409 | PRD NFR-1 |
| 2 | test_concurrent_postgres_reschedules_allow_only_one | PostgreSQL integration, two sessions | no overlapping committed rows | PRD NFR-1 |
| 3 | test_adjacent_appointments_can_both_commit | PostgreSQL integration | both commits succeed | interval semantics in spec 05 |
| 4 | test_conflict_maps_to_409 | API + PostgreSQL | losing request returns 409 | PRD R-10/NFR-1 |

## Out of scope
Availability query performance tuning unrelated to the overlap constraint.

## Notes for the implementer
PostgreSQL `SELECT ... FOR UPDATE` cannot lock a row that does not yet exist. Consider an exclusion constraint over dentist and time range, or a stable dentist-row/advisory lock held through transaction commit. Account for SQLite unit-test limitations.

## Implementation log

## Review history
