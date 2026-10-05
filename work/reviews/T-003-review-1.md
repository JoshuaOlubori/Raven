# Review T-003 round 1 — Changes requested

Gates: ruff ✓ · ruff format ✓ · mypy ✓ · pytest ✓ (17 passed)

Spec sources verified against: `work/specs/01-auth-staff.md` (§2 Contracts, §3 Persistence/Repository Signatures, §4 Wiring/Endpoints, §7 Errors), `work/specs/00-architecture.md` (§4 Global Error Model, §5 AuthN/AuthZ, §8 error body shape), PRD `R-2` / `NFR-6` (CONTEXT.md glossary). Standards source: `fastapi-production-architecture` skill (§2 Naming, §3/§4/§5/§6/§8 checklists) + Fowler baseline.

## Spec

| AC | Spec requirement (quoted) | Code | Test | Verdict |
|---|---|---|---|---|
| AC1 | *"Given an Admin user, When `POST /api/v1/staff` is submitted with valid data, Then a new staff account is created with `201 Created` and password hash excluded from response (R-2)."* | `routers/staff.py:31-55` — `POST /` with `status_code=201`, `response_model=StaffRead`, `dependencies=[Depends(require_roles("ADMIN"))]`; `_staff_read` (staff.py:58-69) projects to `StaffRead` dict that omits `hashed_password`; PRD R-2 acceptance: "Given a user authenticated with role ADMIN, When creating a new staff account, Then the system returns 201 Created." | `test_staff.py:17-39` — asserts 201, `body["role"] == "DENTIST"`, `"hashed_password" not in body`. | ✅ Behavior met. |
| AC2 | *"Given a non-Admin user (`RECEPTIONIST` or `DENTIST`), When attempting `POST /api/v1/staff`, Then the system rejects the request with `403 Forbidden`."* | `api/auth.py:83-101` — `require_roles("ADMIN")` closure guard: `if current_user.role not in roles: raise ForbiddenError()` (403, `RBAC_FORBIDDEN`); applied via `dependencies=[Depends(require_roles("ADMIN"))]` on the POST route (staff.py:35). | `test_staff.py:42-64` — tests **RECEPTIONIST** → 403, asserts `body["error"] == "RBAC_FORBIDDEN"`, `"Insufficient role" in body["message"]`. | ⚠️ **minor**: DENTIST sub-case untested. The AC explicitly names "RECEPTIONIST **or** DENTIST"; the test only covers RECEPTIONIST. The guard logic (`role not in ("ADMIN",)`) is correct for both, but the acceptance criterion is not fully exercised. **Fix**: add `test_dentist_creating_staff_returns_403`. |
| AC3 | *"Given an attempt to register an email already in use, When `POST /api/v1/staff` is submitted, Then it returns `409 Conflict` with error code `STAFF_EMAIL_EXISTS`."* | `routers/staff.py:43-45` — `get_staff_by_email` pre-check → `EmailAlreadyExistsError()` (409, `STAFF_EMAIL_EXISTS`); Spec 01 §7: `EmailAlreadyExistsError → 409, STAFF_EMAIL_EXISTS`. | `test_staff.py:67-103` — first POST → 201, second POST same email → 409, `body["error"] == "STAFF_EMAIL_EXISTS"`. | ✅ Behavior met. |
| AC4 | *"Given an Admin or Receptionist, When querying `GET /api/v1/staff?role=DENTIST`, Then all matching staff accounts are returned."* | `routers/staff.py:72-83` — `GET /` with `dependencies=[Depends(require_roles("ADMIN", "RECEPTIONIST"))]`, `role: Annotated[StaffRole | None, Query()] = None`, delegates to `list_staff(session, role=role, active_only=True)` (repository.py:49-61). | `test_staff.py:106-126` — RECEPTIONIST auth, `params={"role": "DENTIST"}`, asserts 200 + all returned items `role == "DENTIST"`. | ✅ Behavior met. (See Tests-axis note on weak assertion.) |
| AC5 | *"Given an Admin, When `PATCH /api/v1/staff/{id}` is submitted with `is_active=False`, Then the staff member's active status is updated to false."* | `routers/staff.py:102-118` — `PATCH /{staff_id}` with `dependencies=[Depends(require_roles("ADMIN"))]`, `model_dump(exclude_unset=True)` (staff.py:116), `update_staff` (repository.py:64-75); Spec 01 §4: PATCH → 200. | `test_staff.py:129-147` — PATCH `{"isActive": False}`, asserts 200 + `body["isActive"] is False`. | ✅ Behavior met. |

