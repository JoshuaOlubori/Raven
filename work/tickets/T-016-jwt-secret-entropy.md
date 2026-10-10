---
id: T-016
title: Reject guessable JWT signing secrets in non-development environments
status: todo
mode: AFK
blocked_by: -
spec_refs: reviews/final-review.md#f-001-major-jwt-secret-validation-accepts-guessable-repeated-strings, specs/00-architecture.md#4-cross-cutting-design
covers: NFR-6
updated: 2026-10-10
---

## Outcome
Non-development deployments cannot start with a JWT signing key that is easy to guess, so attackers cannot forge staff access tokens using a patterned secret.

## What to build
Strengthen `backend/src/app/config.py` validation beyond length and character classes. Require a cryptographically generated high-entropy key or otherwise reject repeated, patterned, and common weak values. Keep validation errors free of the supplied secret. Update `backend/tests/unit/test_config.py` with weak-pattern rejection and strong-key acceptance cases.

## Acceptance criteria
- [ ] Given a non-development environment and a minimum-length key made by repeating a short mixed-class pattern, when settings are created, then validation fails.
- [ ] Given a non-development environment and a predictable sequence/patterned key, when settings are created, then validation fails.
- [ ] Given a non-development environment and a cryptographically random key meeting the documented minimum, when settings are created, then validation succeeds.
- [ ] Given any rejected key, when the validation error is rendered, then the key value is not exposed.
- [ ] Development continues to allow its local default and weak test keys.

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | test_production_rejects_repeated_mixed_class_secret | Settings unit | `ValidationError`; key absent from error | Final review F-001, NFR-6 |
| 2 | test_production_rejects_predictable_patterned_secret | Settings unit | `ValidationError`; key absent from error | Final review F-001, security requirement |
| 3 | test_production_accepts_cryptographically_random_secret | Settings unit | Settings accepted | Architecture secret configuration |
| 4 | test_development_allows_weak_secret | Settings unit | Settings accepted | Existing development behavior |

## Out of scope
JWT algorithm migration, key rotation workflows, and deployment secret-vault provisioning.

## Notes for the implementer
Do not claim entropy based only on a string's character diversity. Prefer a clear operational requirement for generated secrets and document how to generate one without logging it.

## Implementation log
_(filled by sdd-implement)_

## Review history
_(links to work/reviews/T-016-review-N.md)_
