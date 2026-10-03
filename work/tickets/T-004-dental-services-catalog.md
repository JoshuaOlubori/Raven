---
id: T-004
title: Dental services catalog management
status: todo
mode: AFK
blocked_by: T-003
spec_refs: specs/03-services.md#2-layer-1, specs/03-services.md#3-layer-2, specs/03-services.md#4-layer-3
covers: R-6
updated: 2026-10-03
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
- [ ] Given an Admin user, When `POST /api/v1/services` is submitted with valid name and positive `duration_minutes` (e.g. 45), Then it returns `201 Created` with the saved service (R-6).
- [ ] Given a non-Admin user, When attempting to create or edit a dental service, Then the system returns `403 Forbidden`.
- [ ] Given a service creation payload with duration <= 0 or > 480 minutes, When submitted, Then the system rejects it with `422 Unprocessable Entity`.
- [ ] Given a duplicate service name, When creation is attempted, Then the system returns `409 Conflict` with error code `SERVICE_NAME_EXISTS`.
- [ ] Given an active service, When an Admin updates it to `is_active = false`, Then subsequent list queries with `active_only=True` omit it.

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

## Review history