**Scope:** No scope creep. `require_roles`, `StaffCreate`/`StaffUpdate` schemas, `create_staff`/`list_staff`/`update_staff` repositories, staff CRUD endpoints, and the `DomainError` hierarchy (`exceptions.py`, `AuthError(DomainError)`) are all within T-003 scope (Spec 01 §3 §4). The `AuthError(DomainError)` change in `auth_service.py` and the `DomainError` handler in `main.py` are necessary to unify the error model used by `require_roles`' `ForbiddenError`. ✅

**Silent deviations:** None from spec endpoints, status codes, error codes, or state machine. The ticket's implementer note suggesting `set(allowed) & set(user.roles)` was correctly identified as not applicable — `CurrentUser.role` is a single `StaffRole` string (Spec 01 §4: "raises 403 Forbidden if current_user.role not in roles"), so the membership test `current_user.role not in roles` (auth.py:57) is the correct implementation. ✅

## Standards

All checklist smells from the fastapi-production-architecture standard are clean for this diff:

- ✅ **Layer 3 — Handler opens own session / builds services inline**: handlers consume `*Dep` aliases (`DbSessionDep`, `AuthServiceDep`, `CurrentUserDep` via `require_roles`). No inline service construction, no own session. `routers/staff.py:37-41, 77-80, 91-94, 107-111`.
- ✅ **Layer 3 — Role checks scattered as `if user.role`**: RBAC is centralized in the `require_roles` closure (auth.py:83-101), applied as route-level `dependencies=[...]`. No scattered `if user.role` checks in handlers.
- ✅ **Layer 1 — Business rules in handlers**: Email-uniqueness pre-check delegates to `get_staff_by_email` (repository) and raises a `DomainError` subclass; password hashing delegates to `AuthService`. Field validation (email format, password length, `StaffRole` literal, `NonEmptyStr` strip) is in schema validators. ✅
- ✅ **Layer 1 — v1 idioms**: `model_validate`/`model_dump` used throughout. No `parse_obj()`/`dict()`. ✅
- ✅ **Layer 2 — per-row queries / missing eager loading**: `get_staff_by_id` uses `session.get(Staff, ...)` (single PK lookup); `list_staff` uses simple `select(Staff)`. No relationship traversal, no N+1. ✅
- ✅ **Layer 4 — blocking work on event loop**: `AuthService.hash_password` offloads Argon2 to `run_in_executor` (auth_service.py:112-115, from T-002). Staff endpoint calls `auth_service.hash_password` which is async. ✅
- ✅ **Layer 5 — module-level mutable state**: No mutable state. `router = APIRouter(...)` is immutable after construction. ✅
- ✅ **No 401/403 confusion**: 401 = authentication failure (`get_current_user`); 403 = authorization failure (`require_roles` → `ForbiddenError`). ✅
- ✅ **Naming conforms to §2**: `*Dep` aliases, `get_` factory functions, `verb_noun` repository functions (`create_staff`, `list_staff`, `update_staff`, `get_staff_by_id`, `get_staff_by_email`), camelCase JSON aliases (`isActive`, `fullName`, `createdAt`), `StaffCreate`/`StaffUpdate`/`StaffRead` schema naming — all consistent. ✅
- ✅ **Correlation ID / structured logging**: `correlation_id_middleware` (main.py:42-52) propagates `X-Correlation-ID`; `domain_error_handler` (main.py:55-72) includes it in all error responses; 500 handler logs via `logger.exception(..., extra={"correlation_id": ...})` (main.py:90-93). ✅
- ✅ **Secrets / config inline**: No secrets in code. `AuthService` receives `Settings` via DI. ✅

