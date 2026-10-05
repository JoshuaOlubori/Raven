# Review T-002 round 1 — Changes requested

Gates: ruff ✓ · ruff format ✓ · mypy ✓ · pytest ✓ (8 passed)

## Spec

Spec sources verified against: `work/specs/01-auth-staff.md` (§2–§7) and `work/specs/00-architecture.md` (§4 HS256 JWT, §6 statelessness, §8 error model), PRD `R-1` / `NFR-6` (CONTEXT.md glossary).

| AC | Spec requirement (quoted) | Code | Test | Verdict |
|---|---|---|---|---|
| AC1 | *"Given valid active staff credentials, When `POST /api/v1/auth/token` is submitted, Then it returns `200 OK` with a valid Bearer JWT token, expiration, and user role (R-1)."* | `routers/auth.py:24-49` — `login` fetches staff by email, verifies Argon2 password, enforces `is_active`, issues HS256 JWT via `AuthService.create_token`; `schemas.py:42-48` `TokenResponse` with `access_token`/`expires_in`/`role`. | `test_auth.py:17-33` — asserts 200, `accessToken` present, `tokenType=="bearer"`, `role=="DENTIST"`. | ⚠️ **Behavior met, test weak** — does not assert `expiresIn` (spec verification row lists it) nor validate the token is a well-formed JWT. |
| AC2 | *"Given an invalid password or non-existent email, When `POST /api/v1/auth/token` is submitted, Then it returns `401 Unauthorized` with error code `AUTH_INVALID_CREDENTIALS`."* | `routers/auth.py:31-36` — `staff is None → InvalidCredentialsError`; wrong password → `InvalidCredentialsError`. Mapped by `main.py:53-65` (`AuthError` handler). | `test_auth.py:36-50` — only the wrong-password branch. **No test for non-existent email** (`staff is None` branch at `routers/auth.py:32-33`). | ⚠️ **Incomplete coverage** — spec names two cases; one branch untested. |
| AC3 | *"Given an inactive staff account (`is_active = False`), When login is attempted, Then it returns `401 Unauthorized` with error code `AUTH_INACTIVE_ACCOUNT`."* | `routers/auth.py:38-39` — `InactiveAccountError`; error code `AUTH_INACTIVE_ACCOUNT` per `services/auth_service.py:60-61`. | `test_auth.py:53-67` — asserts 401 + `error == "AUTH_INACTIVE_ACCOUNT"`. | ✅ |
| AC4 | *"Given a valid Bearer token, When `GET /api/v1/auth/me` is requested, Then it returns `200 OK` with the authenticated staff member's profile."* | `routers/auth.py:52-64` — `read_current_user` returns `StaffRead`; guarded by `CurrentUserDep` → `get_current_user` (`api/auth.py:40-69`). | `test_auth.py:70-84` — asserts 200, `email` and `role` match. | ⚠️ **Partial assertion** — "profile" implies full `StaffRead`; only `email`+`role` asserted. |
| AC5 | *"Given a missing or expired Bearer token, When accessing protected endpoints, Then it returns `401 Unauthorized`."* | `api/auth.py:25` (`HTTPBearer()` → `auto_error=True` raises 401 on missing token); `api/auth.py:50-56` (`PyJWTError` catch → 401 on invalid/expired). | **None.** The ticket's verification note claims AC5 is "covered by PyJWTError catch; no dedicated test per test plan row 5 scope" — but test-plan row 5 is `test_password_hashing_uses_argon2_and_threadpool` (Argon2/T threadpool), which is unrelated to AC5. AC5 has zero test coverage. | ❌ **Major gap** — entire acceptance criterion untested. |

**Scope:** No scope creep. `require_roles` (RBAC guards) and staff CRUD endpoints (`POST/GET/PATCH /staff`) are correctly deferred to T-003; `list_staff`/`create_staff`/`update_staff` repositories (Spec 01 §3) are also T-003. `StaffCreate`/`StaffUpdate` schemas (Spec 01 §2) are correctly omitted. T-002 implements exactly `POST /auth/token` + `GET /auth/me`. The deletion of the `src/backend/__init__.py` stub (flagged in T-001) is addressed. ✅

## Standards

