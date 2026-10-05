# Review T-004 round 1 — Changes requested

Gates: ruff ✓ · ruff format ✓ · mypy ✓ · pytest ✓ (27 passed)

Spec sources verified against: `work/specs/03-services.md` (§2 Layer 1 Contracts, §3 Layer 2 Persistence/Repository, §4 Layer 3 Wiring/Endpoints, §7 Errors), `work/specs/00-architecture.md` (§4 Global Error Model, §5 AuthN/AuthZ, §6 Quality Gates), PRD `R-6` (CONTEXT.md glossary), `docs/adr/`. Standards source: `fastapi-production-architecture` skill (§2 Naming, §3 Layered smell checklist, §4 Transactions, §5 DI) + Fowler baseline.

Diff reviewed: `git diff 24e5f07..d7adef5` (commit `d7adef5` on top of T-003 done baseline `24e5f07`).

---

## Spec

For each acceptance criterion, the implementing code and test are matched against the quoted spec line.

| AC | Spec requirement (quoted) | Code | Test | Verdict |
|---|---|---|---|---|
| AC1 | *"Given an Admin user, When `POST /api/v1/services` is submitted with valid name and positive `duration_minutes` (e.g. 45), Then it returns `201 Created` with the saved service (R-6)."* | `routers/services.py:42-60` — POST, `status_code=201`, `response_model=ServiceRead`, `dependencies=[Depends(require_roles("ADMIN"))]`; `ServiceCatalog.create` (service_catalog.py:24-38) enforces name uniqueness before `create_service` (repository.py:48-58). `ServiceDuration = Field(gt=0, le=480)` (schemas.py:44-50). | `test_admin_creates_dental_service_201` — asserts 201, `body["durationMinutes"] == 45`, `body["isActive"] is True`. | ✅ Met. |
| AC2 | *"Given a non-Admin user, When attempting to create or edit a dental service, Then the system returns `403 Forbidden`."* | POST + PATCH both use `dependencies=[Depends(require_roles("ADMIN"))]` in `routers/services.py:34` and `routers/services.py:77`. `require_roles` (auth.py:83-101) raises `ForbiddenError` (403, `RBAC_FORBIDDEN`). | `test_non_admin_cannot_create_service_403` — RECEPTIONIST POST → 403, `error == "RBAC_FORBIDDEN"`, `"Insufficient role" in message`. ✅ POST covered. ❌ **PATCH ("edit") and DENTIST sub-cases not tested.** | ⚠️ Partially met — 403 guard correct, but AC2 says "create **or edit**"; only POST is verified. |
| AC3 | *"Given a service creation payload with duration <= 0 or > 480 minutes, When submitted, Then the system rejects it with `422 Unprocessable Entity`."* | `ServiceDuration = Annotated[int, Field(gt=0, le=480)]` (schemas.py:44). Used by `ServiceCreate.duration_minutes` and `ServiceUpdate.duration_minutes`. FastAPI auto-rejects invalid payloads with 422. | `test_invalid_duration_rejected_422` — schema unit test, raises `ValidationError` for `duration_minutes=0` and `-15`. ✅ Lower bound (<=0) covered. ❌ **Upper bound (>480) NOT tested** — AC3 explicitly says "or > 480 minutes." | ⚠️ Partially met — upper bound constraint correctly enforced but untested. |
| AC4 | *"Given a duplicate service name, When creation is attempted, Then the system returns `409 Conflict` with error code `SERVICE_NAME_EXISTS`."* | `ServiceCatalog.create` (service_catalog.py:26-30) calls `get_service_by_name` → raises `ServiceNameExistsError` (exceptions.py:58, 409, `SERVICE_NAME_EXISTS`) if found. | `test_duplicate_service_name_returns_409` — first POST → 201, second POST → 409, `body["error"] == "SERVICE_NAME_EXISTS"`. | ✅ Met. |
| AC5 | *"Given an active service, When an Admin updates it to `is_active = false`, Then subsequent list queries with `active_only=True` omit it."* | PATCH handler (services.py:75-89) → `catalog.update` (service_catalog.py:70-83) → `update_service` (repository.py:64-67) `setattr` + flush. `list_services(active_only=True)` (repository.py:61-68) filters `is_active.is_(True)`. | `test_list_services_active_filter` — creates service, PATCHes `{"isActive": False}` → asserts 200 + `isActive is False`, then GET list `active_only=True` → asserts deactivated service excluded + `all(isActive is True)`. | ✅ Met. |

**Spec endpoint-table coverage gaps (Spec 03 §4):**

The spec §4 endpoint table lists these error codes per route:

| Endpoint | 200 | 401 | 403 | 404 | 409 | 422 |
|---|---|---|---|---|---|---|
| POST /services | (test 1: 201) | inherited | test 2 ✓ | — | test 4 ✓ | unit test |
| GET /services | (test 5 partial) | inherited | — | — | — | — |
| GET /services/{id} | ⚠️ untested | inherited | — | ⚠️ **untested** | — | — |
| PATCH /services/{id} | (test 5: 200) | inherited | ⚠️ untested | ⚠️ untested | ⚠️ untested | — |

