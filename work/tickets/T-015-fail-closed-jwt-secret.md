---
id: T-015
title: Require an explicit JWT signing secret outside development
status: in-review
mode: AFK
blocked_by: -
spec_refs: specs/00-architecture.md#4-cross-cutting-design, reviews/final-review.md#f-003-known-jwt-signing-key-is-accepted-as-a-runtime-default
covers: NFR-6
updated: 2026-10-10
---

## Outcome
Production and non-development environments cannot start with a known or weak JWT signing key.

## What to build
Validate runtime settings so non-development environments require an explicitly configured strong `JWT_SECRET_KEY` and reject the current insecure default. Keep local development and isolated test setup usable without weakening production validation.

## Acceptance criteria
- [x] Given `APP_ENV` is production and `JWT_SECRET_KEY` is missing, When settings load, Then startup fails with a clear configuration error.
- [x] Given a production secret equals the current development default or is below the documented minimum strength, When settings load, Then startup fails.
- [x] Given a sufficiently strong explicit production secret, When settings load, Then startup succeeds.
- [x] Given development configuration, When no secret is provided, Then documented local behavior remains usable.
- [x] Error messages do not include the supplied secret value.

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|---|
| 1 | test_production_requires_explicit_jwt_secret | Settings unit | validation error when omitted | F-003 |
| 2 | test_production_rejects_known_default_secret | Settings unit | validation error | NFR-6 |
| 3 | test_production_accepts_strong_secret | Settings unit | settings constructed | deployment configuration contract |
| 4 | test_secret_value_not_in_validation_error | Settings unit | error omits secret contents | security review |

## Out of scope
Secret vault provisioning, rotation workflows and token key identifiers.

## Notes for the implementer
Use the existing `APP_ENV` setting in validation; do not log settings values on failure.

## Implementation log
- Added model validator `_validate_jwt_secret_for_env` to `Settings` class in `backend/src/app/config.py`
- Validation rejects the development default secret (`dev-insecure-secret-change-in-production`) in non-development environments
- Validation enforces minimum 32-character secret length in non-development environments
- Validation enforces strong secret requirements (uppercase, lowercase, digit, special char) in non-development environments via `_is_strong_secret()` helper and regex pattern
- Environment check is case-insensitive (development, Development, DEVELOPMENT all treated as development)
- Error messages do not include the secret value
- Development environment continues to allow the default insecure secret for local usability
- Added 15 unit tests in `backend/tests/unit/test_config.py` covering all acceptance criteria plus weak-but-long secret rejection
- All quality gates pass: ruff check, ruff format, mypy, pytest (173 passed, 2 skipped)

## Review history
- Round 1: [review report](../reviews/T-015-review-1.md) — changes requested (0 blocker, 1 major, 0 minor, 0 nit).
- Round 2: fixes implemented; strength validation added; tests expanded to cover weak-but-long secrets.
