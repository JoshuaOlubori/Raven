# Appointments & Scheduling Module Spec

_Status: approved · Date: 2026-10-03 · Covers: R-10, R-11, R-12, R-13, R-14, NFR-1, NFR-4_

## 1. Responsibility
This module owns the core appointment lifecycle: booking, conflict-free scheduling with database-level overlap locks (ADR 0001), rescheduling, deterministic finite state machine (FSM) transitions, mandatory-reason cancellations, and the append-only immutable appointment audit log.
It delegates real-time event streaming and notifications to the Notifications & Events module.

---

## 2. Layer 1 — Contracts (Standard §3)

### Shared Constrained Types
```python
AppointmentStatus = Literal[
    "SCHEDULED",
    "CONFIRMED",
    "CHECKED_IN",
    "IN_PROGRESS",
    "COMPLETED",
    "CANCELLED",
    "NO_SHOW",
]
NonEmptyStr = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=500)]
```

### Schemas Table
| Schema | Purpose | Fields (name: type, optional?) | Validators / computed fields |
|---|---|---|---|
| `AppointmentCreate` | Booking request input | `patient_id: UUID`, `dentist_id: UUID`, `service_id: UUID`, `start_time: datetime` | `start_time` must be in the future (or current clinic date) |
| `AppointmentReschedule` | Reschedule request input | `start_time: datetime`, `dentist_id: UUID | None = None` | New slot must be in the future |
| `AppointmentStatusUpdate` | FSM transition input | `to_status: AppointmentStatus`, `note: str | None = None` | Target status must not be `CANCELLED` (cancellation uses dedicated endpoint) |
| `AppointmentCancel` | Cancellation request input | `cancellation_reason: NonEmptyStr` | Non-empty reason mandatory (R-13) |
| `AppointmentRead` | Public appointment view | `id: UUID`, `patient_id: UUID`, `dentist_id: UUID`, `service_id: UUID`, `start_time: datetime`, `end_time: datetime`, `status: AppointmentStatus`, `cancellation_reason: str | None`, `reminder_sent_at: datetime | None`, `created_at: datetime`, `updated_at: datetime` | CamelCase aliases |
| `AppointmentDetailRead` | Rich appointment view with relations | Same as `AppointmentRead` plus nested `patient: PatientRead`, `dentist: StaffRead`, `service: ServiceRead` | Eager-loaded relations for UI cards |
| `AuditLogRead` | Immutable audit log record | `id: UUID`, `appointment_id: UUID`, `actor_id: UUID`, `actor_name: str`, `from_status: str | None`, `to_status: str | None`, `old_start_time: datetime | None`, `new_start_time: datetime | None`, `note: str | None`, `created_at: datetime` | CamelCase aliases |

---

## 3. Layer 2 — Persistence (Standard §4)

### ORM Models: `Appointment` & `AppointmentAuditLog` (`app/models/appointment.py`, `app/models/audit.py`)
| Model | Columns | Relationships | Indexes / Constraints |
|---|---|---|---|
| `Appointment` | `id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)`<br>`patient_id: Mapped[UUID] = mapped_column(ForeignKey("patients.id"), index=True)`<br>`dentist_id: Mapped[UUID] = mapped_column(ForeignKey("staff.id"), index=True)`<br>`service_id: Mapped[UUID] = mapped_column(ForeignKey("dental_services.id"), index=True)`<br>`start_time: Mapped[datetime] = mapped_column(index=True)`<br>`end_time: Mapped[datetime] = mapped_column(index=True)`<br>`status: Mapped[str] = mapped_column(default="SCHEDULED", index=True)`<br>`cancellation_reason: Mapped[str | None]`<br>`reminder_sent_at: Mapped[datetime | None]`<br>`created_at: Mapped[datetime] = mapped_column(default=utcnow)`<br>`updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)` | `patient: Mapped["Patient"] = relationship(back_populates="appointments")`<br>`dentist: Mapped["Staff"] = relationship(back_populates="appointments")`<br>`service: Mapped["DentalService"] = relationship(back_populates="appointments")`<br>`audit_logs: Mapped[list["AppointmentAuditLog"]] = relationship(back_populates="appointment", cascade="all, delete-orphan")` | Composite index on `(dentist_id, start_time, end_time, status)`. Index on `reminder_sent_at`. |
| `AppointmentAuditLog` | `id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)`<br>`appointment_id: Mapped[UUID] = mapped_column(ForeignKey("appointments.id", ondelete="CASCADE"), index=True)`<br>`actor_id: Mapped[UUID] = mapped_column(ForeignKey("staff.id"), index=True)`<br>`from_status: Mapped[str | None]`<br>`to_status: Mapped[str | None]`<br>`old_start_time: Mapped[datetime | None]`<br>`new_start_time: Mapped[datetime | None]`<br>`note: Mapped[str | None]`<br>`created_at: Mapped[datetime] = mapped_column(default=utcnow)` | `appointment: Mapped["Appointment"] = relationship(back_populates="audit_logs")`<br>`actor: Mapped["Staff"] = relationship()` | Index on `(appointment_id, created_at)`. Append-only. |

