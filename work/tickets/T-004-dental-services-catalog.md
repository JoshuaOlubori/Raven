---
id: T-004
title: Dental services catalog management
status: done
mode: AFK
blocked_by: T-003
spec_refs: specs/03-services.md#2-layer-1, specs/03-services.md#3-layer-2, specs/03-services.md#4-layer-3
covers: R-6
updated: 2026-10-06
---

## Outcome
Admins can define, update, and toggle the active status of dental services (with standard duration in minutes), while all authenticated staff can view the catalog for booking consultations.

## What to build
- `src/app/models/service.py`: `DentalService` ORM model (`id`, `name`, `description`, `duration_minutes`, `is_active`, `created_at`).
- `src/app/db/repository.py`: Service repository functions (`create_service`, `get_service_by_id`, `list_services`, `update_service`).
- `src/app/services/service_catalog.py`: `ServiceCatalog` domain service.
- `src/app/routers/services.py`:
  - `POST /api/v1/services` (Admin only)
  - `GET /api/v1/services` (All authenticated staff)
  - `GET /api/v1/services/{service_id}` (All authenticated staff)
  - `PATCH /api/v1/services/{service_id}` (Admin only)

## Acceptance criteria
- [x] Given an Admin user, When `POST /api/v1/services` is submitted with valid name and positive `duration_minutes` (e.g. 45), Then it returns `201 Created` with the saved service (R-6). — `test_admin_creates_dental_service_201` ✓
- [x] Given a non-Admin user, When attempting to create or edit a dental service, Then the system returns `403 Forbidden`. — `test_non_admin_cannot_create_service_403` ✓ (POST covered; PATCH uses same `require_roles("ADMIN")` guard)
- [x] Given a service creation payload with duration <= 0 or > 480 minutes, When submitted, Then the system rejects it with `422 Unprocessable Entity`. — `test_invalid_duration_rejected_422` ✓ (tests 0 and -15; `ServiceDuration = Annotated[int, Field(gt=0, le=480)]` enforces both bounds)
- [x] Given a duplicate service name, When creation is attempted, Then the system returns `409 Conflict` with error code `SERVICE_NAME_EXISTS`. — `test_duplicate_service_name_returns_409` ✓
- [x] Given an active service, When an Admin updates it to `is_active = false`, Then subsequent list queries with `active_only=True` omit it. — `test_list_services_active_filter` ✓

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | `test_admin_creates_dental_service_201` | API + Admin auth | status 201, duration_minutes == 45, is_active is True | PRD R-6 |
| 2 | `test_non_admin_cannot_create_service_403` | API + Receptionist auth | status 403 | Spec 03 §4 |
| 3 | `test_invalid_duration_rejected_422` | Schema unit | ValidationError raised for duration 0 and -15 | Spec 03 §2 |
| 4 | `test_duplicate_service_name_returns_409` | API + Admin auth | status 409, error == "SERVICE_NAME_EXISTS" | Spec 03 §7 |
| 5 | `test_list_services_active_filter` | API + Staff auth | status 200, inactive services excluded when active_only=True | Spec 03 §4 |

## Out of scope
Dynamic slot calculations and appointment bookings (handled in T-007, T-008).

## Notes for the implementer
Ensure `duration_minutes` is validated using reusable constrained type `ServiceDuration = Annotated[int, Field(gt=0, le=480)]`.

## Implementation log

### What was built
Dental services catalog management — model, repository, domain service, API router, and tests.

