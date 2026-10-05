# Review T-002 round 2 — Approve

Gates: ruff ✓ · ruff format ✓ · mypy ✓ · pytest ✓ (12 passed)

## Spec

Spec sources verified against: `work/specs/01-auth-staff.md` (§2–§7), `work/specs/00-architecture.md` (§4 HS256 JWT, §6 statelessness, §8 error model), PRD `R-1` / `NFR-6` (CONTEXT.md glossary).

| AC | Spec requirement (quoted) | Code | Test | Verdict |
|---|---|---|---|---|
| AC1 | *"Given valid active staff credentials, When `POST /api/v1/auth/token` is submitted, Then it returns `200 OK` with a valid Bearer JWT token, expiration, and user role (R-1)."* | `routers/auth.py:22-49` — `login` fetches by email (`get_staff_by_email`), verifies Argon2 via `auth_service.verify_password`, enforces `is_active`, issues HS256 JWT via `auth_service.create_token`; `schemas.py:TokenResponse` with `access_token`/`expires_in`/`role` + camelCase aliases | `test_auth.py:test_login_success_returns_jwt_token` — asserts 200, `accessToken` present, `tokenType == "bearer"`, `role == "DENTIST"` | ✅ Behavior met. **Nit** (left as-is): does not assert `expiresIn` value (spec verification row lists it) nor validate the token is a well-formed JWT with an `exp` claim. |
| AC2 | *"Given an invalid password or non-existent email, When `POST /api/v1/auth/token` is submitted, Then it returns `401 Unauthorized` with error code `AUTH_INVALID_CREDENTIALS`."* | `routers/auth.py:31-33` — `staff is None → InvalidCredentialsError`; `routers/auth.py:36` — wrong password → `InvalidCredentialsError`. Mapped by `main.py:53-65` (`AuthError` handler) | `test_login_invalid_password_returns_401` + `test_login_nonexistent_email_returns_401` — both assert 401 + `body["error"] == "AUTH_INVALID_CREDENTIALS"` | ✅ Both branches now covered. Round-1 **minor** resolved. |
| AC3 | *"Given an inactive staff account (`is_active = False`), When login is attempted, Then it returns `401 Unauthorized` with error code `AUTH_INACTIVE_ACCOUNT`."* | `routers/auth.py:38-39` — `InactiveAccountError`; error code per `services/auth_service.py:53-64` | `test_auth.py:test_login_inactive_user_returns_401` — asserts 401 + `body["error"] == "AUTH_INACTIVE_ACCOUNT"` | ✅ |
| AC4 | *"Given a valid Bearer token, When `GET /api/v1/auth/me` is requested, Then it returns `200 OK` with the authenticated staff member's profile."* | `routers/auth.py:52-64` — `read_current_user` returns `StaffRead` via `CurrentUserDep → get_current_user` (`api/auth.py:46-75`) | `test_auth.py:test_auth_me_returns_current_user_profile` — asserts 200, `body["email"]`, `body["role"]` | ⚠️ **Major gap resolved** (round-1 had zero `/me` test). **Minor not addressed**: test asserts only `email` + `role`; round-1 review asked to also assert `id`, `fullName`, `isActive`, `createdAt` to fully cover "the authenticated staff member's profile." The implementer's log claims to have addressed "both minors" but AC4 does not appear in the round-1 summary count (which listed AC2 + 500-handler leak only) and was never fixed — the test still asserts just `email` and `role` (`test_auth.py:84-87`). |
| AC5 | *"Given a missing or expired Bearer token, When accessing protected endpoints, Then it returns `401 Unauthorized`."* | `api/auth.py:31` (`HTTPBearer()` defaults to `auto_error=True` → 401 on missing token); `api/auth.py:56-62` (`PyJWTError` catch → 401 on invalid/expired); `api/auth.py:65-66` (staff not found/inactive → 401) | `test_auth_me_missing_token_returns_401` (no `Authorization` header → 401); `test_auth_me_invalid_token_returns_401` (malformed JWT `"Bearer not.a.valid.jwt"` → 401); `test_auth_me_expired_token_returns_401` (expired token built directly via `pyjwt.encode` with past `iat`/`exp` — expected 401 from spec, not from `AuthService.create_token`) | ✅ All three paths now covered. Round-1 **major** resolved. |

