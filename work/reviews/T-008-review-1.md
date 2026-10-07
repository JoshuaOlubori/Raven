# Review T-008 round 1 — Changes Requested
Gates: ruff ✓ · mypy ✓ · pytest ✓ (103 passed)

## Spec — findings (quote the spec line)

### 1. Missing `exclude_id` handling in overlap check for reschedule (future-proofing)
**File:** `backend/src/app/db/repository.py:107`  
**Spec §5 (Layer 4) ADR 0001:** "If exclude_id: stmt = stmt.where(Appointment.id != exclude_id)"  
The `check_appointment_overlap` function correctly accepts `exclude_id` parameter and filters it, but the service layer doesn't pass it when it could be needed. The ticket explicitly notes this is for future T-009 reschedule. While not strictly required for T-008, the repository implementation has it but the service doesn't use it — this is acceptable for now but worth noting.

### 2. Shift coverage validation doesn't enforce "same day in clinic timezone" for multi-day appointments
**File:** `backend/src/app/services/appointment_service.py:100-104`  
**Spec §7 (Errors):** `OutsideShiftHoursError` — "Target booking interval does not fall entirely within dentist's shift"  
The service validates that `start_local.date() != end_local.date()` and raises `OutsideShiftHoursError`, but this only catches appointments that span midnight in clinic timezone. It doesn't validate that the appointment doesn't span multiple days (e.g., a 2-hour appointment starting at 11pm). The check is correct for the typical case but could be more explicit about the requirement that the entire interval falls within one shift day.

### 3. Time-off block query uses UTC window but blocks stored in UTC — correct
**File:** `backend/src/app/services/appointment_service.py:137-143`  
**Spec §7:** `TimeOffConflictError` — 409 `TIME_OFF_CONFLICT`  
The validation correctly queries time-off blocks using the UTC window. This matches the spec. ✓

### 4. Appointment creation returns correct status and auto-calculated end_time
**File:** `backend/src/app/routers/appointments.py:48-72`  
**PRD R-10 Acceptance:** "Given an open slot, When staff submit POST /api/v1/appointments, Then the appointment is created with status SCHEDULED, end time auto-computed, and 201 Created returned."  
The endpoint returns 201 with `AppointmentDetailRead` containing eager-loaded relations. The service auto-calculates `end_time = start_time + duration_minutes`. ✓

### 5. RBAC enforcement — Dentist cannot book, Unauthenticated returns 401
**File:** `backend/src/app/routers/appointments.py:39-41`  
**Spec §4 Authorization Matrix:** "Book / Reschedule / Cancel: ADMIN, RECEPTIONIST"  
The POST endpoint uses `require_roles("ADMIN", "RECEPTIONIST")`. API tests verify 403 for Dentist and 401 for unauthenticated. ✓

### 6. GET /api/v1/appointments returns eager-loaded relations (no N+1)
**File:** `backend/src/app/db/repository.py:70-94`, `backend/src/app/routers/appointments.py:85-115`  
**Spec §3 (Layer 2) §4.5:** "Eager-Loading Strategy... Use joinedload on Appointment.patient, Appointment.dentist, and Appointment.service."  
**Test Strategy §4:** "Query-Count Guards — List endpoints maintain constant query count"  
Both repository functions use `joinedload` for all three relations. The API endpoint passes them through. API test `test_list_appointments_eager_loading` verifies relations are present. ✓

### 7. Filtering on list endpoint matches spec
**File:** `backend/src/app/routers/appointments.py:85-115`  
**Spec §4 Endpoints Table:** Query params `dentist_id`, `patient_id`, `status`, `start_date`, `end_date`  
The endpoint accepts all five filters with correct aliases (`dentistId`, `patientId`, `startDate`, `endDate`). ✓

### 8. Error codes match spec exactly
**File:** `backend/src/app/exceptions.py:111-157`  
**Spec §7 Errors Table:** `APPOINTMENT_OVERLAP_CONFLICT` (409), `OUTSIDE_SHIFT_HOURS` (400), `TIME_OFF_CONFLICT` (409)  
All three error codes and HTTP status codes match the spec. Additional exceptions for future tickets (`APPOINTMENT_NOT_FOUND`, `INVALID_STATUS_TRANSITION`, `CANCELLATION_REASON_REQUIRED`) are also present with correct codes. ✓

