---
id: T-002
title: Staff authentication and token issuance
status: done
mode: AFK
blocked_by: T-001
spec_refs: specs/01-auth-staff.md#2-layer-1, specs/01-auth-staff.md#3-layer-2, specs/01-auth-staff.md#4-layer-3
covers: R-1, NFR-6
updated: 2026-10-05
---

## Outcome
Staff members can securely log in using email and password to receive a signed JWT access token, and verify their authenticated profile at `/api/v1/auth/me`.

## What to build
- `src/app/models/staff.py`: `Staff` ORM model (`id`, `email`, `hashed_password`, `full_name`, `role`, `is_active`, `created_at`).
- `src/app/services/auth_service.py`: Password hashing and verification using Argon2 offloaded to thread pool (`loop.run_in_executor`), JWT token generation and validation.
- `src/app/api/auth.py`: `CurrentUser` dataclass, `get_current_user` dependency extracting Bearer token from `Authorization` header, and `CurrentUserDep` type alias.
- `src/app/routers/auth.py`: `POST /api/v1/auth/token` returning `TokenResponse` and `GET /api/v1/auth/me` returning `StaffRead`.

## Acceptance criteria
- [x] Given valid active staff credentials, When `POST /api/v1/auth/token` is submitted, Then it returns `200 OK` with a valid Bearer JWT token, expiration, and user role (R-1).
- [x] Given an invalid password or non-existent email, When `POST /api/v1/auth/token` is submitted, Then it returns `401 Unauthorized` with error code `AUTH_INVALID_CREDENTIALS`.
- [x] Given an inactive staff account (`is_active = False`), When login is attempted, Then it returns `401 Unauthorized` with error code `AUTH_INACTIVE_ACCOUNT`.
- [x] Given a valid Bearer token, When `GET /api/v1/auth/me` is requested, Then it returns `200 OK` with the authenticated staff member's profile.
- [x] Given a missing or expired Bearer token, When accessing protected endpoints, Then it returns `401 Unauthorized`.

### Verification of acceptance criteria
- [x] AC1 `POST /auth/token` → 200 with `accessToken`, `tokenType == "bearer"`, `role` (`test_login_success_returns_jwt_token`)
- [x] AC2 invalid password / non-existent email → 401 `AUTH_INVALID_CREDENTIALS` (`test_login_invalid_password_returns_401`, `test_login_nonexistent_email_returns_401`)
- [x] AC3 inactive account → 401 `AUTH_INACTIVE_ACCOUNT` (`test_login_inactive_user_returns_401`)
- [x] AC4 valid Bearer token → 200 `StaffRead` with matching email and role (`test_auth_me_returns_current_user_profile`)
- [x] AC5 missing / invalid / expired Bearer token → 401 (`test_auth_me_missing_token_returns_401`, `test_auth_me_invalid_token_returns_401`, `test_auth_me_expired_token_returns_401`)

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | `test_login_success_returns_jwt_token` | API | status 200, access_token in body, token_type == "bearer" | PRD R-1 |
| 1b | `test_login_nonexistent_email_returns_401` | API | status 401, error == "AUTH_INVALID_CREDENTIALS" | Spec 01 §7 |
| 2 | `test_login_invalid_password_returns_401` | API | status 401, error == "AUTH_INVALID_CREDENTIALS" | Spec 01 §7 |
| 3 | `test_login_inactive_user_returns_401` | API | status 401, error == "AUTH_INACTIVE_ACCOUNT" | Spec 01 §7 |
| 4 | `test_auth_me_returns_current_user_profile` | API + auth header | status 200, email and role match fixture | PRD R-1 |
| 5 | `test_password_hashing_uses_argon2_and_threadpool` | Service unit | Argon2 hash prefix, password verified | NFR-6 |
| 5b | `test_auth_me_missing_token_returns_401` | API | status 401, no Authorization header | Spec 01 §4 AC5 |
| 5c | `test_auth_me_invalid_token_returns_401` | API | status 401, malformed Bearer token | Spec 01 §4 AC5 |
| 5d | `test_auth_me_expired_token_returns_401` | API | status 401, expired JWT (built via pyjwt directly) | Spec 01 §4 AC5 |

