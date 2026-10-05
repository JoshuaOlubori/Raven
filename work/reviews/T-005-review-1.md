# Review T-005 round 1 — Changes requested

Gates: ruff ✓ · ruff format ✓ · mypy ✓ · pytest ✓ (40 passed)

Verified against: `work/specs/02-patients.md` (§2 Layer 1 Contracts, §3 Layer 2 Persistence/Repository, §4 Layer 3 Wiring/Endpoints, §7 Errors), `work/specs/00-architecture.md` (§4 Global Error Model, §5 AuthN/AuthZ, §6 Quality Gates, §7 State), PRD `R-3` / `R-4` / `R-5` / `NFR-6` (work/prd.md §4.2, §6), `CONTEXT.md` (Glossary), `docs/adr/0001` (slot computation), Standard `fastapi-production-architecture` (§2 Naming, §3 Layered smell checklist, §4 Transactions, §5 DI) + Fowler baseline.

Diff reviewed: `git diff 835e9dc..0204012` (commit `0204012` on top of T-004 done baseline `835e9dc`).

---

## Spec

For each acceptance criterion, the implementing code and test are matched against the quoted spec line.

| AC | Spec requirement (quoted from ticket / PRD / Spec 02) | Code | Test | Verdict |
|---|---|---|---|---|
| AC1 | *"Given valid demographic data and medical alert text, When `POST /api/v1/patients` is submitted, Then it returns `201 Created` with computed `fullName` (R-3)."* — PRD R-3: "Given valid demographic fields and allergy flags, When staff post to `POST /api/v1/patients`, Then a new patient profile is created with `201 Created`." | `routers/patients.py:104-125` — POST, `status_code=201`, `response_model=PatientRead`, `dependencies=[Depends(require_roles("ADMIN", "RECEPTIONIST"))]`; `PatientRead` has `@computed_field(alias="fullName")` (schemas.py:222-248). | `test_create_patient_success_201` — asserts 201, `body["fullName"] == "Jane Doe"`, `body["medicalAlerts"] == "Penicillin allergy"`. | ✅ Met. |
| AC2 | *"Given an invalid phone format or date of birth in the future, When submitted, Then the system returns `422 Unprocessable Entity`."* — PRD R-3: "Given missing mandatory fields (e.g. phone number or DOB), When staff attempt creation, Then the system returns `422 Unprocessable Entity`." | `PhoneStr` with `pattern=r"^\+?[0-9\s\-()]+$"` + `min_length=7, max_length=20` (schemas.py:52-56); `PatientCreate._dob_not_in_future` model_validator (schemas.py:188-193). | `test_invalid_phone_rejected_422` (422, API seam) ✅ · `test_create_patient_missing_phone_422` (422, API seam) ✅ · `test_future_dob_rejected_422` (schema unit, ValidationError) ✅. | ✅ Met. |
| AC3 | *"Given a search string matching first name, last name, or phone number, When querying `GET /api/v1/patients?search=smith`, Then matching active patients are returned with pagination metadata (R-4)."* — PRD R-4: "Given multiple registered patients, When staff query `GET /api/v1/patients?search=smith`, Then matching active patients are returned with pagination metadata." | `list_patients`: `ILIKE` on `first_name`, `last_name`, `phone` (repository.py:74-88); `is_active.is_(True)` filter by default (repository.py:79); `PatientPage` with `items`, `total`, `page`, `size`, `pages` (schemas.py:251-260). | `test_search_patients_by_name_and_phone` — asserts 200, `total >= 1`, `items` returned, `page == 1`, `size == 50`, `pages >= 1`; verifies both name and phone search. | ✅ Met. |
| AC4 | *"Given an existing patient, When `DELETE /api/v1/patients/{id}` is executed, Then the patient is marked `is_active = false` and returns `204 No Content` (R-5)."* — PRD R-5: "Given an existing patient, When staff invoke `DELETE /api/v1/patients/{id}`, Then the patient is marked `is_active = false`." | `delete_patient_endpoint`: `status_code=204`, `require_roles("ADMIN", "RECEPTIONIST")` (routers/patients.py:85-98); `service.soft_delete` → `soft_delete_patient` sets `is_active = False`, no SQL DELETE (repository.py:144-150). | `test_soft_delete_patient_sets_inactive` — asserts 204, then GET search "Doe" excludes patient. | ✅ Met. |
| AC5 | *"Given a soft-deleted patient, When querying default patient searches, Then they are excluded from the result set (R-5)."* | `list_patients` filters `is_active.is_(True)` by default (repository.py:79); service.list doesn't pass `include_inactive=True`. | `test_soft_delete_patient_sets_inactive` — same test: after DELETE, GET search "Doe" → `patient_id not in found_ids`. | ✅ Met. |