### Eager-Loading Strategy (Avoid N+1, Standard §4.5)
- For `get_appointment_detail`: Use `joinedload` on `Appointment.patient`, `Appointment.dentist`, and `Appointment.service`.
- For `list_audit_logs`: Use `joinedload` on `AppointmentAuditLog.actor`.

### Repository Signatures (`app/db/repository.py`)
```python
async def get_appointment(session: AsyncSession, appointment_id: UUID) -> Appointment | None: ...
async def get_appointment_detail(session: AsyncSession, appointment_id: UUID) -> Appointment | None: ...
async def list_appointments(
    session: AsyncSession,
    dentist_id: UUID | None = None,
    patient_id: UUID | None = None,
    status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[Appointment]: ...
async def check_appointment_overlap(
    session: AsyncSession,
    dentist_id: UUID,
    start_time: datetime,
    end_time: datetime,
    exclude_id: UUID | None = None,
) -> bool: ...
async def create_appointment(session: AsyncSession, **kwargs) -> Appointment: ...
async def create_audit_log(session: AsyncSession, **kwargs) -> AppointmentAuditLog: ...
async def list_audit_logs_for_appointment(session: AsyncSession, appointment_id: UUID) -> list[AppointmentAuditLog]: ...
```

---

## 4. Layer 3 — Wiring (Standard §5)

### Dependencies
- `get_appointment_service(session: DbSessionDep, broadcaster: EventBroadcasterDep, notifier: NotificationServiceDep) -> AppointmentService`
- `AppointmentServiceDep = Annotated[AppointmentService, Depends(get_appointment_service)]`

### Endpoints
| Method | Path | Request | Response | Success | Errors | Guard | Covers |
|---|---|---|---|---|---|---|---|
| `POST` | `/api/v1/appointments` | `AppointmentCreate` | `AppointmentDetailRead` | 201 | 400, 401, 403, 404, 409, 422 | `require_roles("ADMIN", "RECEPTIONIST")` | R-10 |
| `GET` | `/api/v1/appointments` | Query: `dentist_id`, `patient_id`, `status`, `start_date`, `end_date` | `list[AppointmentDetailRead]` | 200 | 401 | `CurrentUserDep` | R-10 |
| `GET` | `/api/v1/appointments/{id}` | Path: `id: UUID` | `AppointmentDetailRead` | 200 | 401, 404 | `CurrentUserDep` | R-10 |
| `POST` | `/api/v1/appointments/{id}/reschedule` | `AppointmentReschedule` | `AppointmentDetailRead` | 200 | 400, 401, 403, 404, 409, 422 | `require_roles("ADMIN", "RECEPTIONIST")` | R-11 |
| `POST` | `/api/v1/appointments/{id}/status` | `AppointmentStatusUpdate` | `AppointmentDetailRead` | 200 | 400, 401, 403, 404, 422 | `require_roles("ADMIN", "RECEPTIONIST", "DENTIST")` | R-12 |
| `POST` | `/api/v1/appointments/{id}/cancel` | `AppointmentCancel` | `AppointmentDetailRead` | 200 | 400, 401, 403, 404, 422 | `require_roles("ADMIN", "RECEPTIONIST")` | R-13 |
| `GET` | `/api/v1/appointments/{id}/audit-logs` | Path: `id: UUID` | `list[AuditLogRead]` | 200 | 401, 404 | `CurrentUserDep` | R-14 |