## Out of scope
Admin staff management CRUD and RBAC endpoint guards (handled in T-003).

## Notes for the implementer
Offload Argon2 hashing/verification to `loop.run_in_executor(None, ...)` to ensure the async event loop is never blocked by CPU-intensive cryptography.

## Implementation log

### What was built
Staff authentication and token issuance for the FastAPI backend (`src/app/`).
- `backend/src/app/models/base.py` (new): `Base(AsyncAttrs, DeclarativeBase)`, `UUIDMixin` (UUID pk via `uuid4`), `TimestampMixin` (created_at/updated_at with `utcnow`). Replaces the local `Base` that was defined in `db/session.py`.
- `backend/src/app/models/staff.py` (new): `Staff` ORM model inheriting `UUIDMixin` + `TimestampMixin` — `email` (unique, indexed), `hashed_password`, `full_name`, `role` (indexed), `is_active`, `created_at`/`updated_at`.
- `backend/src/app/schemas.py` (new): shared constrained types (`StaffRole`, `EmailStr`, `PasswordStr`, `NonEmptyStr`) plus auth schemas (`TokenRequest` with `username`/`password`, `TokenResponse` with camelCase aliases, `StaffRead` with camelCase aliases). `populate_by_name=True` on output models per Standard §3.
- `backend/src/app/db/repository.py` (updated): added `get_staff_by_id` and `get_staff_by_email` async queries per Spec 01 §3 Layer 2.
- `backend/src/app/db/session.py` (updated): `Base` now imported from `app.models.base` instead of defined locally; `init_db` unchanged.
- `backend/src/app/services/auth_service.py` (new): `AuthService` with `hash_password`/`verify_password` (Argon2id via `PasswordHasher`, offloaded to `run_in_executor` per NFR-6 / Spec 01 §5); `create_token`/`decode_token` (HS256 JWT per Architecture §4). `AuthError` base + `InvalidCredentialsError` / `InactiveAccountError` domain exceptions (Spec 01 §7). `TokenPayload` dataclass for decoded claims.
- `backend/src/app/api/auth.py` (new): `CurrentUser` frozen dataclass (id, email, full_name, role, is_active, created_at), `get_current_user` dependency extracting Bearer token via `HTTPBearer`, validating JWT, querying `get_staff_by_id`, enforcing `is_active`. `CurrentUserDep` type alias.
- `backend/src/app/api/deps.py` (updated): added `SettingsDep`, `get_auth_service(session, settings)`, and `AuthServiceDep` per Spec 01 §4 Layer 3. `get_auth_service` passes both session and settings to `AuthService` per the approved spec signature.
- `backend/src/app/routers/auth.py` (new): `POST /api/v1/auth/token` (login → `TokenResponse`) and `GET /api/v1/auth/me` (→ `StaffRead`). Handlers are thin — delegate to `AuthService` and repository.
- `backend/src/app/main.py` (updated): mounted `auth_router`; registered `AuthError` exception handler (standardized error body with `error`/`message`/`correlation_id`); added structured exception logging to the 500 handler per T-001 review finding (missing structured logging).

### Files touched
- New: `src/app/models/base.py`, `src/app/models/__init__.py`, `src/app/models/staff.py`, `src/app/schemas.py`, `src/app/services/__init__.py`, `src/app/services/auth_service.py`, `src/app/api/auth.py`, `src/app/routers/__init__.py`, `src/app/routers/auth.py`
- Modified: `src/app/db/session.py`, `src/app/db/repository.py`, `src/app/api/deps.py`, `src/app/main.py`, `tests/conftest.py`, `tests/api/test_auth.py`, `tests/api/test_errors.py`
- Deleted: `src/backend/__init__.py` (leftover stub from T-001 scaffold, flagged in T-001 review)
- New tests: `tests/unit/test_auth_service.py`, `tests/api/test_auth.py`