### Spec 02 §4 endpoint error-code matrix — coverage gaps

The spec §4 endpoint table lists these error codes per route:

| Endpoint | 200 | 401 | 403 | 404 | 422 |
|---|---|---|---|---|---|
| POST /patients | test 1 (201) ✅ | inherited ✅ | ⚠️ untested | — | test 2, 3 ✅ |
| GET /patients | test 4 (200) ✅ | test 5 ✅ | ⚠️ untested | — | — |
| GET /patients/{id} | ❌ | inherited ✅ | ❌ | ❌ | — |
| PATCH /patients/{id} | ❌ | inherited ✅ | ❌ | ❌ | ❌ |
| DELETE /patients/{id} | test (204) ✅ | inherited ✅ | ❌ | ❌ | — |

**Scope:** No scope creep. Every introduced symbol falls within T-005 scope. `PatientNotFoundError` mirrors `ServiceNotFoundError` (T-004). `_patient_read` mirrors `_service_read` (services router). The `get_patient_service` dependency mirrors `get_service_catalog`. No extra endpoints, no extra business logic beyond the spec. ✅

**Silent deviations:**

- **GET endpoints use `Depends(get_current_user)` instead of Spec 02 §4's `require_roles("ADMIN", "RECEPTIONIST", "DENTIST")`** (routers/patients.py:33, 36). The spec explicitly declares the guard as `require_roles(...)`:
  - `GET /api/v1/patients` — spec §4: `require_roles("ADMIN", "RECEPTIONIST", "DENTIST")`, impl: `Depends(get_current_user)` (routers/patients.py:32)
  - `GET /api/v1/patients/{patient_id}` — spec §4: `require_roles("ADMIN", "RECEPTIONIST", "DENTIST")`, impl: `Depends(get_current_user)` (routers/patients.py:35)

  This is a deviation from the spec's explicit guard declaration. It is **behaviorally equivalent** — `StaffRole = Literal["ADMIN", "RECEPTIONIST", "DENTIST"]`, so `require_roles("ADMIN", "RECEPTIONIST", "DENTIST")` can never raise 403 for any valid staff member; any authenticated, active staff passes both. No security hole, but the code does not match the spec's wiring. The implementation log's claim of "No spec deviations" is incorrect on this point. (Note: T-004 made the same choice for `GET /services` and was not flagged — this is an established codebase pattern, but it is a written deviation from the T-005 spec.)

  **Fix direction:** either change the GET endpoint guards to `dependencies=[Depends(require_roles("ADMIN", "RECEPTIONIST", "DENTIST"))]` to match the spec, or update the spec to document `get_current_user` as the accepted guard for "all staff" read endpoints.

---

## Standards

All `fastapi-production-architecture` checklist smells are clean for this diff:

- ✅ **Layer 3 — Handler opens own session / builds services inline:** handlers consume `PatientServiceDep` (`routers/patients.py:11, 26, 33, 36, 41`). No inline service construction. The handler is the *last* stop before the service layer — it delegates to `service.create/get/list/update/soft_delete` and only projects to the read model.
- ⚠️ **Layer 3 — Role checks scattered as `if user.role` / spec guard deviation:** Write endpoints (POST, PATCH, DELETE) correctly use `require_roles("ADMIN", "RECEPTIONIST")` as route-level `dependencies=[...]`. GET endpoints use `Depends(get_current_user)` — see silent deviation above. No scattered `if user.role` checks anywhere.
- ✅ **Layer 1 — Business rules in handlers:** DOB-future validation lives in Pydantic `model_validator` (schemas.py:188-193, 214-219); existence checks live in `PatientService.get` (patient_service.py:60-614); phone format validation in `PhoneStr`. No business rules in handlers.
- ✅ **Layer 1 — v1 idioms:** `model_validate` (routers/patients.py:286) and `model_dump(exclude_unset=True)` (routers/patients.py:380) throughout. No `parse_obj()` / `dict()`.
- ✅ **Layer 2 — per-row queries / missing eager loading:** `get_patient_by_id` uses `session.get` (single PK lookup). `list_patients` uses a single `select` with `ILIKE` + `ORDER BY` + `LIMIT/OFFSET`; count via `select(func.count()).select_from(stmt.subquery())` before pagination is applied (repository.py:91-92). No N+1. No relationships to eagerly load (appointments omitted per spec).
- ✅ **Layer 4 — blocking work on event loop:** All repository and service methods are `async` with `await`. `math.ceil(total / size)` in handler (routers/patients.py:345) is trivial arithmetic, not blocking I/O.
- ✅ **Layer 5 — module-level mutable state:** None. `router = APIRouter(...)` is immutable. `PatientService` holds only request-scoped `AsyncSession`.
- ✅ **Naming conforms to §2:** `PatientServiceDep` / `get_patient_service` (deps.py:84-89) mirror `ServiceCatalogDep` / `get_service_catalog`. Repository functions `create_patient`, `get_patient_by_id`, `list_patients`, `update_patient`, `soft_delete_patient` mirror the service catalog naming. camelCase aliases (`firstName`, `lastName`, `dateOfBirth`, `medicalAlerts`, `isActive`, `createdAt`, `updatedAt`, `fullName`) consistent with staff/service modules. Endpoint names `create_patient_endpoint`, `list_patients_endpoint`, etc. follow the `*_endpoint` convention from T-004.
- ✅ **Correlation ID / structured logging:** `correlation_id_middleware` (main.py:53-62) extracts/generates `X-Correlation-ID`; `domain_error_handler` (main.py:66-82) includes it in error responses. `PatientNotFoundError` → `DomainError` → handler maps to 404 + `PATIENT_NOT_FOUND`. ✅
- ✅ **Secrets / config inline:** None. `PatientService` receives `AsyncSession` via DI; no settings or secrets in the service or router.

Fowler baseline:

- ✅ **No Duplicated Code:** The `PatientService.get` existence-check pattern (patient_service.py:60-614) centralizes the "fetch-or-404" logic — `update` and `soft_delete` both call `self.get`, which raises `PatientNotFoundError`. No duplication across `get_patient_endpoint`, `update_patient_endpoint`, or `delete_patient_endpoint`. The `_patient_read` projection mirrors `_service_read` (services.py:23) — established codebase pattern for ORM→DTO projection, not a new smell.
- ✅ **No other Fowler smells** (Mysterious Name, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man, Refused Bequest): none observed.

---

## Tests

- ✅ **Every acceptance criterion has a test at the named seam.** AC1 (API/HTTP), AC2 (API/HTTP for phone + schema unit for DOB), AC3 (API/HTTP), AC4 (API/HTTP), AC5 (API/HTTP — same test as AC4). The ticket's test plan (5 seams) is fully covered, plus the implementation added 2 extra API tests for phone validation (AC2 sub-coverage beyond the plan).
- ✅ **Expected values are independent of implementation — no tautological assertions.** `fullName == "Jane Doe"` comes from the test's own input ("Jane" + "Doe") via the API round-trip, not computed by the code under test. `medicalAlerts == "Penicillin allergy"` is the test's own input echoed back. `pages >= 1` (not a specific value) avoids depending on shared-DB row counts. Status codes and error codes come from Spec 02 §4 / §7 and PRD NFR-6. No assertion recomputes the answer the way the code does.
- ✅ **Tests assert behaviour, not private structure.** All 6 API tests drive `httpx.AsyncClient` over `ASGITransport(app=app)` (public HTTP seam). The schema unit test (`test_future_dob_rejected_422`) targets `PatientCreate` at its named seam. No private-method calls.
- ⚠️ **Failure paths — spec-listed errors not tested:**
  - **401**: `test_unauthenticated_request_rejected_401` covers unauthenticated GET /patients (401). ✅ For POST/PATCH/DELETE, 401 is inherited infrastructure (`get_current_user` from T-002/T-003, exercised by T-001/T-002 tests). Acceptable per T-004 precedent ("inherited").
  - **403**: ❌ No test verifies that a DENTIST is rejected from POST/PATCH/DELETE. Spec 02 §4 lists 403 for these endpoints; authorization matrix §4 says Create/Edit/Soft-Delete restricted to ADMIN, RECEPTIONIST only. The `require_roles("ADMIN", "RECEPTIONIST")` guard is the same function tested in T-003, but no API test exercises the 403 path for patient write endpoints.
  - **404**: ❌ No test verifies `PatientNotFoundError` → 404 for `GET /{id}`, `PATCH /{id}`, or `DELETE /{id}`. The wiring is correct (service.get raises PatientNotFoundError; service.update and service.soft_delete both call self.get; domain_error_handler maps to 404) but unverified at the HTTP seam.
  - **422**: ✅ POST 422 (phone pattern, missing phone, future DOB) covered at API + schema seams. ❌ PATCH 422 (future DOB on PatientUpdate) not tested at API seam — `PatientUpdate` has the same `_dob_not_in_future` validator (schemas.py:214-219), but no test exercises it via a PATCH request.