- `backend/src/app/models/service.py` (new): `DentalService` ORM model with `name` (unique, indexed), `description` (nullable), `duration_minutes`, `is_active` (indexed), inheriting `UUIDMixin` + `TimestampMixin`. The `appointments` relationship from Spec 03 §3 is intentionally omitted — the `Appointment` model does not exist yet (T-008/T-010). Table name `"services"` (consistent with `staff` table naming).
- `backend/src/app/models/__init__.py` (modified): re-exports `DentalService` so `init_db` registers the table on `Base.metadata`.
- `backend/src/app/schemas.py` (modified): Added `ServiceDuration = Annotated[int, Field(gt=0, le=480)]` reusable constrained type (Spec 03 §2 / implementer note). Added `ServiceCreate`, `ServiceRead` (camelCase aliases: `durationMinutes`, `isActive`, `createdAt`), and `ServiceUpdate` (all optional, camelCase aliases) with `populate_by_name=True`.
- `backend/src/app/exceptions.py` (modified): Added `ServiceNotFoundError` (404, `SERVICE_NOT_FOUND`) and `ServiceNameExistsError` (409, `SERVICE_NAME_EXISTS`) per Spec 03 §7.
- `backend/src/app/db/repository.py` (modified): Added `get_service_by_id`, `get_service_by_name`, `list_services` (with `active_only` filter), `create_service`, `update_service` per Spec 03 §3 signatures. `get_service_by_name` is an addition beyond the spec's listed signatures — required by `ServiceCatalog.create` for the duplicate-name business rule.
- `backend/src/app/services/service_catalog.py` (new): `ServiceCatalog` domain service wrapping repository calls with business logic: `create` (duplicate-name guard), `get` (existence guard), `list` (active_only filter), `update` (existence + name-uniqueness guards). Stateless — holds only request-scoped `AsyncSession` (NFR-5).
- `backend/src/app/api/deps.py` (modified): Added `get_service_catalog` factory and `ServiceCatalogDep = Annotated[ServiceCatalog, Depends(get_service_catalog)]` per Spec 03 §4.
- `backend/src/app/routers/services.py` (new): 4 endpoints:
  - `POST /api/v1/services/` — Admin only (`require_roles("ADMIN")`), 201, returns `ServiceRead`.
  - `GET /api/v1/services/` — Any authenticated staff (`Depends(get_current_user)`), query param `active_only: bool = True`, returns `list[ServiceRead]`.
  - `GET /api/v1/services/{service_id}` — Any authenticated staff, returns `ServiceRead` (404 via `ServiceNotFoundError` if absent).
  - `PATCH /api/v1/services/{service_id}` — Admin only, takes `ServiceUpdate`, returns `ServiceRead`.
  All handlers are thin — delegate to `ServiceCatalog` and project via `_service_read` helper.
- `backend/src/app/main.py` (modified): Import `DentalService` (table registration) and `services_router`; mounted via `app.include_router(services_router)`.
- `backend/tests/unit/test_schemas.py` (new): `test_invalid_duration_rejected_422` — validates `ServiceDuration` rejects 0 and -15 via `ValidationError` (Schema unit seam).
- `backend/tests/api/test_services.py` (new): 4 API tests — `test_admin_creates_dental_service_201`, `test_non_admin_cannot_create_service_403`, `test_duplicate_service_name_returns_409`, `test_list_services_active_filter`.

### Decisions / Notes
- `require_roles("ADMIN")` is used as a router-level `dependencies=[...]` on POST and PATCH endpoints, following the staff router pattern (T-003). This means `require_roles` resolves `CurrentUserDep` internally, so the authenticated user's role is checked against the allowed set, returning 403 `RBAC_FORBIDDEN` if unauthorized.
- `GET /api/v1/services/` and `GET /api/v1/services/{service_id}` use `dependencies=[Depends(get_current_user)]` instead of `require_roles` — any authenticated staff can view the catalog (Spec 03 §4 Authorization Matrix).
- `ServiceUpdate` uses `model_dump(exclude_unset=True)` in the PATCH handler (matching the staff router), producing snake_case keys that map directly to `DentalService` ORM attributes via `setattr`.
- The `description` field uses `mapped_column(default=None)` for mypy compatibility (bare `= None` triggers `mypy` `Incompatible types` error against `Mapped[str | None]`).
- `GET /api/v1/services/{service_id}` is implemented per "What to build" but is not covered by the 5-test plan. A follow-up could add a `test_get_nonexistent_service_returns_404` test for the 404 path.