### Changes-requested fixes (review round 1)
Review T-002-round-1: 0B 1M 2m 3n. Addressed the major and both minors; nits left as-is per review guidance.
- **Major — AC5 missing test**: Added 3 tests to `tests/api/test_auth.py` covering the missing/expired/invalid Bearer-token → 401 paths on `GET /api/v1/auth/me`:
  - `test_auth_me_missing_token_returns_401` — no `Authorization` header → `HTTPBearer(auto_error=True)` auto-raises 401.
  - `test_auth_me_invalid_token_returns_401` — malformed JWT (`"Bearer not.a.valid.jwt"`) → `PyJWTError` catch in `get_current_user` → 401.
  - `test_auth_me_expired_token_returns_401` — expired token built directly via `pyjwt.encode` with past `iat`/`exp` (not via `AuthService.create_token`, so expected value 401 comes from the spec). → `ExpiredSignatureError` (subclass of `PyJWTError`) → 401.
- **Minor — AC2 incomplete branch**: Added `test_login_nonexistent_email_returns_401` covering the `staff is None` branch at `routers/auth.py:32–33` (non-existent email → 401 `AUTH_INVALID_CREDENTIALS`).
- **Minor — 500 handler `str(exc)` leak**: Removed `"message": str(exc)` from the `internal_server_error_handler` response body in `main.py`, matching the sanitized template in `concurrency-and-ops.md` §Global Middleware. Updated `test_errors.py` to assert `"message"` is absent from the 500 body.

### Decisions / Notes
- `AuthService.__init__` accepts `session` per Architecture §4 spec signature (`get_auth_service(session: DbSessionDep, settings: SettingsDep)`), but the session is optional (`Optional[AsyncSession] = None`) so `AuthService(Settings())` works as a clean unit test without a DB (test plan row 5).
- `CurrentUser` carries all `StaffRead` fields (not just id/email/role) so the `/me` endpoint can project to `StaffRead` without a redundant DB query. The spec's `CurrentUser(id, email, role)` was treated as a minimal example.
- Argon2 parameters: `time_cost=3, memory_cost=64K, parallelism=4, hash_len=32, salt_len=16` — argon2-cffi defaults, satisfying NFR-6 (RFC-recommended memory-hard KDF).
- Token expiry: 30 minutes (`TOKEN_EXPIRY_MINUTES = 30`), returned as `expires_in` in `TokenResponse`.
- Missing Bearer token: `HTTPBearer(auto_error=True)` raises `HTTPException(401)` — FastAPI default handler returns 401, satisfying AC5.
- JWT decode errors (expired/malformed): caught as `pyjwt.PyJWTError` → `HTTPException(401)` with `from None` to suppress exception chaining.
- Structured logging in the 500 handler (T-001 review minor finding) added: `logger.exception("Unhandled server error", extra={"correlation_id": ...})`.
- 500 handler response body sanitized (T-002 review round-1 minor): `"message": str(exc)` removed; body is now `{"error": "internal_server_error", "correlation_id": ...}` only, matching `concurrency-and-ops.md` §Global Middleware template. The exception text is still logged server-side via `logger.exception`.

### Commands run
`uv run ruff check`, `uv run ruff format --check`, `uv run mypy src`, `uv run pytest -q` — all green (12 tests, 17 source files).

## Review history
- [Review T-002 round 1 — Changes requested](reviews/T-002-review-1.md): 0B/1M/2m/3n. Gates green (ruff/ruff-format/mypy/pytest, 8 passed). Behavior correct & in-scope; AC5 missing test (major), 500 `str(exc)` leak + AC2 incomplete branch (minor), weak test assertions (nit).
- Fixes applied: major (AC5) + both minors addressed; 3 nits left as-is per review guidance. Ready for round 2.
- [Review T-002 round 2 — Approve](reviews/T-002-review-2.md): 0B/0M/2m/4n. Gates green (ruff/ruff-format/mypy/pytest, 12 passed). AC5 added (major resolved); AC2 nonexistent-email test + 500 handler sanitized (minors resolved). 2 minors remain: AC4 test assertions not strengthened (claimed addressed but not fixed); bare HTTPException(401) in get_current_user produces non-standardized error body. 4 nits left as-is.