- ✅ **No sleeps, order dependence, or shared-mutable fixtures.** All fixtures function-scoped (`admin_staff`, `receptionist_staff`, `client`). Staff fixtures use UUID-based unique emails (conftest.py:207, 226). `auth_headers` is a factory closure. No cross-test ordering assumptions — assertions use `>=` and `not in` rather than exact counts.

**Test-coverage gaps (summary):**

| Gap | Spec location | Severity |
|---|---|---|
| GET /{id} 404 + PATCH /{id} 404 + DELETE /{id} 404 untested (PatientNotFoundError → 404) | Spec 02 §4 (error column) + §7 | **major** |
| DENTIST 403 on POST / PATCH / DELETE (RBAC rejection) | Spec 02 §4 (authz matrix §4) | minor |
| GET /{id} 200 happy path untested | Spec 02 §4 (success column) | minor |
| PATCH /{id} 200 (successful update) untested | Spec 02 §4 (success column) | minor |
| GET endpoints use `get_current_user` not `require_roles` per spec | Spec 02 §4 (guard column) | minor |
| PATCH /{id} 422 (future DOB on PatientUpdate) not tested at API seam | Spec 02 §4 (error column) | nit |

---

## Summary

| Severity | Count | Findings |
|---|---|---|
| blocker | 0 | — |
| major | 1 | Missing 404 failure-path tests for `GET /api/v1/patients/{id}`, `PATCH /api/v1/patients/{id}`, and `DELETE /api/v1/patients/{id}` — Spec 02 §4 explicitly lists `404` (`PATIENT_NOT_FOUND`) for all three endpoints. `PatientNotFoundError` is correctly wired: `PatientService.get` (patient_service.py:60-614) raises it for missing IDs, and both `service.update` (→ `self.get`) and `service.soft_delete` (→ `self.get`) route through it; the global `domain_error_handler` (main.py:66-82) maps it to `404`. But no API test at the HTTP seam verifies this chain. This is the same class of gap that T-003 round 1 and T-004 round 1 each flagged as **major** — the behaviour is correct, only the test coverage is missing. |
| minor | 4 | (1) DENTIST 403 on POST/PATCH/DELETE untested — Spec 02 §4 §4 authz matrix restricts Create/Edit/Soft-Delete to ADMIN+RECEPTIONIST only, but no test verifies a DENTIST is rejected; (2) GET /{id} 200 happy path untested — no test for retrieving a patient by ID; (3) PATCH /{id} 200 untested — no test for a successful profile update; (4) Silent deviation — GET endpoints use `Depends(get_current_user)` instead of Spec 02 §4's `require_roles("ADMIN", "RECEPTIONIST", "DENTIST")` (behaviourally equivalent but doesn't match spec guard declaration). |
| nit | 1 | PATCH /{id} 422 (future DOB on `PatientUpdate`) not tested at API seam — `PatientUpdate` has the same `_dob_not_in_future` validator as `PatientCreate` (schemas.py:214-219), and the schema unit test covers `PatientCreate`; the PATCH validation path is structurally identical (Pydantic model_validator runs before the handler). Optional follow-up: add `test_patch_future_dob_rejected_422`. |

**Single worst issue:** The `GET /{id}`, `PATCH /{id}`, and `DELETE /{id}` 404 paths are entirely untested. Spec 02 §4 explicitly lists `404` / `PATIENT_NOT_FOUND` for all three endpoints, the `PatientService.get`/`update`/`soft_delete` chain raises `PatientNotFoundError` correctly, and the global `domain_error_handler` maps it — but no test at the HTTP seam verifies this wiring. This is the same gap class that T-003 round 1 and T-004 round 1 each flagged as major and required fixes for before approval.

**Verdict: Changes requested** — the 1 major must be resolved (add 404 tests for `GET /{id}`, `PATCH /{id}`, `DELETE /{id}`, each asserting `404` + `body["error"] == "PATIENT_NOT_FOUND"`) before this ticket can be approved. The 4 minors are recommended. The 1 nit is optional. All 4 quality gates are green (ruff ✓, ruff format ✓, mypy ✓, pytest 40 passed), so no implementation changes are required — only test additions.