**Major — Missing 404 failure-path tests for GET /{id} and PATCH:** Spec 03 §4 lists `404` (error code `SERVICE_NOT_FOUND`) for both `GET /api/v1/services/{service_id}` and `PATCH /api/v1/services/{service_id}`. The `ServiceNotFoundError` is correctly wired — `ServiceCatalog.get` (service_catalog.py:63-65) raises it for missing IDs, `ServiceCatalog.update` (service_catalog.py:73) calls `self.get` which raises it, and the global `DomainError` handler (main.py:60-77) maps it to 404. **However, no API test exercises either 404 path.** The implementation log acknowledges this for GET /{id} (impl-log line: *"A follow-up could add a test_get_nonexistent_service_returns_404 test for the 404 path"*) but the PATCH 404 is not mentioned. This is the same class of gap T-003 round 1 flagged as **major** (missing 404 tests for `StaffNotFoundError`) — the behaviour is correct but the handler→exception→handler wiring for the new domain error is unverified at the seam. **Fix:** add `test_get_nonexistent_service_returns_404` and `test_patch_nonexistent_service_returns_404`, each asserting `404` + `body["error"] == "SERVICE_NOT_FOUND"`.

**Scope:** No scope creep. Every introduced symbol is within T-004 scope: `DentalService` model, `ServiceDuration`/`ServiceCreate`/`ServiceRead`/`ServiceUpdate` schemas, `ServiceNotFoundError`/`ServiceNameExistsError` exceptions, 5 repository functions, `ServiceCatalog` domain service, `ServiceCatalogDep` dependency, 4 endpoints. The `get_service_by_name` repository addition is a necessary helper for the duplicate-name business rule (documented in impl log; Spec 03 §3 lists 4 signatures, this is a 5th). ✅

**Silent deviations:** None from spec endpoints, status codes, or error codes. The `DentalService.appointments` relationship from Spec 03 §3 is omitted — but this is **not silent**: the impl log documents it with the reason that the `Appointment` model does not exist yet (T-008/T-010). It is not a defect.

---

## Standards

All `fastapi-production-architecture` checklist smells are clean for this diff:

