# Review T-003 round 2 — Approve

Gates: ruff ✓ · ruff format ✓ · mypy ✓ · pytest ✓ (22 passed)

Spec sources verified against: `work/specs/01-auth-staff.md` (§2 Contracts, §3 Persistence/Repository Signatures, §4 Wiring/Endpoints, §7 Errors), `work/specs/00-architecture.md` (§4 Global Error Model, §5 AuthN/AuthZ, §8 error body shape), PRD `R-2` / `NFR-6` (CONTEXT.md glossary). Standards source: `fastapi-production-architecture` skill (§2 Naming, §3/§4/§5/§6/§8 checklists) + Fowler baseline.

## Round-1 finding reconciliation

All round-1 findings were addressed by the implementer in commit `c6e7dbe` (tests only — zero implementation-code changes):

| Round-1 finding | Severity | Fix direction (R1) | Status (R2) |
|---|---|---|---|
| Missing 404 tests for `StaffNotFoundError` | **major** | Add `test_get_nonexistent_staff_returns_404` + `test_patch_nonexistent_staff_returns_404` asserting 404 + `STAFF_NOT_FOUND` | ✅ Addressed — both tests added (test_staff.py:132–148, 151–168) |
| AC2 DENTIST sub-case untested | **minor** | Add DENTIST-auth 403 test | ✅ Addressed — `test_dentist_creating_staff_returns_403` added (test_staff.py:192–215) |
| No 401 test on staff endpoints | **minor** | Add unauthenticated 401 test | ✅ Addressed — two tests added (GET + PATCH, test_staff.py:218–236) |
| Weak list-filter assertion | **minor** | Assert `len(body) >= 1` + fixture ID present | ✅ Addressed (test_staff.py:124–129) |
| Commit hash mismatch in impl log | **nit** | Update to `d3da075` | ✅ Fixed |
| Implementation log inaccuracy | **nit** | Correct false claim about 401 fix | ✅ Fixed — impl log now correctly notes 401 path left as-is |
| Duplicated fetch-or-404 | **nit** | Extract `_get_staff_or_404` helper | ❌ Not addressed (optional nit; 3-line duplication) |
| Stale `AuthError` docstring | **nit** | Update docstring to `DomainError` | ❌ Not addressed (optional nit) |
| Non-standardized 401 body | **nit** (T-002 carryover) | Raise `InvalidCredentialsError` instead of bare `HTTPException` | ❌ Not addressed (T-002 carryover, explicitly out-of-scope per impl log) |

The changes-requested diff was purely additive to the test file — no implementation code was modified (confirmed via `git diff c6e7dbe~1..c6e7dbe -- backend/` showing changes only in `test_staff.py`). The round-1 major and minors were design gaps, not implementation bugs; the `StaffNotFoundError` guards and `require_roles` RBAC guards already existed and were correct.

## Spec

| AC | Spec requirement (quoted) | Code | Test | Verdict |
|---|---|---|---|---|
| AC1 | *"Given an Admin user, When `POST /api/v1/staff` is submitted with valid data, Then a new staff account is created with `201 Created` and password hash excluded from response (R-2)."* | `routers/staff.py:31-55` — POST with `status_code=201`, `response_model=StaffRead`, `dependencies=[Depends(require_roles("ADMIN"))]`; `_staff_read` (staff.py:58-69) omits `hashed_password`. | `test_admin_creates_staff_success_201` (test_staff.py:17-39) — asserts 201, `body["role"] == "DENTIST"`, `"hashed_password" not in body`. | ✅ Met. |
| AC2 | *"Given a non-Admin user (`RECEPTIONIST` or `DENTIST`), When attempting `POST /api/v1/staff`, Then the system rejects the request with `403 Forbidden`."* | `api/auth.py:83-101` — `require_roles("ADMIN")` closure guard raises `ForbiddenError` (403, `RBAC_FORBIDDEN`); applied via `dependencies=[Depends(require_roles("ADMIN"))]` on POST route (staff.py:35). | `test_receptionist_creating_staff_returns_403` (test_staff.py:42-64) + `test_dentist_creating_staff_returns_403` (test_staff.py:192-215) — both assert 403, `body["error"] == "RBAC_FORBIDDEN"`, `"Insufficient role" in body["message"]`. | ✅ Met — both sub-cases now covered. |
| AC3 | *"Given an attempt to register an email already in use, When `POST /api/v1/staff` is submitted, Then it returns `409 Conflict` with error code `STAFF_EMAIL_EXISTS`."* | `routers/staff.py:43-45` — `get_staff_by_email` pre-check → `EmailAlreadyExistsError()` (409, `STAFF_EMAIL_EXISTS`). Spec 01 §7 error table. | `test_create_duplicate_email_returns_409` (test_staff.py:67-103) — first POST → 201, second → 409, `body["error"] == "STAFF_EMAIL_EXISTS"`. | ✅ Met. |
| AC4 | *"Given an Admin or Receptionist, When querying `GET /api/v1/staff?role=DENTIST`, Then all matching staff accounts are returned."* | `routers/staff.py:72-83` — GET with `dependencies=[Depends(require_roles("ADMIN", "RECEPTIONIST"))]`, `role: Annotated[StaffRole \| None, Query()]`, delegates to `list_staff(session, role=role, active_only=True)` (repository.py:49-61). | `test_list_staff_filters_by_role` (test_staff.py:106-129) — RECEPTIONIST auth, `params={"role": "DENTIST"}`, asserts 200, `len(body) >= 1`, DENTIST fixture ID in results, all items `role == "DENTIST"`. | ✅ Met — assertion hardened (no vacuous pass). |
| AC5 | *"Given an Admin, When `PATCH /api/v1/staff/{id}` is submitted with `is_active=False`, Then the staff member's active status is updated to false."* | `routers/staff.py:102-118` — PATCH with `dependencies=[Depends(require_roles("ADMIN"))]`, `model_dump(exclude_unset=True)` (staff.py:116), `update_staff` (repository.py:64-75). | `test_admin_deactivates_staff_member` (test_staff.py:171-189) — PATCH `{"isActive": False}`, asserts 200 + `body["isActive"] is False`. | ✅ Met. |