**Scope:** No scope creep. `require_roles`, staff CRUD endpoints (`POST/GET/PATCH /staff`), `StaffCreate`/`StaffUpdate` schemas, `list_staff`/`create_staff`/`update_staff` repositories all correctly deferred to T-003 (Spec 01 §3/§4). `src/backend/__init__.py` orphan stub deleted (T-001 flag). The `SrcBackend` deletion is the only file removal outside the auth module. ✅

## Standards

- ✅ 500 handler sanitized — `"message": str(exc)` removed from `internal_server_error_handler` (`main.py:87-93`); body is now `{"error": "internal_server_error", "correlation_id": ...}` only, matching `concurrency-and-ops.md §Global Middleware` template. `test_errors.py` updated to assert `"message" not in body`. (Round-1 **minor** — resolved.)
- ✅ Structured exception logging added — `logger.exception("Unhandled server error", extra={"correlation_id": correlation_id})` in the 500 handler (`main.py:83-86`). (T-001 carryover — resolved.)
- ✅ `AuthError` exception handler registered — maps `InvalidCredentialsError`/`InactiveAccountError` to standardized error body with `error`/`message`/`correlation_id` (`main.py:53-65`).
- ✅ Handlers consume `*Dep` aliases — no inline service construction, no own session (`routers/auth.py:24-29`). Layer 3 compliant.
- ✅ Argon2 hashing/verification offloaded via `run_in_executor` (`services/auth_service.py:113-114, 119-120`). Layer 4 compliant. (NFR-6 / Spec 01 §5.)
- ✅ No module-level mutable state — `TOKEN_EXPIRY_MINUTES` is an `int` constant; `security = HTTPBearer()` and `logger` are stateless. Layer 5 compliant. (Spec 01 §6.)
- ✅ No v1 idioms — `parse_obj`/`dict()` absent; `model_validate` used throughout (`routers/auth.py:42, 54`).
- ✅ No N+1 / eager-loading concerns — `get_staff_by_id` uses single-PK `session.get`; no relationship traversal needed.
- ✅ No 401/403 confusion — login failures are 401/authn per Spec 01 §7; RBAC 403 is T-003.
- ✅ Naming conforms to Standard §2: `*Dep` aliases (`CurrentUserDep`, `DbSessionDep`, `AuthServiceDep`), `get_` factory functions, `PascalCase …Service` class, `verb_noun` repository functions, camelCase JSON aliases — all consistent.
- ⚠️ **minor**: `get_current_user` raises bare `HTTPException(401)` for the "valid token but staff not found/inactive" case (`api/auth.py:65-66`) instead of an `AuthError` subclass. This produces a non-standardized body (`{"detail": "Invalid or expired token"}`) lacking `correlation_id`, inconsistent with Architecture §4's error model (`concurrency-and-ops.md` §Global Middleware: "standardized RFC-compliant error body `{"error": "<code>", "message": "<str>", "correlation_id": "<str>"}`"). The login path correctly raises `InvalidCredentialsError`/`InactiveAccountError` (→ `auth_error_handler` → standardized body), but the `/me` token-verification path does not. The three AC5 tests only assert `status_code == 401` and do not check the body, so this inconsistency is not caught by tests. **Fix direction**: raise `InvalidCredentialsError` (or a dedicated `AuthTokenError`) so `auth_error_handler` formats the body consistently, or add a generic `HTTPException` handler that reformats to the standardized shape. (Edge case — status code is correct; information leakage avoided since the message is generic.)
- **nit** (left as-is): `AuthService.__init__(self, settings, session=None)` parameter order differs from `get_auth_service(session, settings)` factory (`deps.py:132-137`). Works by keyword; readability hazard only. (Round-1 **nit** — as-is.)
- **nit** (new): `expires_in: 1800` in `routers/auth.py:43` is a magic number duplicating `TOKEN_EXPIRY_MINUTES * 60`. If `TOKEN_EXPIRY_MINUTES` changes, the JWT `exp` claim (`services/auth_service.py:134`) and the response's `expires_in` field would diverge. **Fix direction**: compute `expires_in` from `TOKEN_EXPIRY_MINUTES * 60` or return it from `create_token`. (Low priority — currently consistent.)
- **nit** (left as-is): AC1 test (`test_login_success_returns_jwt_token`) doesn't assert `expiresIn` value or JWT structure. (Round-1 **nit** — as-is.)
- **nit** (left as-is): No 422 test for malformed login input. Spec 01 §4 lists 422; Pydantic provides it automatically. (Round-1 **nit** — as-is.)
- **nit** (left as-is): `test_password_hashing_uses_argon2_and_threadpool` asserts Argon2 prefix + verify results but does not verify `run_in_executor` offload (would require mocking the event loop). Name slightly overstates coverage. (Round-1 **nit** — as-is.)