### Authorization Matrix
| Action | Role / Permission | Row-Level (ABAC) Rule |
|---|---|---|
| Book / Reschedule / Cancel | `ADMIN`, `RECEPTIONIST` | Receptionists coordinate schedules |
| Check-in Patient | `ADMIN`, `RECEPTIONIST` | Receptionists greet arriving patients |
| Transition `IN_PROGRESS` / `COMPLETED` | `ADMIN`, `DENTIST` | Dentists mark their active chair appointments |
| View Appointments | `ADMIN`, `RECEPTIONIST`, `DENTIST` | Dentists can filter by their own `dentist_id` |
| View Audit Logs | `ADMIN`, `RECEPTIONIST`, `DENTIST` | Any staff can view transition history (R-14) |

---

## 5. Layer 4 — Concurrency and Overlap Locking (Standard §6)

### Atomic Overlap Guard (ADR 0001, NFR-1)
During booking or rescheduling within an active `AsyncSession` transaction:
```python
# 1. Fetch service duration to compute end_time = start_time + duration
# 2. Acquire a row lock on the stable dentist record. This lock is held until
#    the surrounding booking/rescheduling transaction commits and also covers
#    the case where the overlap query returns no appointment rows:
await session.execute(
    select(Staff.id).where(Staff.id == dentist_id).with_for_update()
)
# 3. Check non-cancelled overlapping records:
stmt = (
    select(Appointment.id)
    .where(
        Appointment.dentist_id == dentist_id,
        Appointment.status != "CANCELLED",
        Appointment.start_time < end_time,
        Appointment.end_time > start_time,
    )
)
if exclude_id:
    stmt = stmt.where(Appointment.id != exclude_id)
# Do not rely on FOR UPDATE on Appointment rows: an empty result locks nothing.
existing = await session.scalar(stmt)
if existing is not None:
    raise AppointmentOverlapConflictError("The requested time window overlaps an existing appointment for this dentist.")
```
The dentist-row lock serializes slot checks across PostgreSQL transactions, including when no appointment currently overlaps. After waiting for the previous transaction to commit, the next transaction re-runs the overlap query and raises `409 Conflict` if needed. Booking and rescheduling must use this same lock before checking the target dentist's schedule.

---

## 6. Layer 5 — State and Hardening (Standard §7)
- **Shared State:** No module-level mutable state. All state changes are committed to the ACID database transaction.
- **Audit Immutability (NFR-4):** No `UPDATE` or `DELETE` endpoints exist for `appointment_audit_logs`. The database model is append-only.

---

## 7. Errors
| Exception | Raised when | HTTP Status | Error Code |
|---|---|---|---|
| `AppointmentOverlapConflictError` | Target booking interval overlaps another active appointment for that dentist | 409 | `APPOINTMENT_OVERLAP_CONFLICT` |
| `OutsideShiftHoursError` | Target booking interval does not fall entirely within dentist's shift | 400 | `OUTSIDE_SHIFT_HOURS` |
| `TimeOffConflictError` | Target booking interval intersects a dentist's time-off block | 409 | `TIME_OFF_CONFLICT` |
| `InvalidStateTransitionError` | FSM does not permit transition from current status to requested status | 400 | `INVALID_STATUS_TRANSITION` |
| `AppointmentNotFoundError` | Appointment ID does not exist | 404 | `APPOINTMENT_NOT_FOUND` |
| `CancellationReasonRequiredError` | Cancellation submitted without reason | 422 | `CANCELLATION_REASON_REQUIRED` |