### 9. Availability engine integration with appointments
**File:** `backend/src/app/services/availability_engine.py`, `backend/src/app/routers/schedules.py`  
**Spec §3:** "Available slots are dynamically computed: Working shifts minus existing active appointments (excluding CANCELLED) minus time-off blocks"  
The availability engine now accepts `appointments` parameter and `_build_busy_intervals` includes non-cancelled appointments. The schedules router fetches appointments and passes them to the engine. ✓

---

## Standards — findings (cite standard § or smell)

### 1. ⚠️ MAJOR: `check_appointment_overlap` lacks `with_for_update()` for PostgreSQL row locking
**File:** `backend/src/app/db/repository.py:107-115`  
**Spec §5 (Layer 4) ADR 0001:** "Under PostgreSQL: `.with_for_update()` ensures serializable conflict rejection"  
**Standard §6 (Concurrency):** "pessimistic locking or temporal range exclusion"  

The comment on line 107 says "Under PostgreSQL: .with_for_update() ensures serializable conflict rejection" but the code does **not** actually call `.with_for_update()`. This is a critical gap for NFR-1 (Zero Double-Booking) in production PostgreSQL. Without row locking, two concurrent transactions can both pass the overlap check and then both insert, causing a double-booking.

**Fix direction:** Add `.with_for_update(nowait=True)` to the select statement in `check_appointment_overlap`, or use `select(...).with_for_update()` with appropriate isolation level. The comment implies intent but implementation is missing.

### 2. ⚠️ MAJOR: Timezone handling inconsistency in `_validate_shift_coverage`
**File:** `backend/src/app/services/appointment_service.py:93-99`  
**Standard §2 (Naming) & §7 (Timezone Consistency NFR-3):** "All database timestamps stored in UTC. Local business logic... must execute against the configured clinic wall-clock timezone"  

The code does:
```python
if start_time.tzinfo is None:
    start_time = start_time.replace(tzinfo=ZoneInfo("UTC"))
if end_time.tzinfo is None:
    end_time = end_time.replace(tzinfo=ZoneInfo("UTC"))
```
This assumes naive datetimes are UTC. However, earlier in `book_appointment` (line 63-65), the code converts timezone-aware input to naive UTC:
```python
if start_time.tzinfo is not None:
    start_time = start_time.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
```
So by the time `_validate_shift_coverage` receives `start_time`, it's already naive UTC. The defensive re-attachment of UTC tzinfo is redundant but harmless. However, the pattern is inconsistent and could lead to bugs if callers change.

**Fix direction:** Document clearly that all internal service methods expect naive UTC datetimes. Remove the redundant tzinfo handling in `_validate_shift_coverage` since the caller already normalized.

### 3. MINOR: `__import__("datetime").timedelta` instead of direct import
**File:** `backend/src/app/services/appointment_service.py:66`  
**Standard §2 (Naming) / Code clarity:**  
```python
end_time = start_time + __import__("datetime").timedelta(minutes=duration)
```
This is an unusual pattern. A standard import at the top of the file (`from datetime import timedelta`) would be clearer and more idiomatic.

**Fix direction:** Move `timedelta` to the top-level imports.

### 4. MINOR: Redundant `from sqlalchemy import select` inside function
**File:** `backend/src/app/db/repository.py:102`  
**Standard:** Module-level imports preferred. The function imports `select` again even though it's already imported at module level (line 7).

**Fix direction:** Remove the inner import.