## Tests

- ✅ AC5 (round-1 **major**) resolved: three new tests added — `test_auth_me_missing_token_returns_401` (no `Authorization` header → `HTTPBearer` auto-rejects), `test_auth_me_invalid_token_returns_401` (malformed JWT → `PyJWTError` → 401), `test_auth_me_expired_token_returns_401` (expired token built directly via `pyjwt.encode` — expected 401 from spec, not from `AuthService.create_token`). All assert `response.status_code == 401`.
- ✅ AC2 (round-1 **minor**) resolved: `test_login_nonexistent_email_returns_401` covers the `staff is None` branch (`routers/auth.py:31-32`), testing against an empty test DB via the `override_dbsession` fixture.
- ⚠️ **minor**: AC4 test not strengthened — see Standards section. The implementer's log claims "Addressed the major and both minors" but AC4 was not in the round-1 summary count and was not fixed (`test_auth.py:84-87` still asserts only `email` + `role`).
- ✅ Expected values are independent of implementation: `"bearer"` from spec; `"AUTH_INVALID_CREDENTIALS"`/`"AUTH_INACTIVE_ACCOUNT"` from Spec 01 §7; `"DENTIST"` and `staff.email` from fixture (not recomputed); `$argon2` prefix from NFR-6; expired-token 401 from spec via direct `pyjwt.encode`. No tautological assertions.
- ✅ Test seam matches the spec: all auth tests drive the public HTTP seam (`AsyncClient` over `ASGITransport`, `client` fixture), not private internals. Tests would survive a refactor that preserves the contract.
- ✅ No sleeps, order dependence, or shared-mutable-fixture hazards — staff fixtures use UUID-based unique emails (`conftest.py:152, 174`), `auth_headers` is a factory (`conftest.py:186`), no cross-test ordering assumptions.
- ✅ Failure paths covered: 401 across all auth-failure branches (invalid password, nonexistent email, inactive account, missing/invalid/expired token). 422 not tested — nit (as-is).

## Summary

| Severity | Count |
|---|---|
| blocker | 0 |
| major | 0 |
| minor | 2 (AC4 test not strengthened; bare `HTTPException(401)` in `get_current_user` produces non-standardized error body) |
| nit | 4 (auth_service param order; AC1 weak assertions; no 422 test; threadpool-test name overstates; `expires_in` magic number — all left as-is or low priority) |

Gates: ruff ✓ · ruff format ✓ · mypy ✓ · pytest ✓ (12 passed)

**Single worst issue:** The round-1 **major** (AC5 missing test) is resolved. The most notable outstanding item is the **minor** that the implementer claimed to address but didn't: AC4's test (`test_auth_me_returns_current_user_profile`) still only asserts `email` + `role` despite round-1 asking to also cover `id`, `fullName`, `isActive`, `createdAt`. While this is optional per SDD policy, the discrepancy between the implementation log ("Addressed … both minors") and the actual code warrants a note to the implementer.

**Verdict: Approve.** All gates green; 0 blockers, 0 majors. The round-1 changes-requested items in the summary table (AC5 major, AC2 minor, 500-handler minor) are all resolved. Two minors remain (AC4 not strengthened; inconsistent error body for staff-not-found on `/me`); both are optional.