---

## 8. State Machine (FSM)

```
       +------------+
       | SCHEDULED  | <-----+ (Reschedule)
       +------------+       |
         |   |    |         |
         |   |    +---------+
         |   v
         | [CONFIRMED] <----+ (Reschedule)
         |   |    |         |
         |   |    +---------+
         v   v
     [CHECKED_IN]
         |
         v
    [IN_PROGRESS]
         |
         v
     [COMPLETED] (Terminal)

From SCHEDULED, CONFIRMED, CHECKED_IN -> [CANCELLED] (Terminal, Reason Required)
From SCHEDULED, CONFIRMED -> [NO_SHOW] (Terminal)
```

| From Status | Event / Action | To Status | Guard Rules | Side Effects |
|---|---|---|---|---|
| `SCHEDULED` | Confirm | `CONFIRMED` | Staff confirmation | Emit SSE event |
| `SCHEDULED` / `CONFIRMED` | Check-in | `CHECKED_IN` | Patient arrives at desk | Emit SSE event |
| `SCHEDULED` / `CONFIRMED` | Reschedule | `SCHEDULED` | New slot conflict-free | Audit log entry, dispatch reschedule confirmation |
| `CHECKED_IN` | Begin Treatment | `IN_PROGRESS` | Dentist seats patient in chair | Emit SSE event |
| `IN_PROGRESS` | Complete Treatment | `COMPLETED` | Treatment finished | Emit SSE event, Terminal state |
| `SCHEDULED` / `CONFIRMED` / `CHECKED_IN` | Cancel | `CANCELLED` | Non-empty `cancellation_reason` | Audit log entry, freed slot, Emit SSE event |
| `SCHEDULED` / `CONFIRMED` | Mark No-Show | `NO_SHOW` | Patient did not arrive | Audit log entry, Emit SSE event |

---

## 9. Test Seams
| Behaviour | Seam | Notes |
|---|---|---|
| Empty cancellation reason rejected | Schema unit test | 422 raised |
| Illegal FSM transition (e.g. COMPLETED -> CANCELLED) | Service unit test | `InvalidStateTransitionError` raised with 400 |
| Concurrent booking of same slot | Integration test with 2 sessions | Exactly one commits (201), the other raises 409 Conflict (NFR-1) |
| Audit log immutability | Integration test | Asserts every state change generates an append-only row with acting staff ID |
| Eager loading avoids N+1 | Repository test | Verifies single query with joins returns patient and service |

---

## 10. Traceability
| Requirement | Spec Section | Endpoint(s) |
|---|---|---|
| **R-10** Book Appointment | §2 Contracts, §3 Persistence, §4 Endpoints, §5 Concurrency | `POST /api/v1/appointments` |
| **R-11** Reschedule Appointment | §2 Contracts, §4 Endpoints, §8 FSM | `POST /api/v1/appointments/{id}/reschedule` |
| **R-12** State Machine Transitions | §4 Endpoints, §8 State Machine | `POST /api/v1/appointments/{id}/status` |
| **R-13** Cancel Appointment | §2 Contracts, §4 Endpoints, §8 FSM | `POST /api/v1/appointments/{id}/cancel` |
| **R-14** Immutable Audit Log | §2 Contracts, §3 Persistence, §4 Endpoints | `GET /api/v1/appointments/{id}/audit-logs` |
| **NFR-1** Zero Double-Booking | §5 Atomic Overlap Guard | Tested via concurrent session tests |
| **NFR-4** Audit Immutability | §3 Persistence, §6 Hardening | No mutation endpoints; append-only schema |

---

## 11. Open Questions / ADRs
- [ADR 0001: Dynamic Slot Computation and Database Overlap Guard](file:///c:/Users/seyi/Documents/Development/Raven/docs/adr/0001-dynamic-slot-computation-and-conflict-prevention.md)