- ✅ **Layer 3 — Handler opens own session / builds services inline:** handlers consume `ServiceCatalogDep` (services.py:18, 28, 41, 63). No inline service construction in handlers. (Unlike T-003's staff router which called `auth_service.hash_password` and `get_staff_by_email` directly in the handler, T-004 correctly delegates all business logic to `ServiceCatalog`.)
- ✅ **Layer 3 — Role checks scattered as `if user.role`:** RBAC centralized in `require_roles("ADMIN")` closure (auth.py:83-101), applied as route-level `dependencies=[...]` on POST and PATCH. GET endpoints use `Depends(get_current_user)` for authentication-only access. No scattered checks.
- ✅ **Layer 1 — Business rules in handlers:** Duplicate-name guard and existence validation live in `ServiceCatalog.create`/`get`/`update` (service_catalog.py), not in handlers. Field validation (`ServiceDuration`, `NonEmptyStr`) is in Pydantic schema validators.
- ✅ **Layer 1 — v1 idioms:** `model_validate` (services.py:19, 22-27 projection) and `model_dump(exclude_unset=True)` (services.py:84) throughout. No `parse_obj()`/`dict()`.
- ✅ **Layer 2 — per-row queries / missing eager loading:** `get_service_by_id` uses `session.get` (single PK lookup, repository.py:20); `list_services` uses a single `select` (repository.py:61-68); `get_service_by_name` uses single `select` (repository.py:23-26). No N+1. No relationships to eagerly load (appointments omitted).
- ✅ **Layer 4 — blocking work on event loop:** All repository and service methods are `async` with `await`. No sync I/O or CPU-bound work.
- ✅ **Layer 5 — module-level mutable state:** None. `router = APIRouter(...)` is immutable after construction. `ServiceCatalog` holds only request-scoped `AsyncSession`.
- ✅ **Naming conforms to §2:** `*Dep` aliases (`ServiceCatalogDep`), `get_` factory (`get_service_catalog`), `verb_noun` repository functions (`create_service`, `get_service_by_id`, `list_services`, `update_service`), camelCase JSON aliases (`durationMinutes`, `isActive`, `createdAt`), `ServiceCreate`/`ServiceRead`/`ServiceUpdate` schema naming — all consistent with the staff module.
- ✅ **Correlation ID / structured logging:** `correlation_id_middleware` (main.py:47-57) + `domain_error_handler` includes `correlation_id` in 404/409 error responses (main.py:60-77). Present in shared infra.
- ✅ **Secrets / config inline:** None. `ServiceCatalog` receives `AsyncSession` via DI; no settings or secrets in the service or router.

Fowler baseline:

- ✅ **No Duplicated Code:** The T-003 round-2 "fetch-or-404" duplication smell is *avoided* here — `ServiceCatalog.get()` (`service_catalog.py:63-65`) and `catalog.update()` (`service_catalog.py:73`) centralize the existence check. Both handlers delegate to the catalog, so there's no duplicated `if service is None: raise ServiceNotFoundError` across `get_service_endpoint` and `update_service_endpoint`. The `_service_read` projection mirrors `_staff_read` (`routers/staff.py:58`), which is the established codebase pattern for ORM→DTO projection, not a new smell.
- ✅ **No other Fowler smells** (Mysterious Name, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man, Refused Bequest): none observed in the diff.

---

## Tests

- ✅ **Every acceptance criterion has a test at the named seam.** AC1 (API/HTTP), AC2 (API/HTTP — partial, see minor), AC3 (schema unit), AC4 (API/HTTP), AC5 (API/HTTP). The test plan's 5 seams are all present.
- ✅ **Expected values are independent of implementation — no tautological assertions.** Status codes (201/403/409/422/200) and error codes (`SERVICE_NAME_EXISTS`, `RBAC_FORBIDDEN`, `SERVICE_NOT_FOUND`) come from Spec 03 §4/§7 and PRD R-6. `45` is the value the test itself submits (round-trip verification at the HTTP seam, not a recomputation) — it catches serialization/alias/persistence bugs. `isActive is True` asserts the `ServiceRead` default is applied (schema default, not computed by the code under test). `"Insufficient role"` comes from `ForbiddenError.message`. No assertion recomputes the answer the way the code does.
- ✅ **Tests assert behaviour, not private structure.** All 5 tests drive `httpx.AsyncClient` over `ASGITransport(app=app)` — the public HTTP seam. The one schema-unit test (`test_invalid_duration_rejected_422`) tests the constrained type at its own named seam. No private-method calls.
- ✅ **Failure paths exist for spec'd errors where listed:** AC4 (409) ✓, AC2 (403) ✓ for POST, AC3 (422) ✓. ⚠️ 404 on GET/{id} and PATCH is spec-listed but untested (see **major** above). ⚠️ 409 on PATCH (duplicate-name-on-rename) is spec-listed but untested (see minor).
- ✅ **No sleeps, order dependence, or shared-mutable fixtures.** All fixtures are function-scoped (`admin_staff`, `receptionist_staff`, `client`). Staff fixtures use UUID-based unique emails (`f"admin-{uuid.uuid4().hex[:8]}@clinic.com"`). `auth_headers` is a factory closure. Service names are unique per test. No cross-test ordering assumptions — `test_list_services_active_filter` asserts `service_id not in ids` and `all(isActive is True)` in the remaining list regardless of other fixtures' state.

**Test-coverage gaps (summary):**

| Gap | Spec location | Severity |
|---|---|---|
| GET /{id} 404 + PATCH 404 untested (ServiceNotFoundError → 404) | Spec 03 §4 (error column) | **major** |
| AC3 upper bound (>480) untested | AC3 / Spec 03 §2 | minor |
| AC2 "edit" (PATCH 403) sub-case untested | AC2 / Spec 03 §4 | minor |
| DENTIST role 403 untested (AC2 "non-Admin" only tests RECEPTIONIST) | AC2 / Spec 03 §5 | minor |
| GET /{id} 200 happy path untested | Spec 03 §4 (success column) | minor |
| PATCH 409 (duplicate-name-on-rename) untested | Spec 03 §4 (error column) | minor |

---

## Summary

| Severity | Count | Findings |
|---|---|---|
| blocker | 0 | — |
| major | 1 | Missing 404 failure-path tests for `GET /api/v1/services/{id}` and `PATCH` — spec §4 lists 404 (`SERVICE_NOT_FOUND`); code wires it correctly via `ServiceCatalog.get`/`update` → `ServiceNotFoundError` → global handler, but **zero test coverage** for the 404 path at the API seam. |
| minor | 5 | AC3 upper bound (>480) untested; AC2 "edit" (PATCH 403) sub-case untested; DENTIST-role 403 untested; GET /{id} 200 happy path untested; PATCH 409 duplicate-name-on-rename untested |

**Single worst issue:** The `GET /api/v1/services/{id}` and `PATCH /api/v1/services/{service_id}` 404 paths are entirely untested. Spec 03 §4 explicitly lists `404` / `SERVICE_NOT_FOUND` for both endpoints, the `ServiceCatalog` raises `ServiceNotFoundError` correctly, and the global `DomainError` handler maps it — but no test at the HTTP seam verifies this chain. This is the same gap class that T-003 round 1 flagged as major and required fixes for before approval. The implementation is correct; only the test coverage is missing.

**Verdict: Changes requested** — the 1 major must be resolved (add 404 tests for GET/{id} and PATCH) before this ticket can be approved. The 5 minors are optional but recommended. All 4 quality gates are green (ruff ✓, ruff format ✓, mypy ✓, pytest 27 passed), so no implementation changes are required — only test additions.
