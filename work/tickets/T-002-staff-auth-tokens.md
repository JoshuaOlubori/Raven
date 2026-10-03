---
id: T-002
title: Staff authentication and token issuance
status: todo
mode: AFK
blocked_by: T-001
spec_refs: specs/01-auth-staff.md#2-layer-1, specs/01-auth-staff.md#3-layer-2, specs/01-auth-staff.md#4-layer-3
covers: R-1, NFR-6
updated: 2026-10-03
---

## Outcome
Staff members can securely log in using email and password to receive a signed JWT access token, and verify their authenticated profile at `/api/v1/auth/me`.

## What to build
- `src/app/models/staff.py`: `Staff` ORM model (`id`, `email`, `hashed_password`, `full_name`, `role`, `is_active`, `created_at`).
- `src/app/services/auth_service.py`: Password hashing and verification using Argon2 offloaded to thread pool (`loop.run_in_executor`), JWT token generation and validation.
- `src/app/api/auth.py`: `CurrentUser` dataclass, `get_current_user` dependency extracting Bearer token from `Authorization` header, and `CurrentUserDep` type alias.
- `src/app/routers/auth.py`: `POST /api/v1/auth/token` returning `TokenResponse` and `GET /api/v1/auth/me` returning `StaffRead`.

## Acceptance criteria
- [ ] Given valid active staff credentials, When `POST /api/v1/auth/token` is submitted, Then it returns `200 OK` with a valid Bearer JWT token, expiration, and user role (R-1).
- [ ] Given an invalid password or non-existent email, When `POST /api/v1/auth/token` is submitted, Then it returns `401 Unauthorized` with error code `AUTH_INVALID_CREDENTIALS`.
- [ ] Given an inactive staff account (`is_active = False`), When login is attempted, Then it returns `401 Unauthorized` with error code `AUTH_INACTIVE_ACCOUNT`.
- [ ] Given a valid Bearer token, When `GET /api/v1/auth/me` is requested, Then it returns `200 OK` with the authenticated staff member's profile.
- [ ] Given a missing or expired Bearer token, When accessing protected endpoints, Then it returns `401 Unauthorized`.

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | `test_login_success_returns_jwt_token` | API | status 200, access_token in body, token_type == "bearer" | PRD R-1 |
| 2 | `test_login_invalid_password_returns_401` | API | status 401, error == "AUTH_INVALID_CREDENTIALS" | Spec 01 §7 |
| 3 | `test_login_inactive_user_returns_401` | API | status 401, error == "AUTH_INACTIVE_ACCOUNT" | Spec 01 §7 |
| 4 | `test_auth_me_returns_current_user_profile` | API + auth header | status 200, email and role match fixture | PRD R-1 |
| 5 | `test_password_hashing_uses_argon2_and_threadpool` | Service unit | Argon2 hash prefix, password verified | NFR-6 |

## Out of scope
Admin staff management CRUD and RBAC endpoint guards (handled in T-003).

## Notes for the implementer
Offload Argon2 hashing/verification to `loop.run_in_executor(None, ...)` to ensure the async event loop is never blocked by CPU-intensive cryptography.

## Implementation log

## Review history
