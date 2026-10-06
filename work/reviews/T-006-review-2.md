# Review T-006 round 2 — approve
Gates: ruff ✓ · mypy ✓ · pytest ✓ (61 passed)

## Spec — no findings
All 5 acceptance criteria satisfied with tests at the API seam:

| AC | Spec line | Test |
|----|-----------|------|
| AC1 | R-7: Admin POST /shifts → 201 | `test_admin_creates_working_shift_201` |
| AC2 | Spec 04 §2: start_time ≥ end_time → 422/400 | `test_shift_start_after_end_rejected` (schema), `test_time_off_block_start_after_end_rejected` (schema) |
| AC3 | Spec 04 §7: Overlapping shift same dentist/day → 409 SHIFT_OVERLAP | `test_duplicate_or_overlapping_shift_returns_409` |
| AC4 | R-8: Dentist POST /time-off for self → 201 | `test_dentist_creates_own_time_off_201` |
| AC5 | Spec 04 §4: Dentist cannot modify peer time-off → 403 SCHEDULE_FORBIDDEN | `test_dentist_cannot_modify_peer_time_off_403`, `test_dentist_cannot_delete_peer_time_off_403` |

Extra coverage (not required but present): non-overlapping adjacent shifts allowed (`test_non_overlapping_shift_same_day_allowed`), list endpoints, delete endpoints, unauthenticated 401.

## Standards — no findings
All standard checks pass:
- Layer 3 handlers thin, delegate to service via `ScheduleServiceDep` ✓
- Role checks via `require_roles` dependency ✓
- Business rules in schema validators (Layer 1) and service (Layer 2) ✓
- No v1 Pydantic idioms ✓
- Repository queries use `session.get()` and indexed selects ✓
- No blocking I/O, mutable module state, or streaming sessions ✓
- Correct 401 vs 403 semantics ✓
- Naming follows §2 (camelCase API, snake_case internal) ✓
- Global error handler adds correlation ID ✓
- No secrets/config inline ✓
- Fowler smells: none significant

The mypy alias/field mismatch in router projection helpers (`_shift_read`, `_time_off_read`) noted in round 1 has been resolved — the code now constructs response models using snake_case field names (`dentist_id=...`) which work correctly with `populate_by_name=True`.

## Tests — no findings
- Every AC has a dedicated API or schema-unit test ✓
- Expected values from PRD/spec (hard-coded "09:00:00", "Vacation", "SHIFT_OVERLAP", "SCHEDULE_FORBIDDEN") — never recomputed from implementation ✓
- Tests assert HTTP behaviour (status, body fields), not ORM internals ✓
- Failure paths covered: 401 (unauth), 403 (forbidden), 409 (overlap), 422 (validation) ✓
- No sleeps, order dependence, or shared mutable fixtures ✓

## Summary
| Severity | Count |
|----------|-------|
| blocker | 0 |
| major | 0 |
| minor | 0 |
| nit | 0 |

**Verdict: approve** — All acceptance criteria verified, all quality gates pass, no standard violations.