**Scope:** No scope creep. All new code (`require_roles`, `StaffCreate`/`StaffUpdate`/`StaffRead` schemas, `create_staff`/`list_staff`/`update_staff` repositories, staff CRUD endpoints, `DomainError` hierarchy) is within T-003 scope per Spec 01 §3/§4. The `AuthError(DomainError)` change and `DomainError` handler replacement in `main.py` are necessary to unify the error model used by `require_roles`' `ForbiddenError`. ✅

**Silent deviations:** None from spec endpoints, status codes, error codes, or state machine.

**Spec §4 endpoint table coverage:**

| Endpoint | 200 | 401 | 403 | 404 | 409 | 422 |
|---|---|---|---|---|---|---|
| POST /api/v1/staff | test 1 ✓ | test 9* ✓ | test 2,8 ✓ | — | test 3 ✓ | nit |
| GET /api/v1/staff | test 4 ✓ | test 9* ✓ | (RECEPTIONIST tested) ✓ | — | — | — |
| GET /api/v1/staff/{id} | ⚠️ untested | (inherited) ✓ | (inherited) ✓ | test 5 ✓ | — | — |
| PATCH /api/v1/staff/{id} | test 7 ✓ | test 10* ✓ | — | test 6 ✓ | — | nit |

\* 401 path is shared via `get_current_user` (HTTPBearer auto-rejection); tested at the staff-endpoint seam.

## Standards

All fastapi-production-architecture checklist smells are clean for this diff (same code as round 1 — no implementation changes):

- ✅ **Layer 3 — Handler opens own session / builds services inline**: handlers consume `*Dep` aliases (`DbSessionDep`, `AuthServiceDep`, `CurrentUserDep` via `require_roles`). No inline service construction. `routers/staff.py:37-41, 77-80, 91-94, 107-111`.
- ✅ **Layer 3 — Role checks scattered as `if user.role`**: RBAC centralized in `require_roles` closure (auth.py:83-101), applied as route-level `dependencies=[...]`. No scattered checks in handlers.
- ✅ **Layer 1 — Business rules in handlers**: Email-uniqueness pre-check delegates to `get_staff_by_email` (repository); password hashing delegates to `AuthService`; field validation in schema validators (`EmailStr`, `PasswordStr`, `NonEmptyStr`, `StaffRole` literal).
- ✅ **Layer 1 — v1 idioms**: `model_validate`/`model_dump` throughout. No `parse_obj()`/`dict()`.
- ✅ **Layer 2 — per-row queries / missing eager loading**: `get_staff_by_id` uses `session.get` (single PK); `list_staff` uses simple `select(Staff)`. No N+1.
- ✅ **Layer 4 — blocking work on event loop**: `AuthService.hash_password` offloads Argon2 to `run_in_executor` (auth_service.py:112-115, from T-002).
- ✅ **Layer 5 — module-level mutable state**: None. `router = APIRouter(...)` immutable after construction.
- ✅ **Naming conforms to §2**: `*Dep` aliases, `get_` factories, `verb_noun` repository functions, camelCase JSON aliases, `StaffCreate`/`StaffUpdate`/`StaffRead` schema naming — all consistent.
- ✅ **Correlation ID / structured logging**: `correlation_id_middleware` (main.py:42-52); `domain_error_handler` (main.py:55-72) includes correlation_id in all error responses; 500 handler logs via `logger.exception(..., extra={"correlation_id": ...})`.
- ✅ **Secrets / config inline**: None. `AuthService` receives `Settings` via DI.

Fowler smells:

