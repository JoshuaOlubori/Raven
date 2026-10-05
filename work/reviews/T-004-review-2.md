# Review T-004 round 2 — Approve

Gates: ruff ✓ · ruff format ✓ · mypy ✓ · pytest ✓ (33 passed)

Verified against: `work/specs/03-services.md` (§2 Layer 1 Contracts, §3 Layer 2 Persistence/Repository, §4 Layer 3 Wiring/Endpoints, §7 Errors), `work/specs/00-architecture.md` (§4 Global Error Model, §5 AuthN/AuthZ, §6 Quality Gates), PRD `R-6` (CONTEXT.md glossary, prd.md §4.3), `docs/adr/0001`, `docs/adr/0002`, Standard `fastapi-production-architecture` (§2 Naming, §3 Layered smell checklist, §4 Transactions, §5 DI).

Diff reviewed: `git diff d7adef5..25ba105` (commit `25ba105` on top of round-1 baseline `d7adef5`). The fix commit contains **only test additions** — no implementation code changed. The round-1 implementation was correct; only test coverage was missing.

---

## Spec

All six round-1 findings fully resolved. Every acceptance criterion now has full coverage at the specified seam, and the Spec 03 §4 endpoint error-code matrix is fully exercised.

### Acceptance criteria — round 2 status

| AC | Spec requirement (quoted from ticket) | Test(s) | Verdict |
|---|---|---|---|
| AC1 | *"Given an Admin user, When `POST /api/v1/services` is submitted with valid name and positive `duration_minutes` (e.g. 45), Then it returns `201 Created` with the saved service (R-6)."* | `test_admin_creates_dental_service_201` — asserts 201, `body["durationMinutes"] == 45`, `body["isActive"] is True`. | ✅ Met (unchanged from round 1). |
| AC2 | *"Given a non-Admin user, When attempting to create **or edit** a dental service, Then the system returns `403 Forbidden`."* | `test_non_admin_cannot_create_service_403` (RECEPTIONIST → POST 403) ✅ · `test_non_admin_cannot_edit_service_403` (RECEPTIONIST → PATCH 403) ✅ new · `test_dentist_cannot_create_service_403` (DENTIST → POST 403) ✅ new. | ✅ **Fully met** — both "create" and "edit" sub-cases covered for both RECEPTIONIST and DENTIST roles. |
| AC3 | *"Given a service creation payload with duration <= 0 or > 480 minutes, When submitted, Then the system rejects it with `422 Unprocessable Entity`."* | `test_invalid_duration_rejected_422` — tests 0 (rejected) ✅, -15 (rejected) ✅, 481 (rejected) ✅ new, 480 (accepted boundary) ✅ new. | ✅ **Fully met** — both bounds (<=0 and >480) tested at schema unit seam. |
| AC4 | *"Given a duplicate service name, When creation is attempted, Then the system returns `409 Conflict` with error code `SERVICE_NAME_EXISTS`."* | `test_duplicate_service_name_returns_409` — first POST → 201, second POST → 409, `body["error"] == "SERVICE_NAME_EXISTS"`. | ✅ Met (unchanged from round 1). |
| AC5 | *"Given an active service, When an Admin updates it to `is_active = false`, Then subsequent list queries with `active_only=True` omit it."* | `test_list_services_active_filter` — PATCH `{"isActive": False}` → 200 + `isActive is False`, then GET list `active_only=True` → asserts deactivated service excluded + all remaining `isActive is True`. | ✅ Met (unchanged from round 1). |

### Spec 03 §4 endpoint error-code matrix — round 2 coverage

| Endpoint | 200 | 401 | 403 | 404 | 409 | 422 |
|---|---|---|---|---|---|---|
| POST /services | test 1 (201) | inherited (`get_current_user` / `require_roles`) | `test_non_admin_cannot_create_service_403` ✅ + `test_dentist_cannot_create_service_403` ✅ | — | `test_duplicate_service_name_returns_409` ✅ | `test_invalid_duration_rejected_422` (schema unit) ✅ |
| GET /services | `test_list_services_active_filter` (200) ✅ | inherited | — | — | — | — |
| GET /services/{id} | `test_get_service_by_id_200` ✅ new | inherited | — | `test_get_nonexistent_service_returns_404` ✅ new | — | — |
| PATCH /services/{id} | `test_list_services_active_filter` (200) ✅ | inherited | `test_non_admin_cannot_edit_service_403` ✅ new | `test_patch_nonexistent_service_returns_404` ✅ new | `test_patch_duplicate_name_returns_409` ✅ new | — |

