# Review T-009 round 1 — Approve
Gates: ruff ✓ · mypy ✓ · pytest ✓ (108 passed)

## Spec — findings (quote the spec line)

### ✅ AC1 — Happy-path reschedule (R-11)
**Spec:** "Given an appointment in `SCHEDULED` or `CONFIRMED` status, When `POST /api/v1/appointments/{id}/reschedule` is submitted with a valid open slot, Then the appointment slot is updated, status is reset to `SCHEDULED`, and `200 OK` is returned (R-11)."  
**File:** `backend/tests/api/test_appointments.py:517-575` (`test_reschedule_appointment_success_200`)  
**Verifies:** status 200, start_time matches new slot, status == "SCHEDULED", end_time = start_time + service duration, eager-loaded relations present.

### ✅ AC2 — Reschedule rejected for COMPLETED/CANCELLED (R-11)
**Spec:** "Given an appointment in `COMPLETED` or `CANCELLED` status, When rescheduling is attempted, Then the system rejects the request with `400 Bad Request` ("Cannot reschedule a completed or cancelled appointment")."  
**File:** `backend/tests/api/test_appointments.py:578-630` (`test_reschedule_completed_appointment_rejected_400`)  
**Verifies:** 400 status, error code `INVALID_STATUS_TRANSITION`, message contains "Cannot reschedule".

### ✅ AC3 — Reschedule to conflicting slot → 409 (Spec 05 §7)
**Spec:** "Given an appointment reschedule to a slot that overlaps another appointment, Then the system returns `409 Conflict`."  
**File:** `backend/tests/api/test_appointments.py:633-703` (`test_reschedule_to_conflicting_slot_returns_409`)  
**Verifies:** 409 status, error code `APPOINTMENT_OVERLAP_CONFLICT`.

### ✅ AC4 — Cancel with reason success (R-13)
**Spec:** "Given an appointment, When `POST /api/v1/appointments/{id}/cancel` is submitted with reason "Patient has flu", Then status transitions to `CANCELLED` and returns `200 OK` (R-13)."  
**File:** `backend/tests/api/test_appointments.py:706-750` (`test_cancel_appointment_with_reason_success_200`)  
**Verifies:** 200 status, status == "CANCELLED", cancellationReason saved and returned, eager-loaded relations present.

### ✅ AC5 — Cancel without reason → 422 (R-13)
**Spec:** "Given a cancellation request with an empty reason, When submitted, Then the system rejects the request with `422 Unprocessable Entity` (R-13)."  
**File:** `backend/tests/api/test_appointments.py:753-794` (`test_cancel_appointment_without_reason_rejected_422`)  
**Verifies:** 422 status, Pydantic validation error on `cancellationReason` with "at least 1" message.

### ✅ AC6 — Cancelled appointment frees slot (covered by existing tests)
**Spec:** "Given a cancelled appointment, When availability slots are queried for that time interval, Then the freed slot is immediately available for new bookings (covered by existing availability engine tests)."  
**Note:** Ticket explicitly states this is covered by existing availability engine tests in T-007. No new test added for this ticket.

### ✅ FSM compliance
**Spec 05 §8:** "From SCHEDULED / CONFIRMED | Reschedule | SCHEDULED | New slot conflict-free" — implemented, status reset to SCHEDULED.  
**Spec 05 §8:** "From SCHEDULED / CONFIRMED / CHECKED_IN | Cancel | CANCELLED | Non-empty cancellation_reason" — implemented, validates SCHEDULED, CONFIRMED, CHECKED_IN states.

### ✅ Error codes match spec exactly
**Spec 05 §7:** `APPOINTMENT_OVERLAP_CONFLICT` (409), `OUTSIDE_SHIFT_HOURS` (400), `TIME_OFF_CONFLICT` (409), `INVALID_STATUS_TRANSITION` (400), `CANCELLATION_REASON_REQUIRED` (422), `APPOINTMENT_NOT_FOUND` (404) — all match.

### ✅ RBAC enforcement
**Spec 05 §4 Authorization Matrix:** "Book / Reschedule / Cancel | ADMIN, RECEPTIONIST" — endpoints use `require_roles("ADMIN", "RECEPTIONIST")`.

### ✅ Endpoints match spec
**Spec 05 §4:** `POST /api/v1/appointments/{id}/reschedule` and `POST /api/v1/appointments/{id}/cancel` with `AppointmentReschedule` and `AppointmentCancel` request bodies, returning `AppointmentDetailRead`.

### ✅ Atomic overlap guard with exclude_id
**Spec 05 §5:** "Uses SELECT ... FOR UPDATE NOWAIT ... if exclude_id: stmt = stmt.where(Appointment.id != exclude_id)" — implemented in `repository.py:443-456` and used in service with `exclude_id=appointment_id`.

---

## Standards — findings (cite standard § or smell)

### ✅ Layer separation (Standard §3/§5)
- Handlers are thin (`appointments.py`), delegate to `AppointmentService`
- Service contains business logic (`appointment_service.py`)
- Repository is pure data access (`repository.py`)

### ✅ No handler opens its own session
- Uses `AppointmentServiceDep` dependency injection (Standard §3)

### ✅ No scattered role checks
- Uses `require_roles("ADMIN", "RECEPTIONIST")` dependency (Standard §3)

### ✅ Business rules in service, not handlers
- State validation, shift coverage, time-off, overlap check all in service