- **minor**: 500 handler leaks `str(exc)`. `concurrency-and-ops.md:60-96` requires the unhandled-error path to "return a **sanitized** 500 JSON response" and the template (`concurrency-and-ops.md:84-88`) returns only `{"error": "internal_server_error", "correlation_id": ...}` with no `message` field. `main.py:68-91` instead returns `"message": str(exc)` (`main.py:89`), which can disclose internal exception text/SQL/fragment paths to clients. Pre-existing from T-001 (reviewed there only as a cosmetic field-ordering nit), but the function is in this diff and the deviation from "sanitized" is now explicit. **Fix**: drop `message` or replace `str(exc)` with a generic constant like `"An internal error occurred"`.
- **nit**: `AuthService.__init__` parameter order differs from the dependency signature. Spec (Architecture §4 / Spec 01 §4) defines `get_auth_service(session, settings)`, but `AuthService.__init__(self, settings, session=None)` (`services/auth_service.py:60-64`) takes `settings` first. `get_auth_service` (`deps.py:132-137`) calls `AuthService(session=session, settings=settings)` by keyword so it works, and the `Optional` session is documented for clean unit testing — but the mismatch is a readability hazard. **Suggestion**: align the constructor to `(self, session, settings)` or document the intentional reorder. Low priority.
- (T-001 carryover, now **fixed** ✓): structured exception logging added to the 500 handler (`main.py:79-82` calls `logger.exception(...)` with `correlation_id`). ✅
- All other Layer-1/3/4/5 checklist smells are clean: handlers consume `*Dep` aliases (no inline service construction, no own session — `routers/auth.py:25-29`); no v1 idioms (`parse_obj`/`dict` absent — grep confirmed); Argon2 hashing offloaded via `run_in_executor` (`services/auth_service.py:88-96`); no module-level mutable state (`TOKEN_EXPIRY_MINUTES` is an `int` constant; `security = HTTPBearer()` is stateless); no eager-loading/N+1 concerns (single-PK fetch `repository.py:32`); no 401/403 confusions (login failures are 401/authn per Spec 01 §7; RBAC 403 is T-003). ✅
- Naming conforms to Standard §2: `*Dep` aliases (`CurrentUserDep`, `DbSessionDep`, `AuthServiceDep`), `get_` factory functions, `PascalCase …Service` class, `verb_noun` repository functions, camelCase JSON aliases — all consistent. ✅

## Tests

- **major**: AC5 has no test. Missing-Bearer-token and invalid/expired-token → 401 paths of the protected `/me` endpoint are entirely unverified. The ticket deferred this with a rationale that cites the wrong test-plan row. Recommended additions: a `GET /api/v1/auth/me` with no `Authorization` header → 401; a request with an expired/invalid token → 401. These verify the `HTTPBearer` + `PyJWTError` wiring end-to-end (not just the code's existence).
- **minor**: AC2 incomplete — `test_login_invalid_password_returns_401` (`test_auth.py:36-50`) exercises only the wrong-password branch. The `staff is None` branch (`routers/auth.py:32-33`, non-existent email → same 401/error code) is untested. Add `test_login_nonexistent_email_returns_401`.
- **minor**: AC4 assertion is partial. `test_auth_me_returns_current_user_profile` (`test_auth.py:70-84`) asserts only `email` + `role`; should also assert `id`, `fullName`, `isActive`, `createdAt` to fully cover "the authenticated staff member's profile" (a refactor that dropped a field would pass unnoticed).
- **nit**: AC1 test is weak. `test_login_success_returns_jwt_token` (`test_auth.py:17-33`) only checks `"accessToken" in body` — does not assert `expiresIn` (spec verification row lists it) nor that the token decodes as a JWT with an `exp` claim.
- **nit**: No 422 test for malformed login input. Spec 01 §4 lists 422 for `POST /auth/token`; a short password or bad email would raise Pydantic 422. Framework-provided, not in the test plan — low value, but the spec lists it.
- **nit**: Test name overstates coverage. `test_password_hashing_uses_argon2_and_threadpool` (`test_auth_service.py:16-28`) asserts the Argon2 hash prefix (`$argon2`) and verify results (both independent of implementation ✅) but does **not** verify `run_in_executor` offload — confirming that would require mocking the event loop. The "threadpool" in the name is unverifiable here without a mock.
- Positive: expected values are genuinely independent — `"bearer"`, `"AUTH_INVALID_CREDENTIALS"`, `"AUTH_INACTIVE_ACCOUNT"` all come from Spec 01 §7; role `"DENTIST"` and email come from the persisted fixture (not recomputed by the code under test); Argon2 `$argon2` prefix comes from NFR-6. ✅ No tautological assertions.
- Positive: no shared-mutable-fixture hazards — staff fixtures use `uuid`-based unique emails (`conftest.py` `test_staff`/`inactive_test_staff`), `auth_headers` is a factory, no sleeps, no cross-test ordering assumptions. ✅ Behavior is asserted at the HTTP seam, surviving refactors that preserve the contract. ✅

## Summary

| Severity | Count |
|---|---|
| blocker | 0 |
| major | 1 (AC5 missing test) |
| minor | 2 (AC2 incomplete branch; 500 `str(exc)` leak) |
| nit | 3 (AC1 weak assertions; no 422 test; threadpool-test name overstates) |

**Single worst issue:** **AC5 has zero test coverage** (`api/auth.py:50-60` — missing/expired/invalid Bearer token → 401). This is the security-critical path of the entire ticket (auth gating on `/me`), yet only the happy path is exercised. The ticket's deferral rationale is flawed (it cites test-plan row 5, which is the Argon2 test, not an AC5 test). The gates are green and behavior is correct, but spec-driven discipline requires a test for every acceptance criterion — and T-001 was approved on exactly that bar ("every acceptance criterion has a test"). Requesting the AC5 test (missing token + invalid/expired token → 401) before this can land.

The minors are optional but recommended before merge; the nits are leave-as-is.
