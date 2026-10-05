---
id: T-003
title: Staff management and RBAC route guards
status: done
mode: AFK
blocked_by: T-002
spec_refs: specs/01-auth-staff.md#3-layer-2, specs/01-auth-staff.md#4-layer-3
covers: R-2, NFR-6
updated: 2026-10-05
---

## Outcome
Admins can create, list, inspect, and update clinic staff accounts (`ADMIN`, `RECEPTIONIST`, `DENTIST`), protected by reusable role-based dependency guards (`require_roles`).

## What to build
- `src/app/api/auth.py`: `require_roles(*roles: str)` closure-based dependency factory returning an async guard raising `403 Forbidden` if the user role is not authorized.
- `src/app/db/repository.py`: Staff query functions (`create_staff`, `list_staff`, `get_staff_by_id`, `update_staff`).
- `src/app/routers/staff.py`:
  - `POST /api/v1/staff` (Admin only)
  - `GET /api/v1/staff` (Admin, Receptionist)
  - `GET /api/v1/staff/{staff_id}` (Admin, Receptionist)
  - `PATCH /api/v1/staff/{staff_id}` (Admin only)

## Acceptance criteria
- [x] Given an Admin user, When `POST /api/v1/staff` is submitted with valid data, Then a new staff account is created with `201 Created` and password hash excluded from response (R-2). — `test_admin_creates_staff_success_201` ✓
- [x] Given a non-Admin user (`RECEPTIONIST` or `DENTIST`), When attempting `POST /api/v1/staff`, Then the system rejects the request with `403 Forbidden`. — `test_receptionist_creating_staff_returns_403` ✓, `test_dentist_creating_staff_returns_403` ✓
- [x] Given an attempt to register an email already in use, When `POST /api/v1/staff` is submitted, Then it returns `409 Conflict` with error code `STAFF_EMAIL_EXISTS`. — `test_create_duplicate_email_returns_409` ✓
- [x] Given an Admin or Receptionist, When querying `GET /api/v1/staff?role=DENTIST`, Then all matching staff accounts are returned. — `test_list_staff_filters_by_role` ✓
- [x] Given an Admin, When `PATCH /api/v1/staff/{id}` is submitted with `is_active=False`, Then the staff member's active status is updated to false. — `test_admin_deactivates_staff_member` ✓

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | `test_admin_creates_staff_success_201` | API + Admin auth | status 201, role == "DENTIST", "hashed_password" not in body | PRD R-2 |
| 2 | `test_receptionist_creating_staff_returns_403` | API + Receptionist auth | status 403, body["error"] == "RBAC_FORBIDDEN", "Insufficient role" in message | PRD R-2 |
| 3 | `test_create_duplicate_email_returns_409` | API + Admin auth | status 409, error == "STAFF_EMAIL_EXISTS" | Spec 01 §7 |
| 4 | `test_list_staff_filters_by_role` | API + Receptionist auth | status 200, non-empty, DENTIST fixture in results, all items have requested role | Spec 01 §4 |
| 5 | `test_admin_deactivates_staff_member` | API + Admin auth | status 200, `body["isActive"] is False` | Spec 01 §4 |
| 6 | `test_get_nonexistent_staff_returns_404` | API + Admin auth | status 404, error == "STAFF_NOT_FOUND" | Spec 01 §4, §7 |
| 7 | `test_patch_nonexistent_staff_returns_404` | API + Admin auth | status 404, error == "STAFF_NOT_FOUND" | Spec 01 §4, §7 |
| 8 | `test_dentist_creating_staff_returns_403` | API + Dentist auth | status 403, body["error"] == "RBAC_FORBIDDEN" | PRD R-2 |
| 9 | `test_staff_endpoint_without_auth_returns_401` | API (no auth) | status 401 | Spec 01 §4 |
| 10 | `test_staff_endpoint_without_auth_returns_401_on_patch` | API (no auth) | status 401 | Spec 01 §4 |

## Out of scope
Patient records, services, and appointment schedules.

## Notes for the implementer
Ensure `require_roles` uses `set(allowed) & set(user.roles)` logic. Use camelCase JSON aliases for all output schemas (`isActive`, `fullName`).

## Implementation log

### What was built
Staff management endpoints with RBAC guards (`src/backend/src/app/`):
- `backend/src/app/exceptions.py` (new): `DomainError` base class with `error_code`/`message`/`status_code` attributes, plus `EmailAlreadyExistsError` (409, STAFF_EMAIL_EXISTS), `StaffNotFoundError` (404, STAFF_NOT_FOUND), and `ForbiddenError` (403, RBAC_FORBIDDEN).
- `backend/src/app/services/auth_service.py` (modified): `AuthError` now inherits from `DomainError` so all domain exceptions are caught by a single handler in `main.py`.
- `backend/src/app/schemas.py` (modified): Added `StaffCreate` (email, password, fullName, role) and `StaffUpdate` (full_name, role, is_active — all optional) with camelCase aliases and `populate_by_name=True`.
- `backend/src/app/db/repository.py` (modified): Added `create_staff`, `list_staff` (with role + active_only filters), and `update_staff` (generic `**kwargs` setter) per Spec 01 §3 Layer 2 signatures.
- `backend/src/app/api/auth.py` (modified): Added `require_roles(*roles)` closure-based dependency factory that raises `ForbiddenError` (403) when `current_user.role not in roles`.
- `backend/src/app/routers/staff.py` (new): `POST /api/v1/staff/` (Admin), `GET /api/v1/staff/` (Admin, Receptionist), `GET /api/v1/staff/{id}` (Admin, Receptionist), `PATCH /api/v1/staff/{id}` (Admin). Handlers are thin — delegate to repository and `AuthService` for password hashing.
- `backend/src/app/main.py` (modified): Replaced `AuthError` handler with `DomainError` handler (covers all domain exceptions); mounted `staff_router`.
- `backend/tests/conftest.py` (modified): Added `admin_staff` and `receptionist_staff` fixtures.
- `backend/tests/api/test_staff.py` (new): 5 tests covering all ACs.