### ✅ Modern Pydantic v2 idioms
- Uses `model_validate()` not `parse_obj()`, `model_dump()` not `dict()`

### ✅ Eager loading avoids N+1
- `get_appointment_detail` and `list_appointments` use `joinedload` on patient, dentist, service (Standard §4.5)

### ✅ No blocking work on event loop
- All I/O is async, no sync calls in async functions

### ✅ No module-level mutable state
- Service is stateless, holds only session reference (Standard §7)

### ✅ Sessions not held across streaming
- Not applicable (no streaming in this ticket)

### ✅ Correct 401 vs 403
- 401 for unauthenticated, 403 for unauthorized role (Standard §4)

### ✅ Naming conventions (Standard §2)
- Schema names: `AppointmentReschedule`, `AppointmentCancel`, `AppointmentDetailRead`
- Function names: `reschedule_appointment`, `cancel_appointment`
- Error codes: SCREAMING_SNAKE_CASE

### ✅ Correlation ID / structured logging
- Handled by global error handler in `main.py` (Standard §4)

### ✅ No secrets or config inline
- Settings injected via dependency

### Fowler baseline (judgement calls)
- ✅ No Mysterious Names — clear, domain-aligned naming
- ✅ No Duplicated Code — validation helpers reused (`_validate_shift_coverage`, `_validate_time_off_conflict`)
- ✅ No Feature Envy — service calls repository functions appropriately
- ✅ No Data Clumps — datetime parameters passed as explicit arguments
- ✅ No Primitive Obsession — uses UUID, datetime, NonEmptyStr constrained types
- ✅ No Repeated Switches — no switch statements
- ✅ No Shotgun Surgery — changes localized to service, router, schemas, repository
- ✅ No Divergent Change — service handles all appointment mutations
- ✅ No Speculative Generality — no over-engineered abstractions
- ✅ No Message Chains — direct method calls
- ✅ No Middle Man — thin handlers, direct service delegation
- ✅ No Refused Bequest — not applicable

### ⚠️ MINOR: Generic `update_appointment` in repository
**File:** `backend/src/app/db/repository.py:484-495`  
**Problem:** `update_appointment` accepts `**kwargs: object` and blindly applies `setattr` for any field. While the service layer validates before calling, the repository function allows arbitrary field updates that could bypass FSM validation if called directly.  
**Fix direction:** Restrict to known mutable fields or add field validation. Consider typed keyword arguments (e.g., `status: str | None = None, start_time: datetime | None = None, ...`) or a domain-specific update function.

### ⚠️ NIT: Missing docstring on `AppointmentDetailRead.model_config`
**File:** `backend/src/app/schemas.py:436`  
**Problem:** `model_config = ConfigDict(populate_by_name=True, from_attributes=True)` — no comment explaining why `from_attributes=True` is needed here but not on `AppointmentRead`.  
**Fix direction:** Add inline comment: `# from_attributes=True required for ORM -> Pydantic validation with nested relations`

### ✅ Defense in depth on cancellation reason
- Schema: `cancellation_reason: NonEmptyStr` (Pydantic validates → 422)
- Service: explicit `if not cancellation_reason or not cancellation_reason.strip(): raise CancellationReasonRequiredError()` (service validates → 422)
- Both paths return 422, consistent with spec

---

## Tests — findings

### ✅ Every acceptance criterion has a test at the named seam
| AC | Test | Seam |
|----|------|------|
| 1 | `test_reschedule_appointment_success_200` | API + Receptionist auth |
| 2 | `test_reschedule_completed_appointment_rejected_400` | API + Receptionist auth |
| 3 | `test_reschedule_to_conflicting_slot_returns_409` | API + Receptionist auth |
| 4 | `test_cancel_appointment_with_reason_success_200` | API + Receptionist auth |
| 5 | `test_cancel_appointment_without_reason_rejected_422` | API + Receptionist auth |

### ✅ Expected values independent of implementation
- Tests use fixed timezone-aware datetimes and compute expected UTC values from spec/fixtures (`timedelta(minutes=45)` from service fixture), not from implementation code.

### ✅ Tests assert behaviour, not private structure
- API tests verify HTTP status, response body fields, error codes
- Would survive refactor of internal service/repository methods

### ✅ Failure paths exist
- 400 (invalid state transition), 404 (not found), 409 (overlap), 422 (validation), 401/403 (auth/RBAC)

### ✅ No sleeps, order dependence, or shared mutable fixtures
- Each test creates its own appointments, uses transaction-scoped fixtures

### ⚠️ MINOR: Test #6 from test plan not explicitly implemented
**Test plan:** "test_cancelled_appointment_frees_slot_for_booking" (Integration)  
**Ticket note:** "covered by existing availability engine tests"  
**Status:** Acceptable per ticket, but consider adding an explicit test here for traceability in future.

---

## Summary — counts per severity; the single worst issue

| Severity | Count | Issues |
|---|---|---|
| **Blocker** | 0 | — |
| **Major** | 0 | — |
| **Minor** | 1 | Generic `update_appointment` in repository allows arbitrary field updates |
| **Nit** | 1 | Missing docstring on `AppointmentDetailRead.model_config` |

**Single worst issue:** The generic `update_appointment` repository function — while currently safe because the service layer validates, it creates a footgun for future callers who might bypass the service layer.

---

## Verdict
**Approve** — All acceptance criteria satisfied, quality gates green, tests meaningful at correct seams, standards followed. The minor finding on `update_appointment` is a defensive consideration, not a current bug.