Fowler smells:

- ⚠️ **minor — Duplicated Code**: "Fetch-or-raise-404" pattern duplicated between `get_staff_endpoint` (staff.py:96-98) and `update_staff_endpoint` (staff.py:113-115):
  ```python
  staff = await get_staff_by_id(session, staff_id)
  if staff is None:
      raise StaffNotFoundError()
  ```
  Both endpoints repeat the same 3-line lookup-and-404 guard. **Fix direction:** extract a private `_get_staff_or_404(session, staff_id) -> Staff` helper (or a dependency) and reuse it. (3-line duplication — low impact but trivially deduplicated.)
- ⚠️ **minor — Pre-existing 401 body inconsistency (T-002 carryover, not fixed by T-003)**: `get_current_user` (auth.py:56-59, 63) raises bare `HTTPException(401, detail="Invalid or expired token")` for missing/malformed/expired tokens and non-existent/inactive staff lookups. This produces a non-standardized body `{"detail": "Invalid or expired token"}` lacking the `error` field and `correlation_id` mandated by Architecture §4 (`00-architecture.md §4: "standardized RFC-compliant error body {"error": "<code>", "message": "<str>", "correlation_id": "<str>"}``). The T-002 round-2 review flagged this as a **minor**; it remains unfixed. The 403 path was correctly upgraded to `ForbiddenError` (standardized ✅), but the 401 path was not. **Fix direction:** raise `InvalidCredentialsError` (or a dedicated `AuthTokenError(DomainError)`) so the `DomainError` handler formats the 401 body consistently.
- ⚠️ **minor — Implementation log inaccuracy**: T-003's implementation log (ticket:60-61) claims: *"This addresses the T-002 review round-2 minor about non-standardized `HTTPException(401)` bodies."* This is incorrect — T-003 only standardized the **403** path (`ForbiddenError`); the **401** `HTTPException` in `get_current_user` is unchanged (auth.py:56-59, 63). The 403 fix addresses the RBAC guard, not the token-verification 401 path. **Fix direction:** correct the implementation log, and fix the 401 path per above.
- **nit**: Stale `AuthError` docstring. `auth_service.py:41-48` says *"main.py registers a single handler for AuthError"* but `main.py:55-56` registers a handler for `DomainError` (the base class). The handler does catch `AuthError` (via inheritance), so behavior is correct, but the docstring is misleading. **Fix direction:** update docstring to say `DomainError`.
- **nit**: Commit hash mismatch. The ticket's implementation log (ticket:74) references commit `318e1ae`, but the current HEAD is `d3da075` (with `85c2300` also existing in history). The actual commit on `master` is `d3da075`. **Fix direction:** update the implementation log's commit hash to `d3da075`.

## Tests

- ⚠️ **major — Missing 404 test for `StaffNotFoundError`.** Spec 01 §4 endpoint table lists `404` for both `GET /api/v1/staff/{staff_id}` and `PATCH /api/v1/staff/{staff_id}`, with error mapping `StaffNotFoundError → 404, STAFF_NOT_FOUND` (Spec 01 §7). The T-003 diff introduces the `StaffNotFoundError` class (exceptions.py:34-39) and the `if staff is None: raise StaffNotFoundError()` guards (staff.py:97-98, 114-115), but no test exercises the "non-existent staff ID" → 404 path. This is a new code path with zero coverage; a regression (e.g., returning 200, wrong error code, or removing the check) would go undetected. **Fix direction:** add `test_get_nonexistent_staff_returns_404` and `test_patch_nonexistent_staff_returns_404`, asserting 404 + `body["error"] == "STAFF_NOT_FOUND"`.
- ⚠️ **minor — AC2 DENTIST sub-case untested** (restated from Spec axis): the acceptance criterion names "RECEPTIONIST **or** DENTIST" but `test_receptionist_creating_staff_returns_403` only tests RECEPTIONIST. A DENTIST attempting `POST /api/v1/staff` should also receive 403. **Fix direction:** add a DENTIST-auth test.
- ⚠️ **minor — No 401 test on staff endpoints.** Spec 01 §4 endpoint table lists `401` for all four staff endpoints. There is no test that an unauthenticated request (no `Authorization` header) to any `/api/v1/staff*` endpoint returns 401. This is a shared dependency (`get_current_user`, tested in T-002 for `/auth/me`) but not verified at the staff-endpoint seam. **Fix direction:** add `test_staff_endpoint_without_auth_returns_401` hitting at least one staff endpoint with no token.
- ⚠️ **minor — Weak assertion in `test_list_staff_filters_by_role`.** The test asserts `for item in body: assert item["role"] == "DENTIST"` but never asserts the list is non-empty. If `list_staff` returned `[]` (e.g., due to a filter bug), the `for` loop body never executes and the test passes vacuously. The `test_staff` DENTIST fixture is in the DB, so the endpoint should return it — but the test doesn't verify that. **Fix direction:** assert `len(body) >= 1` or assert that `test_staff.id` appears in the returned IDs.
- **nit — No 422 test for malformed input.** Spec 01 §4 lists `422` for `POST /api/v1/staff` (invalid `StaffCreate`) and `PATCH /api/v1/staff/{id}` (invalid `StaffUpdate`). Pydantic v2 raises 422 automatically for schema violations; no explicit test exists. **Consistent with T-002 round-2 precedent** ("Pydantic provides it automatically" → nit, left as-is).
- ✅ **Independent expected values — no tautological assertions**: `201`/`200`/`403`/`409` come from Spec 01 §4/§7 and PRD R-2; `RBAC_FORBIDDEN`/`STAFF_EMAIL_EXISTS` come from Spec 01 §7 error-code table; `"Insufficient role"` comes from `ForbiddenError.message` (spec-defined); `"DENTIST"` comes from the request payload the test controls. No assertion recomputes the answer the way the code does. ✅
- ✅ **Tests assert behaviour at the HTTP seam**: all 5 tests drive `AsyncClient` over `ASGITransport` — no private-structure assertions. ✅
- ✅ **No sleeps, order dependence, or shared-mutable fixtures**: fixtures use UUID-based unique emails; each fixture is function-scoped; `auth_headers` is a factory; no cross-test ordering assumptions. ✅

## Summary

| Severity | Count | Findings |
|---|---|---|
| blocker | 0 | — |
| major | 1 | Missing 404 test for `StaffNotFoundError` (staff.py:97-98, 114-115; Spec 01 §4, §7) |
| minor | 3 | AC2 DENTIST untested; no 401 test on staff endpoints; weak list-filter assertion |
| nit | 4 | Pre-existing 401 `HTTPException` body non-standardized + impl-log inaccuracy; stale `AuthError` docstring; duplicated fetch-or-404; commit-hash mismatch in impl log |

**Single worst issue:** The `StaffNotFoundError` 404 path (staff.py:97-98, 114-115) is a **new code path introduced by this ticket** — the class (exceptions.py:34-39) and both `if staff is None: raise StaffNotFoundError()` guards are T-003 additions — yet it has **zero test coverage**. Spec 01 §4 explicitly lists `404` for both `GET /{staff_id}` and `PATCH /{staff_id}`, and Spec 01 §7 defines the `STAFF_NOT_FOUND` error code. Without a test, a regression (returning 200, wrong error code, or silently succeeding) would be invisible. This is the same class of gap that T-002 round-1 was blocked on (AC5, missing 401 test), and the same bar the PRD §4.3 requires: "Failure paths exist: 401/403/404/409/422 where the spec lists them."

Gates are green and the 5 acceptance criteria all have tests. The single major is a missing failure-path test for a spec-listed error code on new code. Requesting the 404 tests (plus the 401-on-staff-endpoints test) before this can land. Minors are optional but recommended; nits are leave-as-is.

**Verdict: Changes requested** (1 major). The implementer should add 404 tests for `GET /{staff_id}` and `PATCH /{staff_id}` with a non-existent ID; the minor/optional items await the implementer's discretion.