### Decisions / Notes
- `require_roles` raises `ForbiddenError(DomainError)` (403, error code `RBAC_FORBIDDEN`) rather than bare `HTTPException`, so the response uses the standardized error body `{"error": ..., "message": ..., "correlation_id": ...}` per Architecture §4. This standardizes the **403** RBAC path. (Note: the **401** token-verification path in `get_current_user` still uses bare `HTTPException` — a pre-existing T-002 nit left as-is per review guidance.)
- `_staff_read` helper in `routers/staff.py` projects `Staff` ORM objects to `StaffRead` via dict construction (matching the pattern in `routers/auth.py`); `hashed_password` is never included in the response.
- `list_staff` defaults to `active_only=True` per Spec 01 §3; the GET list endpoint delegates to it with no override.
- PATCH uses `model_dump(exclude_unset=True)` to build partial updates; field names (snake_case) match `Staff` model attributes.
- `get_staff_by_id` and `get_staff_by_email` were already present from T-002; only `create_staff`, `list_staff`, `update_staff` were added.
- The implementer note about `set(allowed) & set(user.roles)` was not applicable — `CurrentUser.role` is a single string, not a list; the guard checks `current_user.role in roles` (membership test), which is correct for single-role RBAC.

### Deviations
None. The spec was complete and unambiguous for all 4 endpoints + `require_roles`.

### Commands run (original build)
`uv run --directory backend ruff check` ✓ · `uv run --directory backend ruff format --check` ✓ · `uv run --directory backend mypy src` ✓ · `uv run --directory backend pytest -q` ✓ (17 passed)

Commit: `d3da075` — T-003: Staff management and RBAC route guards

### Changes-requested fixes (review round 1)
Added 5 tests to `backend/tests/api/test_staff.py` addressing all review findings:
- `test_get_nonexistent_staff_returns_404` — MAJOR: 404 path for `GET /api/v1/staff/{id}` (StaffNotFoundError → 404, STAFF_NOT_FOUND). Spec 01 §4/§7 lists 404 for this endpoint; zero coverage previously.
- `test_patch_nonexistent_staff_returns_404` — MAJOR: 404 path for `PATCH /api/v1/staff/{id}` (StaffNotFoundError → 404, STAFF_NOT_FOUND). Same code path as GET; both guards tested.
- `test_dentist_creating_staff_returns_403` — MINOR: AC2 DENTIST sub-case (AC names "RECEPTIONIST **or** DENTIST"; only RECEPTIONIST was tested).
- `test_staff_endpoint_without_auth_returns_401` — MINOR: unauthenticated GET to staff endpoint → 401 (HTTPBearer auto-rejection). Spec 01 §4 lists 401 for all staff endpoints.
- `test_staff_endpoint_without_auth_returns_401_on_patch` — MINOR: unauthenticated PATCH to staff endpoint → 401.
- Strengthened `test_list_staff_filters_by_role` assertion: added `len(body) >= 1` and `dentist_staff.id in returned IDs` to eliminate the vacuous-pass gap (the old `for` loop passed trivially on empty lists).

All tests driven through the HTTP seam (`AsyncClient` over `ASGITransport`) with expected values from Spec 01 §4/§7 and PRD R-2. No implementation code changes required — the `StaffNotFoundError` guards and `require_roles` RBAC guard already existed; only the missing tests were added.

### Commands run (changes-requested fixes)
`uv run --directory backend ruff check` ✓ · `uv run --directory backend ruff format --check` ✓ · `uv run --directory backend mypy src` ✓ · `uv run --directory backend pytest -q` ✓ (22 passed)

## Review history
- [Review T-003 — pending] — completed and approved on changes-requested fixes.
- [Review T-003 round 1 — Changes requested](reviews/T-003-review-1.md): 0B/1M/3m/4n. All findings addressed: 404 tests (major), 401 test, DENTIST sub-case, weak assertion fix. Nits left as-is per reviewer guidance (non-standardized 401 HTTPException body, stale AuthError docstring, duplicated fetch-or-404, pre-existing code patterns).
- [Review T-003 round 2 — Approved](reviews/T-003-review-2.md): 0B/0M/1m/3n. All round-1 blockers and majors addressed (tests only, no implementation changes). One optional minor noted (missing GET /{id} 200 happy-path test). Nits carried forward (stale AuthError docstring, duplicated fetch-or-404, non-standardized 401 body — T-002 carryover).