### 5. NIT: Missing docstring on `AppointmentDetailRead` model_config
**File:** `backend/src/app/schemas.py:412`  
`model_config = ConfigDict(populate_by_name=True, from_attributes=True)` — no comment explaining why `from_attributes=True` is needed here but not on `AppointmentRead`. (It's needed for ORM model validation with nested relations.)

**Fix direction:** Add inline comment.

### 6. NIT: Composite index column order
**File:** `backend/src/app/models/appointment.py:25-29`  
**Standard §4 (Layer 2):** "Composite index on (dentist_id, start_time, end_time, status)"  
The index is defined as `(dentist_id, start_time, end_time, status)`. For the overlap query pattern `WHERE dentist_id = ? AND start_time < ? AND end_time > ? AND status != 'CANCELLED'`, the column order is reasonable but putting `status` last means the index can't be used for the status filter efficiently. Consider `(dentist_id, status, start_time, end_time)` if status filtering is common.

---

## Tests — findings

### 1. ✅ AC1 — `test_book_appointment_success_201` (API) / `test_book_appointment_success` (Unit)
- Drives public HTTP seam with `AsyncClient` (API) and service directly (Unit)
- Expected values from PRD R-10: status 201, `SCHEDULED`, end_time = start_time + duration
- Assertions are independent of implementation (uses `timedelta(minutes=45)` from fixture, not from service code)
- Verifies eager-loaded patient, dentist, service in response

### 2. ✅ AC2 — `test_booking_before_shift_rejected_400`, `test_booking_after_shift_rejected_400`, `test_booking_on_non_shift_day_rejected_400` (API) / `test_booking_outside_shift_rejected`, `test_booking_on_non_shift_day_rejected` (Unit)
- Tests all three outside-shift scenarios: before shift start, after shift end (with duration), non-shift day
- Asserts exact error code `OUTSIDE_SHIFT_HOURS` and status 400
- Unit tests use pytest.raises on service exception; API tests check HTTP response

### 3. ✅ AC3 — `test_booking_overlapping_time_off_rejected_409` (API) / `test_booking_overlapping_time_off_rejected` (Unit)
- Creates time-off block via API then attempts overlapping booking
- Asserts 409 with `TIME_OFF_CONFLICT`
- Unit test uses repository directly to create block

### 4. ⚠️ MINOR: AC4 — `test_concurrent_booking_overlap_prevention_409` (API) / `test_concurrent_booking_overlap_prevention` (Unit)
**API test note (line 359-361):** "With SQLite test DB, requests run sequentially so first commits before second runs its overlap check. In production (PostgreSQL), SELECT FOR UPDATE handles true concurrent requests."
- The test simulates concurrency by running sequentially with commit between — this works for SQLite but **does not test true concurrent behavior**
- Without `with_for_update()` in the repository (see Standards #1), the test would pass even if the production code is broken for real concurrency
- This is a test limitation due to SQLite, but the missing `with_for_update()` means the production guarantee is not actually enforced

**Fix direction:** The test correctly documents its limitation. The fix for Standards #1 (adding `with_for_update()`) would make the test actually meaningful for PostgreSQL.

### 5. ✅ AC5 — `test_list_appointments_eager_loading` (API) / `test_list_appointments_eager_loading_no_n_plus_one` (Unit)
- Creates appointment then lists — verifies patient, dentist, service are present without additional queries
- Unit test explicitly checks all three relations are accessible

### 6. ✅ Additional validation tests
- `test_admin_can_book_appointment` — verifies Admin role works
- `test_dentist_cannot_book_appointment_403` — 403 with `RBAC_FORBIDDEN`
- `test_unauthenticated_booking_rejected_401` — 401
- `test_booking_inactive_service_rejected` — `ServiceNotFoundError`
- `test_booking_nonexistent_service_rejected` — `ServiceNotFoundError`
- `test_check_appointment_overlap_true` — tests exact, partial (start during, end during, contained) overlaps
- `test_check_appointment_overlap_false` — tests before, after, different dentist
- `test_check_appointment_overlap_excludes_cancelled` — cancelled appointments ignored
- `test_check_appointment_overlap_exclude_id` — exclude_id parameter works for reschedule

### 7. NIT: Test fixtures use `override_dbsession` inconsistently
Some fixtures use `override_dbsession` parameter, others don't. This is a test infrastructure detail but could lead to session isolation issues.

---

## Summary — counts per severity; the single worst issue

| Severity | Count | Issues |
|---|---|---|
| **Blocker** | 1 | Missing `with_for_update()` in overlap check — breaks NFR-1 in production PostgreSQL |
| **Major** | 1 | Timezone handling inconsistency in `_validate_shift_coverage` |
| **Minor** | 3 | `__import__` pattern, redundant import, test concurrency limitation |
| **Nit** | 3 | Docstring on model_config, composite index column order, fixture inconsistency |

**Single worst issue:** The `check_appointment_overlap` function lacks `.with_for_update()` for PostgreSQL row locking (ADR 0001, Spec §5, Standard §6). Without this, concurrent booking requests can both pass the overlap check and both insert, violating the core NFR-1 guarantee of zero double-booking. The comment in the code acknowledges this but the implementation is missing.