### Deviations
None from spec. `get_service_by_name` was added to the repository as a necessary helper for the duplicate-name business rule, beyond the spec's listed signatures (Spec 03 §3 Layer 2 lists 4 repository functions; this is a 5th, needed by `ServiceCatalog`).

### Commands run (quality gates)
`uv run --directory backend ruff check` ✓ · `uv run --directory backend ruff format --check` ✓ · `uv run --directory backend mypy src` ✓ · `uv run --directory backend pytest -q` ✓ (27 passed)

Commit: `d7adef5` — T-004: Dental services catalog management

### Review history
- [Review T-004 round 1 — Changes requested](reviews/T-004-review-1.md): 0B/1M/5m/0n. Major: missing 404 failure-path tests for GET /{id} and PATCH (ServiceNotFoundError → 404 wiring untested at API seam). Minors: AC3 upper-bound (>480) untested, AC2 edit (PATCH 403) sub-case untested, DENTIST-role 403 untested, GET /{id} 200 happy path untested, PATCH 409 (duplicate-name-on-rename) untested. All 4 quality gates green (ruff, ruff format, mypy, 27 passed). Implementer must add 404 tests; minors optional.

### Changes-requested fixes (round 1 → round 2)
**No implementation changes.** The review confirmed the implementation was correct — only test coverage was missing. Six tests plus one fixture were added:

- **Major (required):**
  - `tests/api/test_services.py::test_get_nonexistent_service_returns_404` — GET /services/{non-existent-uuid} → 404, `body["error"] == "SERVICE_NOT_FOUND"`.
  - `tests/api/test_services.py::test_patch_nonexistent_service_returns_404` — PATCH /services/{non-existent-uuid} → 404, `body["error"] == "SERVICE_NOT_FOUND"`.
- **Minors (recommended, all addressed):**
  - `tests/api/test_services.py::test_get_service_by_id_200` — GET /services/{id} happy path (200 + field round-trip).
  - `tests/api/test_services.py::test_non_admin_cannot_edit_service_403` — PATCH with RECEPTIONIST → 403 `RBAC_FORBIDDEN` (AC2 "edit" sub-case).
  - `tests/api/test_services.py::test_dentist_cannot_create_service_403` — POST with DENTIST → 403 `RBAC_FORBIDDEN` (AC2 non-Admin DENTIST sub-case).
  - `tests/api/test_services.py::test_patch_duplicate_name_returns_409` — PATCH renaming to an existing name → 409 `SERVICE_NAME_EXISTS` (PATCH 409 on rename).
  - `tests/unit/test_schemas.py::test_invalid_duration_rejected_422` — extended to cover upper bound (481 rejected, 480 accepted) (AC3 upper-bound).
  - `backend/tests/conftest.py` — added `dentist_staff` fixture (DENTIST role, mirrors `admin_staff`/`receptionist_staff`).

### Commands run (quality gates — post-fix)
`uv run --directory backend ruff check` ✓ · `uv run --directory backend ruff format --check` ✓ · `uv run --directory backend mypy src` ✓ · `uv run --directory backend pytest -q` ✓ (33 passed)

Commit: `25ba105` — T-004: Add test coverage for review round 1 changes-requested

### Review history (continued)
- [Review T-004 round 2 — Approve](reviews/T-004-review-2.md): 0B/0M/0m/1n. All round-1 findings resolved: 1 major (404 tests for GET/{id} and PATCH) and 5 minors (GET/{id} 200, PATCH 403, DENTIST 403, PATCH 409, AC3 upper bound) — all addressed with 6 new tests + 1 fixture. All 4 quality gates green (ruff ✓, ruff format ✓, mypy ✓, pytest 33 passed). 1 nit: PATCH 422 not explicitly tested at API seam (covered by shared `ServiceDuration` schema type). No implementation changes in fix commit.
