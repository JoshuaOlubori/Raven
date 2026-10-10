---
id: T-015
title: Require an explicit JWT signing secret outside development
status: todo
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
- [ ] Given `APP_ENV` is production and `JWT_SECRET_KEY` is missing, When settings load, Then startup fails with a clear configuration error.
- [ ] Given a production secret equals the current development default or is below the documented minimum strength, When settings load, Then startup fails.
- [ ] Given a sufficiently strong explicit production secret, When settings load, Then startup succeeds.
- [ ] Given development configuration, When no secret is provided, Then documented local behavior remains usable.
- [ ] Error messages do not include the supplied secret value.

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | test_production_requires_explicit_jwt_secret | Settings unit | validation error when omitted | F-003 |
| 2 | test_production_rejects_known_default_secret | Settings unit | validation error | NFR-6 |
| 3 | test_production_accepts_strong_secret | Settings unit | settings constructed | deployment configuration contract |
| 4 | test_secret_value_not_in_validation_error | Settings unit | error omits secret contents | security review |

## Out of scope
Secret vault provisioning, rotation workflows and token key identifiers.

## Notes for the implementer
Use the existing `APP_ENV` setting in validation; do not log settings values on failure.

## Implementation log

## Review history