**Verification notes for new 404 tests:**

- `test_get_nonexistent_service_returns_404` — uses `admin_staff` (passes `require_roles("ADMIN")`), GETs a random `uuid.uuid4()`. Trace: `get_service_endpoint` → `catalog.get(random_uuid)` → `get_service_by_id` returns `None` → `ServiceNotFoundError` raised → `domain_error_handler` maps to `404` + `body["error"] == "SERVICE_NOT_FOUND"`. ✅ Verified against `service_catalog.py:56-64` and `main.py:60-77`.

- `test_patch_nonexistent_service_returns_404` — uses `admin_staff` (passes RBAC), PATCHes a random `uuid.uuid4()` with `{"isActive": False}`. Trace: `require_roles("ADMIN")` passes at route-level dependency → handler calls `catalog.update(random_uuid, is_active=False)` → `self.get(random_uuid)` (service_catalog.py:76) → `ServiceNotFoundError` → 404. The 404 raises **before** the name-uniqueness check (service_catalog.py:77-82) is reached, which is correct ordering. ✅

**Verification notes for new 403 tests:**

- `test_non_admin_cannot_edit_service_403` — uses `receptionist_staff`, PATCHes `uuid.uuid4()` (random UUID — service_id is irrelevant because RBAC fires first). Trace: `require_roles("ADMIN")` (route-level dependency, routers/services.py:90) runs before the handler → `role_guard` (auth.py:96-99) sees `RECEPTIONIST not in ("ADMIN",)` → raises `ForbiddenError` → `domain_error_handler` maps to 403 + `RBAC_FORBIDDEN`. ✅ The 403 correctly short-circuits before any existence check.

- `test_dentist_cannot_create_service_403` — uses new `dentist_staff` fixture, POSTs to create. Trace: `require_roles("ADMIN")` (routers/services.py:41) → `role_guard` sees `DENTIST not in ("ADMIN",)` → 403 `RBAC_FORBIDDEN`. ✅

**Verification notes for new 409 test:**

- `test_patch_duplicate_name_returns_409` — creates "Root Canal" and "Bridge", then PATCHes "Bridge"'s ID with `{"name": "Root Canal"}`. Trace: RBAC passes (admin) → handler calls `catalog.update(bridge_id, name="Root Canal")` → `self.get(bridge_id)` returns "Bridge" (exists) → `name in kwargs` → `"Root Canal" != "Bridge"` → `get_service_by_name("Root Canal")` finds existing → `ServiceNameExistsError` → 409 `SERVICE_NAME_EXISTS`. ✅ Verified against `service_catalog.py:70-83`.

### Scope

**No scope creep.** The diff adds exactly 6 tests and 1 fixture — all directly addressing round-1 findings. No new production code, no new dependencies, no endpoint or behaviour changes. ✅

### Silent deviations

None. The implementation is unchanged from round 1 (which had zero silent deviations). The test additions match the spec's test seams exactly (API/HTTP seam for endpoints, schema unit for `ServiceDuration`). ✅

---

## Standards

The diff is test-only, so implementation-layer standards from round 1 remain clean. The new test code itself is reviewed against the same checklist:

- ✅ **Layer 3 — Handlers build services inline:** N/A (no handler changes). Existing handlers consume `ServiceCatalogDep` (services.py:45, 62, 80, 95) — no inline service construction. Unchanged.
- ✅ **Layer 3 — Scattered `if user.role`:** N/A (no auth changes). RBAC centralized in `require_roles("ADMIN")` as route-level `dependencies=[...]` (services.py:41, 90). Unchanged.
- ✅ **Layer 1 — Business rules in handlers:** N/A (no new business logic). All rules remain in `ServiceCatalog` (service_catalog.py). Unchanged.
- ✅ **Layer 1 — v1 idioms:** N/A (no model code changed). Test code uses `model_validate`/`model_dump` patterns inherited from the codebase. ✅
- ✅ **Layer 2 — per-row queries / missing eager loading:** N/A (no repository changes). ✅
- ✅ **Layer 4 — blocking work on event loop:** N/A (no production code changed). All test code is `async` with `await` on the async client. ✅
- ✅ **Layer 5 — module-level mutable state:** N/A. The only new module-level entity is the `dentist_staff` fixture in conftest.py — a standard pytest fixture, not mutable state. ✅
- ✅ **Naming conforms to §2:** Test names follow `test_<action>_<expected>` convention. The `dentist_staff` fixture mirrors the established `admin_staff`/`receptionist_staff` naming pattern exactly (same structure, same docstring style, same `hashed_password="irrelevant"` sentinel). ✅
- ✅ **Correlation ID / structured logging:** N/A (no endpoint changes). The global `domain_error_handler` already includes `correlation_id` in error responses (main.py:72-76). ✅
- ✅ **Secrets / config inline:** None. Fixtures use `hashed_password="irrelevant"` for role-only tests (no real auth flow needed). ✅