- ⚠️ **minor (carried forward) — Duplicated Code**: "Fetch-or-raise-404" pattern duplicated between `get_staff_endpoint` (staff.py:96-98) and `update_staff_endpoint` (staff.py:113-115). Was a nit in R1; still present. **Fix direction:** extract `_get_staff_or_404(session, staff_id) -> Staff` helper. (3-line duplication — low impact.)
- ⚠️ **minor (carried forward, T-002 carryover) — Inconsistent 401 body**: `get_current_user` (auth.py:56-56, 63) raises bare `HTTPException(401, detail="Invalid or expired token")` for missing/malformed/expired tokens and non-existent/inactive staff. Produces non-standardized body `{"detail": "Invalid or expired token"}` lacking `error`/`correlation_id` per Architecture §4. The `InvalidCredentialsError` (401, `AUTH_INVALID_CREDENTIALS`) and `InactiveAccountError` (401, `AUTH_INACTIVE_ACCOUNT`) classes exist in `auth_service.py:54-65` but are not used here. Explicitly documented as out-of-scope in the implementation log. **Fix direction:** raise `InvalidCredentialsError` (or a dedicated `AuthTokenError(DomainError)`) so the `DomainError` handler formats the 401 body consistently.

## Tests

- ⚠️ **minor — Missing GET /api/v1/staff/{id} 200 happy-path test.** The spec endpoint table (Spec 01 §4, row 3) lists `GET /api/v1/staff/{staff_id}` → 200 as a success path. Only the 404 failure path is tested (`test_get_nonexistent_staff_returns_404`). No test verifies that fetching an *existing* staff member by ID returns `200 StaffRead` with the correct fields. A regression where `get_staff_endpoint` returns wrong data, wrong status, or 500 for a valid ID would go undetected. (Note: `_staff_read` and `get_staff_by_id` are indirectly exercised by the PATCH success test, but the GET /{id} route handler itself is untested for the success case.) **Fix direction:** add `test_get_existing_staff_returns_200` asserting 200 + correct `id`/`email`/`role` in the response body, with expected values from the fixture (independent of implementation).
- ✅ **All round-1 test findings addressed**: 404 tests (major), DENTIST sub-case, 401 tests, and hardened list-filter assertion — all verified present and correct.
- ✅ **Independent expected values — no tautological assertions**: `201`/`200`/`401`/`403`/`404`/`409` come from Spec 01 §4/§7 and PRD R-2; `RBAC_FORBIDDEN`/`STAFF_EMAIL_EXISTS`/`STAFF_NOT_FOUND` come from Spec 01 §7 error-code table; `"Insufficient role"` comes from `ForbiddenError.message`; `"DENTIST"`/`"ADMIN"`/`"RECEPTIONIST"` come from fixtures or the request payload the test controls. No assertion recomputes the answer the way the code does. ✅
- ✅ **Tests assert behaviour at the HTTP seam**: all 10 tests drive `AsyncClient` over `ASGITransport` — no private-structure assertions. ✅
- ✅ **No sleeps, order dependence, or shared-mutable fixtures**: all fixtures are function-scoped; `test_staff`/`admin_staff`/`receptionist_staff` each create fresh DB rows with UUID-based unique emails; `auth_headers` is a factory; no cross-test ordering assumptions. ✅

## Summary

| Severity | Count | Findings |
|---|---|---|
| blocker | 0 | — |
| major | 0 | — |
| minor | 1 | Missing GET /{id} 200 happy-path test (test coverage gap, not a code defect) |
| nit | 3 | Duplicated fetch-or-404 (staff.py:96-98, 113-115); stale `AuthError` docstring (auth_service.py:45-46); non-standardized 401 body via bare `HTTPException` (auth.py:56-56, 63 — T-002 carryover) |

**All round-1 blockers and majors addressed.** The implementer added 5 tests (covering both 404 paths, DENTIST sub-case, two 401 paths) and strengthened the list-filter assertion — all at the HTTP seam with spec-derived expected values. No implementation code changes were needed (the `StaffNotFoundError` guards and `require_roles` RBAC guard were already correct). All four quality gates are green (ruff ✓, ruff format ✓, mypy ✓, pytest 22 passed).

**Single worst issue:** The missing GET /api/v1/staff/{id} 200 success-path test (minor) — the only spec'd endpoint with a tested failure path but untested happy path. However, this is an optional test-coverage improvement, not a code defect; the shared `_staff_read` projection is exercised by the PATCH success test (AC5), and the 404 path is tested.

The 3 carried-forward nits are all optional: the duplicated 3-line fetch-or-404 is trivially deduplicated, the stale `AuthError` docstring is a one-line fix, and the non-standardized 401 body is a T-002 carryover explicitly scoped out of T-003 (the `InvalidCredentialsError`/`InactiveAccountError` classes already exist for a future ticket to wire in).

**Verdict: Approve** — the ticket's 5 acceptance criteria are each covered by at least one test with spec-derived expected values, all round-1 findings are resolved, and all quality gates pass. The 1 minor and 3 nits are optional improvements the implementer may address at their discretion.
