# Review T-005 round 2 — Approve

Gates: ruff ✓ · ruff format ✓ · mypy ✓ · pytest ✓ (47 passed)

Verified against: `work/specs/02-patients.md` (§2 Layer 1 Contracts, §3 Layer 2 Persistence/Repository, §4 Layer 3 Wiring/Endpoints, §5 Soft Deletion, §7 Errors), `work/specs/00-architecture.md` (§4 Global Error Model, §5 AuthN/AuthZ, §6 Quality Gates, §7 State), PRD `R-3` / `R-4` / `R-5` / `NFR-6` (work/prd.md §4.2, §6), `CONTEXT.md` (Glossary), Standard `fastapi-production-architecture` (§2 Naming, §3 Layered smell checklist, §4 Transactions, §5 DI) + Fowler baseline.

Diff reviewed: `git diff 0204012..58792d1` (commit `58792d1` on top of round-1 baseline `0204012`). **The fix commit contains only test additions + a spec footnote — no implementation code changed.** The round-1 implementation was correct; only test coverage was missing. (Commit `5b1d784` on top merely corrected a SHA reference in the ticket's implementation log from `cf5dfce` to `58792d1`.)

---

## Spec

All six round-1 findings fully resolved. The Spec 02 §4 endpoint error-code matrix is now fully exercised (see matrix below).

### Acceptance criteria — round 2 status

| AC | Spec requirement (quoted from ticket / PRD) | Test(s) | Verdict |
|---|---|---|---|
| AC1 | *"Given valid demographic data and medical alert text, When `POST /api/v1/patients` is submitted, Then it returns `201 Created` with computed `fullName` (R-3)."* — PRD R-3: "Given valid demographic fields and allergy flags, When staff post to `POST /api/v1/patients`, Then a new patient profile is created with `201 Created`." | `test_create_patient_success_201` — asserts 201, `body["fullName"] == "Jane Doe"`, `body["medicalAlerts"] == "Penicillin allergy"`. | ✅ Met (unchanged from round 1). |
| AC2 | *"Given an invalid phone format or date of birth in the future, When submitted, Then the system returns `422 Unprocessable Entity`."* | `test_invalid_phone_rejected_422` (422, API) ✅ · `test_create_patient_missing_phone_422` (422, API) ✅ · `test_future_dob_rejected_422` (schema unit, ValidationError) ✅. | ✅ Met (unchanged from round 1). |
| AC3 | *"Given a search string matching first name, last name, or phone number, When querying `GET /api/v1/patients?search=smith`, Then matching active patients are returned with pagination metadata (R-4)."* — PRD R-4: "Given multiple registered patients, When staff query `GET /api/v1/patients?search=smith`, Then matching active patients are returned with pagination metadata." | `test_search_patients_by_name_and_phone` — asserts 200, `total >= 1`, `items` returned, `page == 1`, `size == 50`, `pages >= 1`; verifies both name and phone search. | ✅ Met (unchanged from round 1). |
| AC4 | *"Given an existing patient, When `DELETE /api/v1/patients/{id}` is executed, Then the patient is marked `is_active = false` and returns `204 No Content` (R-5)."* | `test_soft_delete_patient_sets_inactive` — asserts 204, then GET search "Doe" excludes patient. | ✅ Met (unchanged from round 1). |
| AC5 | *"Given a soft-deleted patient, When querying default patient searches, Then they are excluded from the result set (R-5)."* | `test_soft_delete_patient_sets_inactive` — same test: after DELETE, GET search "Doe" → `patient_id not in found_ids`. | ✅ Met (unchanged from round 1). |

### Spec 02 §4 endpoint error-code matrix — round 2 coverage

| Endpoint | 200/201/204 | 401 | 403 | 404 | 422 |
|---|---|---|---|---|---|
| POST /patients | `test_create_patient_success_201` (201) ✅ | inherited (`get_current_user` / `require_roles`) ✅ | `test_dentist_rejected_from_patient_write_403` ✅ | — | `test_invalid_phone_rejected_422` ✅ · `test_create_patient_missing_phone_422` ✅ |
| GET /patients | `test_search_patients_by_name_and_phone` (200) ✅ | `test_unauthenticated_request_rejected_401` ✅ | — (all-staff read via `get_current_user`¹) ✅ | — | — |
| GET /patients/{id} | `test_get_patient_by_id_200` ✅ new | inherited ✅ | — (all-staff read via `get_current_user`¹) ✅ | `test_get_nonexistent_patient_returns_404` ✅ new | — |
| PATCH /patients/{id} | `test_update_patient_200` ✅ new | inherited ✅ | `test_dentist_rejected_from_patient_write_403` ✅ new | `test_patch_nonexistent_patient_returns_404` ✅ new | `test_patch_future_dob_rejected_422` ✅ new |
| DELETE /patients/{id} | `test_soft_delete_patient_sets_inactive` (204) ✅ | inherited ✅ | `test_dentist_rejected_from_patient_write_403` ✅ new | `test_delete_nonexistent_patient_returns_404` ✅ new | — |

¹ Footnoted in Spec 02 §4: `Depends(get_current_user)` is the accepted guard for all-staff read endpoints — behaviourally equivalent to `require_roles("ADMIN", "RECEPTIONIST", "DENTIST")` because `StaffRole = Literal["ADMIN", "RECEPTIONIST", "DENTIST"]` (CONTEXT.md glossary), so no authenticated staff can be 403'd on a GET endpoint. This pattern is established by T-004 and applied consistently.

### Verification notes for new 404 tests

- **`test_get_nonexistent_patient_returns_404`** — uses `admin_staff` (passes `require_roles`), GETs a random `uuid.uuid4()`. Trace: `get_patient_endpoint` → `service.get(random_uuid)` → `get_patient_by_id` returns `None` → `PatientNotFoundError` raised → `domain_error_handler` (`main.py:65-82`) maps to `404` + `body["error"] == "PATIENT_NOT_FOUND"`. ✅ Verified against `patient_service.py:61-69` and `exceptions.py:66-71`.

- **`test_patch_nonexistent_patient_returns_404`** — uses `admin_staff` (passes RBAC), PATCHes a random `uuid.uuid4()` with `{"medicalAlerts": "Updated alert"}`. Trace: `require_roles("ADMIN", "RECEPTIONIST")` passes at route-level dependency → handler calls `service.update(random_uuid, medical_alerts="Updated alert")` → `self.get(random_uuid)` (`patient_service.py:95`) → `PatientNotFoundError` → 404. The 404 raises **before** `update_patient` is reached. ✅

- **`test_delete_nonexistent_patient_returns_404`** — same trace: RBAC passes → `service.soft_delete(random_uuid)` → `self.get(random_uuid)` → `PatientNotFoundError` → 404. ✅

### Verification notes for new 403 test

- **`test_dentist_rejected_from_patient_write_403`** — uses `dentist_staff`, attempts POST, PATCH, DELETE. The `phantom_id = str(uuid.uuid4())` is used for PATCH/DELETE — irrelevant because `require_roles("ADMIN", "RECEPTIONIST")` runs as a route-level `dependencies=[...]` *before* the handler, so `role_guard` (`auth.py:96-99`) sees `DENTIST not in ("ADMIN", "RECEPTIONIST")` → raises `ForbiddenError` → `domain_error_handler` maps to `403` + `body["error"] == "RBAC_FORBIDDEN"`. The 403 correctly short-circuits before any existence check. ✅ Verified against `auth.py:83-101` and `patients.py:48, 109, 125`.

### Verification notes for new 200 tests

- **`test_get_patient_by_id_200`** — creates a patient via POST (receptionist), then GETs by the returned `id`. Asserts `id`, `fullName == "Alice Smith"`, `medicalAlerts == "Diabetes"` — all from the test's own POST payload (round-trip, not recomputation). ✅

- **`test_update_patient_200`** — creates a patient (admin), PATCHes `firstName="Robert"` + `medicalAlerts="Asthma and penicillin allergy"`. Asserts `fullName == "Robert Jones"` (first_name updated to "Robert", last_name retained as "Jones" from creation) and `medicalAlerts == "Asthma and penicillin allergy"`. Expected values derive from the test's own input data, not from recomputing what the code does. ✅

### Verification notes for new 422 test

- **`test_patch_future_dob_rejected_422`** — creates a patient (admin), PATCHes `dateOfBirth = "2099-12-31"`. The `PatientUpdate._dob_not_in_future` `model_validator` (`schemas.py:214-219`) runs during FastAPI request-body validation — before the handler executes. Asserts `422`. ✅ This mirrors the POST 422 path (`PatientCreate._dob_not_in_future` at `schemas.py:188-193`) now covered at the API seam for PATCH as well.

**Scope:** No scope creep. The diff adds exactly 7 tests — all directly addressing round-1 findings. No new production code, no new dependencies. The spec footnote ¹ documents an already-deployed pattern. ✅

**Silent deviations:** None new. The `get_current_user` guard deviation from round 1 has been resolved by documenting the accepted pattern in Spec 02 §4 footnote ¹ (rather than changing code), keeping the codebase consistent with T-004. This is a *documented* deviation, not a *silent* one. ✅

---

## Standards

The diff is test-only + spec documentation, so implementation-layer standards from round 1 remain clean. The new test code is reviewed against the same checklist:

- ✅ **Layer 3 — Handler opens own session / builds services inline:** N/A (no handler changes). Existing handlers consume `PatientServiceDep` (`deps.py:84-89`) — no inline service construction. Unchanged.
- ✅ **Layer 3 — Scattered `if user.role`:** N/A (no auth changes). RBAC centralized in `require_roles("ADMIN", "RECEPTIONIST")` as route-level `dependencies=[...]` (`patients.py:48, 112, 128`). GET endpoints use `Depends(get_current_user)` — documented in spec footnote ¹. No scattered `if user.role` checks anywhere.
- ✅ **Layer 1 — Business rules in handlers:** N/A (no new business logic). DOB-future validation remains in Pydantic `model_validator` (`schemas.py:188-193, 214-219`); existence checks in `PatientService.get` (`patient_service.py:61-69`). Unchanged.
- ✅ **Layer 1 — v1 idioms:** N/A (no model code changed). Test code uses `response.json()` / dict access — no `parse_obj()` / `dict()` on Pydantic models. ✅
- ✅ **Layer 2 — per-row queries / missing eager loading:** N/A (no repository changes). `get_patient_by_id` uses `session.get` (single PK); `list_patients` uses a single `select` with `ILIKE` + `ORDER BY` + `LIMIT/OFFSET`; count via subquery (`repository.py:151-191`). Unchanged.
- ✅ **Layer 4 — blocking work on event loop:** N/A (no production code changed). All test code is `async` with `await` on the async client. ✅
- ✅ **Layer 5 — module-level mutable state:** N/A. No new module-level state. ✅
- ✅ **Naming conforms to §2:** Test names follow `test_<behaviour>_<expected>` convention. The `dentist_staff` fixture mirrors the established `admin_staff`/`receptionist_staff` naming pattern exactly (same structure, docstring style, `hashed_password="irrelevant"` sentinel). ✅
- ✅ **Correlation ID / structured logging:** N/A (no endpoint changes). The global `domain_error_handler` (`main.py:65-82`) includes `correlation_id` in all domain error responses. ✅
- ✅ **Secrets / config inline:** None. Test fixtures use `hashed_password="irrelevant"` for role-only tests (no real auth flow needed). ✅

Fowler baseline — no new smells in the test diff:

- ✅ **No Duplicated Code:** The 404 tests follow an identical structure (random UUID → assert 404 + `PATIENT_NOT_FOUND`), but this is the *established codebase pattern* from T-004 round 2 (`test_get_nonexistent_service_returns_404` / `test_patch_nonexistent_service_returns_404`). Consistency with precedent, not new duplication. The `dentist_staff` fixture mirrors `admin_staff`/`receptionist_staff` — intentional and consistent (Architecture §5 test strategy).
- ✅ **No other Fowler smells:** No Mysterious Name, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man, or Refused Bequest observed.

---

## Tests

All six round-1 findings fully resolved. All 7 new tests drive the public HTTP seam (`httpx.AsyncClient` over `ASGITransport`) — none poke at private structure.

### Every acceptance criterion has a test at the named seam

| AC | Seam (from ticket test plan) | Test(s) |
|---|---|---|
| AC1 (201 + fullName + medicalAlerts) | API + Receptionist auth | `test_create_patient_success_201` ✅ |
| AC2 (phone/DOB → 422) | Schema unit + API | `test_future_dob_rejected_422` (schema unit) ✅ · `test_invalid_phone_rejected_422` (API) ✅ · `test_create_patient_missing_phone_422` (API) ✅ · `test_patch_future_dob_rejected_422` (API) ✅ new |
| AC3 (search + pagination) | API + Staff auth | `test_search_patients_by_name_and_phone` ✅ |
| AC4 (soft delete → 204) | API + Receptionist auth | `test_soft_delete_patient_sets_inactive` ✅ |
| AC5 (excluded from search) | API + Staff auth | `test_soft_delete_patient_sets_inactive` (asserts `patient_id not in found_ids`) ✅ |

Plus the ticket's test plan seams (§Test plan) all covered: 401 (`test_unauthenticated_request_rejected_401`), 404 (`3 new`), 403 (`1 new`), 200 GET/PATCH (`2 new`).

### Expected values are independent of implementation — no tautological assertions

- `fullName == "Jane Doe"` comes from the test's own input ("Jane" + "Doe") via the API round-trip — the test does not recompute it via the same `f"{first_name} {last_name}"` expression the code uses. ✅
- `fullName == "Alice Smith"` and `fullName == "Robert Jones"` — expected values derived from the test's own POST/PATCH input data, not from calling `PatientRead.full_name` or duplicating the `f"{...} {last_name}"` logic. ✅
- `body["id"] == patient_id` — the ID is returned from the POST response and re-used in the GET; the assertion checks the round-trip identity, not a recomputed value. ✅
- `pages >= 1` (not a specific value) avoids depending on shared-DB row counts. ✅
- All status codes (201, 200, 204, 404, 403, 422, 401) and error codes (`PATIENT_NOT_FOUND`, `RBAC_FORBIDDEN`) come from Spec 02 §4 / §7 and PRD NFR-6, not from the implementation. ✅

### Tests assert behaviour, not private structure

All 13 API tests drive `httpx.AsyncClient` over `ASGITransport(app=app)` (public HTTP seam). The schema unit test (`test_future_dob_rejected_422`) targets `PatientCreate` at its named seam (Spec 02 §9). No private-method calls. ✅

### Failure paths — spec-listed errors all tested

- ✅ **401**: `test_unauthenticated_request_rejected_401` covers unauthenticated GET /patients (401). For POST/PATCH/DELETE, 401 is inherited infrastructure (`get_current_user` from T-002/T-003, exercised by T-001/T-002 tests). Acceptable per T-004 precedent ("inherited").
- ✅ **403**: `test_dentist_rejected_from_patient_write_403` verifies DENTIST → 403 (`RBAC_FORBIDDEN`) on POST/PATCH/DELETE. Spec 02 §4 authz matrix §4 restricts Create/Edit/Soft-Delete to ADMIN + RECEPTIONIST only.
- ✅ **404**: `test_get_nonexistent_patient_returns_404`, `test_patch_nonexistent_patient_returns_404`, `test_delete_nonexistent_patient_returns_404` — each asserts `404` + `body["error"] == "PATIENT_NOT_FOUND"`.
- ✅ **422**: POST 422 (phone pattern, missing phone, future DOB) covered. PATCH 422 (future DOB on `PatientUpdate`) now covered at API seam via `test_patch_future_dob_rejected_422`.
- ✅ **409**: Not applicable to this module (no conflict scenarios in Spec 02 §7).

### No sleeps, order dependence, or shared-mutable fixtures

All fixtures are function-scoped (`admin_staff`, `receptionist_staff`, `dentist_staff`, `client`, `auth_headers`). Staff fixtures use UUID-based unique emails (`f"admin-{uuid.uuid4().hex[:8]}@clinic.com"` pattern). Patient data is created per-test via POST with unique names ("Jane Doe", "Alice Smith", "Bob Jones", "Carol White"). Random UUIDs (`uuid.uuid4()`) for non-existent patient lookups. No cross-test ordering assumptions. ✅

### Test seam matrix

| Behaviour (Spec location) | Seam | Test | Independent expected values? |
|---|---|---|---|
| Receptionist POST valid patient → 201, fullName, medicalAlerts | API/HTTP | `test_create_patient_success_201` | ✅ "Jane Doe" from test input; "Penicillin allergy" from input |
| Invalid phone → 422 | API/HTTP | `test_invalid_phone_rejected_422` | ✅ 422 from Spec 02 §4/§7 |
| Missing phone → 422 | API/HTTP | `test_create_patient_missing_phone_422` | ✅ 422 from Spec 02 §4/§7 |
| Future DOB → 422 (create) | Schema unit | `test_future_dob_rejected_422` | ✅ `ValidationError` from Spec 02 §2 validator |
| Future DOB → 422 (PATCH) | API/HTTP | `test_patch_future_dob_rejected_422` new | ✅ 422 from Spec 02 §2 validator |
| Search by name & phone with pagination | API/HTTP | `test_search_patients_by_name_and_phone` | ✅ 200, `total >= 1`, `page == 1`, `size == 50`, `pages >= 1` — from Spec 02 §4 |
| Soft delete → 204, excluded from search | API/HTTP | `test_soft_delete_patient_sets_inactive` | ✅ 204 from R-5; `patient_id not in found_ids` independent of implementation |
| Unauthenticated → 401 | API/HTTP | `test_unauthenticated_request_rejected_401` | ✅ 401 from NFR-6 |
| GET non-existent → 404 | API/HTTP | `test_get_nonexistent_patient_returns_404` new | ✅ 404 + `PATIENT_NOT_FOUND` from Spec 02 §4/§7 |
| PATCH non-existent → 404 | API/HTTP | `test_patch_nonexistent_patient_returns_404` new | ✅ 404 + `PATIENT_NOT_FOUND` from Spec 02 §4/§7 |
| DELETE non-existent → 404 | API/HTTP | `test_delete_nonexistent_patient_returns_404` new | ✅ 404 + `PATIENT_NOT_FOUND` from Spec 02 §4/§7 |
| DENTIST write attempt → 403 | API/HTTP | `test_dentist_rejected_from_patient_write_403` new | ✅ 403 + `RBAC_FORBIDDEN` from Spec 02 §4 authz matrix |
| GET /{id} existing → 200, round-trip | API/HTTP | `test_get_patient_by_id_200` new | ✅ 200; `fullName == "Alice Smith"`, `medicalAlerts == "Diabetes"` from test's own POST |
| PATCH /{id} update → 200, round-trip | API/HTTP | `test_update_patient_200` new | ✅ 200; `fullName == "Robert Jones"`, `medicalAlerts` from test's own PATCH |

### Fixture consistency

The new `dentist_staff` fixture (conftest.py:245-262) mirrors `admin_staff` (conftest.py:205-222) and `receptionist_staff` (conftest.py:225-242) exactly: same signature (`test_session_local` + `override_dbsession`), same `hashed_password="irrelevant"` sentinel (role-check tests don't exercise password verification), same `is_active=True`, same commit/refresh pattern. ✅

---

## Summary

| Severity | Count | Findings |
|---|---|---|
| blocker | 0 | — |
| major | 0 | — |
| minor | 0 | — |
| nit | 0 | — |

Round 1 had 1 major + 4 minors + 1 nit. **All 6 fully resolved.** The fix commit (`58792d1`) adds 7 tests targeting every round-1 gap:

- **Major (resolved):** `test_get_nonexistent_patient_returns_404`, `test_patch_nonexistent_patient_returns_404`, `test_delete_nonexistent_patient_returns_404` — all three 404 paths at the API seam, asserting `404` + `body["error"] == "PATIENT_NOT_FOUND"`. These verify the full chain: handler → `PatientService.get`/`update`/`soft_delete` → `PatientNotFoundError` → `domain_error_handler` → `404`.
- **Minor (4, all addressed):** `test_dentist_rejected_from_patient_write_403` (DENTIST 403 on POST/PATCH/DELETE), `test_get_patient_by_id_200` (GET 200 happy path), `test_update_patient_200` (PATCH 200 happy path), spec footnote ¹ documenting `get_current_user` guard pattern.
- **Nit (resolved):** `test_patch_future_dob_rejected_422` (PATCH 422 at API seam).

All 4 quality gates green: ruff ✓, ruff format ✓, mypy ✓ (25 source files, 0 issues), pytest 47 passed (7 new tests, up from 40).

**Single worst issue from round 1 (the major — untested 404 paths for `PatientNotFoundError`) is now resolved with three API tests at the HTTP seam that verify the full wiring chain.**

**Verdict: Approve** — no blockers, no majors, no minors, no nits. The ticket is ready to be marked `done`.