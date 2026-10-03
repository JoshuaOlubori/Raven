---
id: T-003
title: Staff management and RBAC route guards
status: todo
mode: AFK
blocked_by: T-002
spec_refs: specs/01-auth-staff.md#3-layer-2, specs/01-auth-staff.md#4-layer-3
covers: R-2, NFR-6
updated: 2026-10-03
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
- [ ] Given an Admin user, When `POST /api/v1/staff` is submitted with valid data, Then a new staff account is created with `201 Created` and password hash excluded from response (R-2).
- [ ] Given a non-Admin user (`RECEPTIONIST` or `DENTIST`), When attempting `POST /api/v1/staff`, Then the system rejects the request with `403 Forbidden`.
- [ ] Given an attempt to register an email already in use, When `POST /api/v1/staff` is submitted, Then it returns `409 Conflict` with error code `STAFF_EMAIL_EXISTS`.
- [ ] Given an Admin or Receptionist, When querying `GET /api/v1/staff?role=DENTIST`, Then all matching staff accounts are returned.
- [ ] Given an Admin, When `PATCH /api/v1/staff/{id}` is submitted with `is_active=False`, Then the staff member's active status is updated to false.

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | `test_admin_creates_staff_success_201` | API + Admin auth | status 201, role == "DENTIST", "hashed_password" not in body | PRD R-2 |
| 2 | `test_receptionist_creating_staff_returns_403` | API + Receptionist auth | status 403, detail contains "Insufficient role" | PRD R-2 |
| 3 | `test_create_duplicate_email_returns_409` | API + Admin auth | status 409, error == "STAFF_EMAIL_EXISTS" | Spec 01 §7 |
| 4 | `test_list_staff_filters_by_role` | API + Receptionist auth | status 200, all returned items have requested role | Spec 01 §4 |
| 5 | `test_admin_deactivates_staff_member` | API + Admin auth | status 200, `body["isActive"] is False` | Spec 01 §4 |

## Out of scope
Patient records, services, and appointment schedules.

## Notes for the implementer
Ensure `require_roles` uses `set(allowed) & set(user.roles)` logic. Use camelCase JSON aliases for all output schemas (`isActive`, `fullName`).

## Implementation log

## Review history
