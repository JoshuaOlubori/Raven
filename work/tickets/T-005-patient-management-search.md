---
id: T-005
title: Patient profile management, search, and soft delete
status: in-progress
mode: AFK
blocked_by: T-003
spec_refs: specs/02-patients.md#2-layer-1, specs/02-patients.md#3-layer-2, specs/02-patients.md#4-layer-3
covers: R-3, R-4, R-5, NFR-6
updated: 2026-10-05
---

## Outcome
Receptionists and Admins can create and edit patient profiles with medical alerts, search active patients by partial name or phone number, and soft delete patients while preserving historical appointment data.

## What to build
- `src/app/models/patient.py`: `Patient` ORM model (`id`, `first_name`, `last_name`, `date_of_birth`, `phone`, `email`, `emergency_contact_name`, `emergency_contact_phone`, `medical_alerts`, `is_active`, `created_at`, `updated_at`).
- `src/app/db/repository.py`: Patient repository functions (`create_patient`, `get_patient_by_id`, `list_patients` with search filter and pagination, `update_patient`, `soft_delete_patient`).
- `src/app/services/patient_service.py`: `PatientService` orchestrating validations and soft deletions.
- `src/app/routers/patients.py`:
  - `POST /api/v1/patients` (Admin, Receptionist)
  - `GET /api/v1/patients` (All staff; search query & pagination)
  - `GET /api/v1/patients/{patient_id}` (All staff)
  - `PATCH /api/v1/patients/{patient_id}` (Admin, Receptionist)
  - `DELETE /api/v1/patients/{patient_id}` (Admin, Receptionist; soft delete)

## Acceptance criteria
- [ ] Given valid demographic data and medical alert text, When `POST /api/v1/patients` is submitted, Then it returns `201 Created` with computed `fullName` (R-3).
- [ ] Given an invalid phone format or date of birth in the future, When submitted, Then the system returns `422 Unprocessable Entity`.
- [ ] Given a search string matching first name, last name, or phone number, When querying `GET /api/v1/patients?search=smith`, Then matching active patients are returned with pagination metadata (R-4).
- [ ] Given an existing patient, When `DELETE /api/v1/patients/{id}` is executed, Then the patient is marked `is_active = false` and returns `204 No Content` (R-5).
- [ ] Given a soft-deleted patient, When querying default patient searches, Then they are excluded from the result set (R-5).

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | `test_create_patient_success_201` | API + Receptionist auth | status 201, fullName == "Jane Doe", medicalAlerts present | PRD R-3 |
| 2 | `test_future_dob_rejected_422` | Schema unit | ValidationError raised when date_of_birth > today | Spec 02 §2 |
| 3 | `test_search_patients_by_name_and_phone` | API + Staff auth | status 200, matching items returned with pagination metadata | PRD R-4 |
| 4 | `test_soft_delete_patient_sets_inactive` | API + Receptionist auth | status 204, subsequent GET query omits patient | PRD R-5 |
| 5 | `test_unauthenticated_request_rejected_401` | API | status 401 | NFR-6 |

## Out of scope
Appointment bookings for the patient (handled in T-008).

## Notes for the implementer
Ensure soft deletion modifies `is_active = False` rather than running a SQL `DELETE` statement. Use composite indexing on `(last_name, first_name)` and index on `phone`.

## Implementation log

**What was built:** Full patient management module — ORM model, schemas (with
`@computed_field` `fullName` alias and future-DOB validator), repository
functions (search + pagination), `PatientService`, REST router with RBAC guards,
and 6 API tests + 1 schema unit test.

**Files touched:**
- `backend/src/app/models/patient.py` — New: `Patient` ORM model (UUIDMixin,
  TimestampMixin, composite index `(last_name, first_name)`, index on `phone`
  and `is_active`)
- `backend/src/app/models/__init__.py` — Added `Patient` to exports
- `backend/src/app/schemas.py` — Added `PhoneStr`, `PatientCreate`,
  `PatientUpdate`, `PatientRead` (with `@computed_field(alias="fullName")`),
  `PatientPage`; `model_validator` on create/update rejects future DOB
- `backend/src/app/exceptions.py` — Added `PatientNotFoundError` (→ 404)
- `backend/src/app/db/repository.py` — Added `create_patient`,
  `get_patient_by_id`, `list_patients` (ILIKE search + pagination with count),
  `update_patient`, `soft_delete_patient`
- `backend/src/app/services/patient_service.py` — New: `PatientService`
  orchestrating create/get/list/update/soft_delete with existence guards
- `backend/src/app/api/deps.py` — Added `get_patient_service` and
  `PatientServiceDep`
- `backend/src/app/routers/patients.py` — New: 5 endpoints (POST, GET list,
  GET /{id}, PATCH, DELETE) with RBAC via `require_roles`
- `backend/src/app/main.py` — Registered `patients_router`, imported `Patient`
  model
- `backend/tests/api/test_patients.py` — New: 6 API tests
- `backend/tests/unit/test_schemas.py` — Added
  `test_future_dob_rejected_422`

**Acceptance criteria:**
- AC1 ✅ `test_create_patient_success_201` — 201 + `fullName` + `medicalAlerts`
- AC2 ✅ `test_invalid_phone_rejected_422` + `test_create_patient_missing_phone_422`
- AC3 ✅ `test_search_patients_by_name_and_phone` — search by name and phone
  with pagination metadata (`total`, `page`, `size`, `pages`)
- AC4 ✅ `test_soft_delete_patient_sets_inactive` — 204, patient excluded
  from default search
- AC5 ✅ `test_unauthenticated_request_rejected_401` — 401 without auth

**Quality gates:** ruff check ✅ | ruff format --check ✅ | mypy src ✅ |
pytest (40 passed) ✅

**Notes:** `@computed_field(alias="fullName")` stacked on `@property` requires
`# type: ignore[prop-decorator]` for mypy (Standard §3 Computed Fields pattern).
No spec deviations.

## Review history