Fowler baseline — no new smells in the test diff:

- ✅ **No Duplicated Code:** The `dentist_staff` fixture mirrors `admin_staff`/`receptionist_staff` — this is the established codebase pattern for role-based staff fixtures (Architecture §5 test strategy). It is intentional and consistent, not a new smell.
- ✅ **No other Fowler smells:** No Mysterious Name, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man, or Refused Bequest observed.

### Nit

- **PATCH 422 (invalid duration) not tested at the API seam** (Spec 03 §4 lists 422 for PATCH). The `ServiceUpdate.duration_minutes` field uses the same `ServiceDuration` constrained type as `ServiceCreate` (schemas.py:146-148), and the schema unit test (`test_invalid_duration_rejected_422`) validates `ServiceDuration` rejects 0, -15, and 481. FastAPI validates the request body against `ServiceUpdate` before the handler executes, so the 422 behavior for PATCH is structurally identical to POST and covered by the shared type test. **Recommendation (optional):** add `test_patch_invalid_duration_rejected_422` for API-seam parity with POST, asserting that a PATCH body with `"durationMinutes": 481` returns 422. This is low-priority — the validation path is shared and already tested at the schema level.

---

## Tests

Every round-1 test-coverage gap is closed. All new tests drive the public HTTP seam (`httpx.AsyncClient` over `ASGITransport`) or the named schema unit seam — none poke at private structure.

### Test seam matrix — full coverage

| Behaviour (Spec location) | Seam | Test | Independent expected values? |
|---|---|---|---|
| Admin POST → 201, duration 45, active | API/HTTP | `test_admin_creates_dental_service_201` | ✅ 45 is the test's own input; `isActive is True` is the schema default from Spec 03 §2. |
| Non-admin (RECEPTIONIST) POST → 403 | API/HTTP | `test_non_admin_cannot_create_service_403` | ✅ 403 + `RBAC_FORBIDDEN` + `"Insufficient role"` from Spec 03 §4 / §7. |
| Non-admin (RECEPTIONIST) PATCH → 403 | API/HTTP | `test_non_admin_cannot_edit_service_403` ✅ new | ✅ 403 + `RBAC_FORBIDDEN` + `"Insufficient role"` from Spec 03 §4. |
| DENTIST POST → 403 (AC2 non-Admin sub-case) | API/HTTP | `test_dentist_cannot_create_service_403` ✅ new | ✅ 403 + `RBAC_FORBIDDEN` + `"Insufficient role"` from Spec 03 §4/§5. |
| Duration 0, -15 rejected | Schema unit | `test_invalid_duration_rejected_422` | ✅ `ValidationError` raised by `ServiceDuration = Field(gt=0)` (Spec 03 §2). |
| Duration 481 rejected, 480 accepted | Schema unit | `test_invalid_duration_rejected_422` ✅ extended | ✅ 481 rejected (`le=480`), 480 accepted — boundary from Spec 03 §2. |
| Duplicate name → 409 | API/HTTP | `test_duplicate_service_name_returns_409` | ✅ 409 + `SERVICE_NAME_EXISTS` from Spec 03 §7. |
| Deactivate → excluded from active-only list | API/HTTP | `test_list_services_active_filter` | ✅ 200 + `service_id not in ids` + `all(isActive is True)` — assertions independent of implementation. |
| GET /{id} non-existent → 404 | API/HTTP | `test_get_nonexistent_service_returns_404` ✅ new | ✅ 404 + `SERVICE_NOT_FOUND` from Spec 03 §4/§7. |
| PATCH /{id} non-existent → 404 | API/HTTP | `test_patch_nonexistent_service_returns_404` ✅ new | ✅ 404 + `SERVICE_NOT_FOUND` from Spec 03 §4/§7. |
| GET /{id} existing → 200, field round-trip | API/HTTP | `test_get_service_by_id_200` ✅ new | ✅ 200; `name`, `durationMinutes`, `isActive` from the test's own POST payload — round-trip at the HTTP seam catches serialization/alias/persistence bugs. |
| PATCH rename to existing name → 409 | API/HTTP | `test_patch_duplicate_name_returns_409` ✅ new | ✅ 409 + `SERVICE_NAME_EXISTS` from Spec 03 §7. |

