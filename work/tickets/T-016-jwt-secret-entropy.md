---
id: T-016
title: Reject guessable JWT signing secrets in non-development environments
status: in-progress
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
- [x] Given a non-development environment and a minimum-length key made by repeating a short mixed-class pattern, when settings are created, then validation fails. (`test_production_rejects_repeated_mixed_class_secret`)
- [x] Given a non-development environment and a predictable sequence/patterned key, when settings are created, then validation fails. (`test_production_rejects_predictable_patterned_secret`)
- [x] Given a non-development environment and a cryptographically random key meeting the documented minimum, when settings are created, then validation succeeds. (`test_production_accepts_cryptographically_random_secret`)
- [x] Given any rejected key, when the validation error is rendered, then the key value is not exposed. (Rejection tests assert secret absence; settings field is excluded from model repr.)
- [x] Development continues to allow its local default and weak test keys. (`test_development_allows_default_secret`, `test_development_allows_weak_secret`)

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
- Replaced character-class-only validation with a documented 43-character URL-safe key format produced by `secrets.token_urlsafe(32)`; validation rejects low-diversity, repeated, and sequential patterns.
- Set `jwt_secret_key` to `repr=False` so Pydantic model validation errors do not render the configured secret.
- Documented safe generation in the architecture config-and-secrets contract; updated config unit tests for repeated, sequential, generated, and development values.
- Files: `backend/src/app/config.py`, `backend/tests/unit/test_config.py`, `work/specs/00-architecture.md`.
- Checks: `git diff --check` passed. Bundled Python AST parse and isolated validator checks passed. `pytest` and Ruff could not run: the project `.venv` interpreter is inaccessible to this session, and `uv` cannot persist its interpreter cache; bundled Python has no `pytest` module. Full quality gates remain outstanding.
- No spec deviations. Committed as `T-016: reject guessable JWT signing secrets`. Ticket remains in-progress until the project quality gates can run and pass.

## Review history
_(links to work/reviews/T-016-review-N.md)_