### Test quality checks

- ✅ **Every acceptance criterion has a test at the named seam.** AC1 (API/HTTP), AC2 (API/HTTP — both POST and PATCH sub-cases, both RECEPTIONIST and DENTIST), AC3 (schema unit), AC4 (API/HTTP), AC5 (API/HTTP). All seams from the ticket's test plan (§Test plan) are present, plus all error-code paths from Spec 03 §4.
- ✅ **Expected values are independent of implementation — no tautological assertions.** All expected status codes and error codes come from Spec 03 §4/§7 and PRD R-6. Duration/1 values come from the test's own input (round-trip, not recomputation). No assertion duplicates the code-under-test's logic.
- ✅ **Tests assert behaviour, not private structure.** All 10 API tests drive `httpx.AsyncClient` over `ASGITransport(app=app)` — the public HTTP seam. The schema unit test targets `ServiceDuration` via `ServiceCreate` at its named seam. No private-method calls.
- ✅ **Failure paths exist for spec'd errors:** 403 ✅ (POST + PATCH + DENTIST), 404 ✅ (GET + PATCH), 409 ✅ (POST + PATCH), 422 ✅ (schema unit, shared type). 401 is inherited infrastructure (`get_current_user` from T-002/T-003, tested in T-002).
- ✅ **No sleeps, order dependence, or shared-mutable fixtures.** All new fixtures are function-scoped. The `dentist_staff` fixture uses UUID-based unique emails (`f"dentist-{uuid.uuid4().hex[:8]}@clinic.com"`), mirroring `admin_staff`/`receptionist_staff`. Service names are unique per test (`"Root Canal"`, `"Bridge"`, `"Consultation"`, `"Routine Cleaning"`, etc.). No cross-test ordering assumptions.

### Fixture consistency

The new `dentist_staff` fixture (conftest.py:245-262) mirrors `admin_staff` and `receptionist_staff` exactly: same signature (`test_session_local` + `override_dbsession`), same `hashed_password="irrelevant"` sentinel (role-check tests don't exercise password verification), same `is_active=True`, same commit/refresh pattern. ✅

---

## Summary

| Severity | Count | Findings |
|---|---|---|
| blocker | 0 | — |
| major | 0 | — |
| minor | 0 | — |
| nit | 1 | PATCH 422 (invalid duration) not tested at API seam — structurally covered by shared `ServiceDuration` schema type and schema unit test. Optional follow-up. |

**Round 1 had 1 major + 5 minors. All 6 fully resolved.** The fix commit (`25ba105`) adds 6 tests + 1 fixture targeting every round-1 gap:

- **Major (required, resolved):** `test_get_nonexistent_service_returns_404` and `test_patch_nonexistent_service_returns_404` — both 404 paths at the API seam, asserting `SERVICE_NOT_FOUND`.
- **Minor (5, all addressed):** `test_get_service_by_id_200` (GET 200), `test_non_admin_cannot_edit_service_403` (PATCH 403), `test_dentist_cannot_create_service_403` (DENTIST 403), `test_patch_duplicate_name_returns_409` (PATCH 409), extended `test_invalid_duration_rejected_422` (upper bound 481/480), `dentist_staff` fixture.

All 4 quality gates green: ruff ✓, ruff format ✓, mypy ✓, pytest 33 passed (6 new tests + 1 extended + 1 fixture = 33 total, up from 27).

**Single worst issue from round 1 (the major — untested 404 paths for `ServiceNotFoundError`) is now resolved with two API tests at the http seam that verify the full chain: handler → `ServiceCatalog.get`/`update` → `ServiceNotFoundError` → `domain_error_handler` → `404` + `SERVICE_NOT_FOUND`.**

**Verdict: Approve** — no blockers, no majors, no minors remaining; one optional nit for follow-up.
