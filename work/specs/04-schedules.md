# Dentist Schedules & Availability Engine Module Spec

_Status: approved · Date: 2026-10-03 · Covers: R-7, R-8, R-9, NFR-2, NFR-3_

## 1. Responsibility
This module owns the definition of dentist weekly recurring working shifts, ad-hoc time-off / blocked periods (vacations, lunch, sick leave), and the dynamic availability computation engine that calculates open booking slots matching specific service procedure durations in real time.
It explicitly does NOT own the booking state machine (which is owned by Appointments).

---

## 2. Layer 1 — Contracts (Standard §3)

### Shared Constrained Types
```python
DayOfWeek = Annotated[int, Field(ge=0, le=6, description="0=Monday, 1=Tuesday, ..., 6=Sunday")]
```

### Schemas Table
| Schema | Purpose | Fields (name: type, optional?) | Validators / computed fields |
|---|---|---|---|
| `WorkingShiftCreate` | Register weekly recurring shift | `dentist_id: UUID`, `day_of_week: DayOfWeek`, `start_time: time`, `end_time: time` | `start_time < end_time` enforced via `@model_validator(mode="after")` |
| `WorkingShiftRead` | Public shift view | `id: UUID`, `dentist_id: UUID`, `day_of_week: DayOfWeek`, `start_time: time`, `end_time: time` | CamelCase aliases |
| `TimeOffBlockCreate` | Ad-hoc blocked period input | `dentist_id: UUID`, `start_time: datetime`, `end_time: datetime`, `reason: str | None = None` | `start_time < end_time`; normalized to UTC |
| `TimeOffBlockRead` | Public time-off view | `id: UUID`, `dentist_id: UUID`, `start_time: datetime`, `end_time: datetime`, `reason: str | None`, `created_at: datetime` | CamelCase aliases |
| `AvailabilityQuery` | Query parameters for slot search | `dentist_id: UUID | None = None`, `service_id: UUID`, `date: date` | Target date cannot be in the distant past; service must be active |
| `TimeSlot` | Single open bookable window | `start_time: datetime`, `end_time: datetime`, `dentist_id: UUID`, `dentist_name: str` | CamelCase aliases |
| `AvailabilityResponse` | Collection of available slots | `date: date`, `service_id: UUID`, `duration_minutes: int`, `slots: list[TimeSlot]` | CamelCase aliases |

---

## 3. Layer 2 — Persistence (Standard §4)

### ORM Models: `WorkingShift` & `TimeOffBlock` (`app/models/schedule.py`)
| Model | Columns | Relationships | Indexes / Constraints |
|---|---|---|---|
| `WorkingShift` | `id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)`<br>`dentist_id: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="CASCADE"), index=True)`<br>`day_of_week: Mapped[int]`<br>`start_time: Mapped[time]`<br>`end_time: Mapped[time]` | `dentist: Mapped["Staff"] = relationship(back_populates="working_shifts")` | Unique constraint on `(dentist_id, day_of_week, start_time)` |
| `TimeOffBlock` | `id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)`<br>`dentist_id: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="CASCADE"), index=True)`<br>`start_time: Mapped[datetime] = mapped_column(index=True)`<br>`end_time: Mapped[datetime] = mapped_column(index=True)`<br>`reason: Mapped[str | None]`<br>`created_at: Mapped[datetime] = mapped_column(default=utcnow)` | `dentist: Mapped["Staff"] = relationship(back_populates="time_off_blocks")` | Composite index on `(dentist_id, start_time, end_time)` |

### Repository Signatures (`app/db/repository.py`)
```python
async def list_shifts_for_dentist(session: AsyncSession, dentist_id: UUID) -> list[WorkingShift]: ...
async def list_shifts_by_day(session: AsyncSession, day_of_week: int, dentist_id: UUID | None = None) -> list[WorkingShift]: ...
async def create_working_shift(session: AsyncSession, *, dentist_id: UUID, day_of_week: int, start_time: time, end_time: time) -> WorkingShift: ...
async def delete_working_shift(session: AsyncSession, shift_id: UUID) -> bool: ...

async def list_time_off_blocks(session: AsyncSession, dentist_id: UUID, start_range: datetime, end_range: datetime) -> list[TimeOffBlock]: ...
async def create_time_off_block(session: AsyncSession, *, dentist_id: UUID, start_time: datetime, end_time: datetime, reason: str | None) -> TimeOffBlock: ...
async def delete_time_off_block(session: AsyncSession, block_id: UUID) -> bool: ...
```

---

## 4. Layer 3 — Wiring (Standard §5)

### Dependencies
- `get_availability_engine(session: DbSessionDep, settings: SettingsDep) -> AvailabilityEngine`
- `AvailabilityEngineDep = Annotated[AvailabilityEngine, Depends(get_availability_engine)]`

### Endpoints
| Method | Path | Request | Response | Success | Errors | Guard | Covers |
|---|---|---|---|---|---|---|---|
| `POST` | `/api/v1/schedules/shifts` | `WorkingShiftCreate` | `WorkingShiftRead` | 201 | 400, 401, 403, 404, 409, 422 | `require_roles("ADMIN")` | R-7 |
| `GET` | `/api/v1/schedules/shifts` | Query: `dentist_id: UUID | None` | `list[WorkingShiftRead]` | 200 | 401 | `CurrentUserDep` | R-7 |
| `DELETE` | `/api/v1/schedules/shifts/{shift_id}` | Path: `shift_id: UUID` | None (204) | 204 | 401, 403, 404 | `require_roles("ADMIN")` | R-7 |
| `POST` | `/api/v1/schedules/time-off` | `TimeOffBlockCreate` | `TimeOffBlockRead` | 201 | 400, 401, 403, 404, 422 | `require_roles("ADMIN", "DENTIST")` | R-8 |
| `GET` | `/api/v1/schedules/time-off` | Query: `dentist_id: UUID`, `start_date: date`, `end_date: date` | `list[TimeOffBlockRead]` | 200 | 401 | `CurrentUserDep` | R-8 |
| `DELETE` | `/api/v1/schedules/time-off/{block_id}` | Path: `block_id: UUID` | None (204) | 204 | 401, 403, 404 | `require_roles("ADMIN", "DENTIST")` | R-8 |
| `GET` | `/api/v1/schedules/availability` | Query: `AvailabilityQuery` (`dentist_id`, `service_id`, `date`) | `AvailabilityResponse` | 200 | 400, 401, 404, 422 | `CurrentUserDep` | R-9 |

### Authorization Matrix
| Action | Role / Permission | Row-Level (ABAC) Rule |
|---|---|---|
| Configure Working Shifts | `ADMIN` only | Only Admins set recurring clinical operational hours |
| Add Time-Off Block | `ADMIN`, `DENTIST` | Dentists can only add time-off for themselves; Admins can add for anyone |
| Delete Time-Off Block | `ADMIN`, `DENTIST` | Dentists can only delete their own blocks |
| Query Availability Slots | Authenticated staff (`ADMIN`, `RECEPTIONIST`, `DENTIST`) | Any staff can query slots for booking |

---

## 5. Layer 4 — Concurrency and Real-Time (Standard §6)
- **Dynamic Slot Algorithm (ADR 0001):**
  Given target date $D$ in `CLINIC_TIMEZONE`:
  1. Determine weekday $W = D.\text{weekday()}$.
  2. Fetch active shifts for $W$. Convert $(D, \text{shift.start\_time})$ and $(D, \text{shift.end\_time})$ to UTC timezone-aware datetimes.
  3. Fetch active appointments ($status \neq \text{CANCELLED}$) and time-off blocks for the target day window in a single query.
  4. Segment the shift timeline into candidate intervals $[t_i, t_i + \text{duration}]$, advancing in 15-minute slot steps (or full duration steps).
  5. Filter candidates: Keep only intervals completely within the shift and having zero intersection with booked appointments and time-off blocks:
     $$\forall \text{busy}: \max(t_{\text{start}}, \text{busy}_{\text{start}}) < \min(t_{\text{end}}, \text{busy}_{\text{end}}) \implies \text{conflict}$$
  6. The pure interval calculation is CPU-only and executes in $< 2\text{ms}$ per provider (NFR-2).
- SSE / WebSocket: N/A.

---

## 6. Layer 5 — State and Hardening (Standard §7)
- **Timezone Normalization (NFR-3):** All datetimes stored as UTC (`TIMESTAMPTZ`). Local date math executes against `ZoneInfo(settings.CLINIC_TIMEZONE)` (e.g. `America/New_York`) to accurately handle daylight saving shifts.
- **Shared State:** No module-level mutable state. Computations are stateless queries against the database.

---

## 7. Errors
| Exception | Raised when | HTTP Status | Error Code |
|---|---|---|---|
| `ShiftOverlapError` | New recurring shift overlaps an existing shift for that dentist on the same day | 409 | `SHIFT_OVERLAP` |
| `InvalidTimeRangeError` | `start_time >= end_time` | 400 | `INVALID_TIME_RANGE` |
| `DentistNotAvailableError` | Dentist has no shifts on the requested date | 200 (empty slots) | — |
| `UnauthorizedScheduleModificationError` | Dentist attempts to modify another dentist's schedule | 403 | `SCHEDULE_FORBIDDEN` |

---

## 8. State Machine
N/A.

---

## 9. Test Seams
| Behaviour | Seam | Notes |
|---|---|---|
| Shift end before start rejected | Schema unit test | `@model_validator` raises ValueError |
| Dynamic slot calculation subtraction | Pure domain unit test (`test_availability.py`) | Tests shift minus appointment minus lunch block = exact remaining slots |
| DST clock transition calculation | Pure domain unit test | Tests 23h and 25h clock change days |
| Dentist cannot edit peer time-off | API test with `dependency_overrides` | Verifies 403 Forbidden |
| Fast response under load | Integration latency test | Validates p95 < 100ms requirement (NFR-2) |

---

## 10. Traceability
| Requirement | Spec Section | Endpoint(s) |
|---|---|---|
| **R-7** Recurring Working Shift Configuration | §2 Contracts, §3 Persistence, §4 Endpoints | `POST /api/v1/schedules/shifts`, `GET /api/v1/schedules/shifts`, `DELETE /api/v1/schedules/shifts/{id}` |
| **R-8** Time-Off & Blocked Interval Management | §2 Contracts, §3 Persistence, §4 Endpoints | `POST /api/v1/schedules/time-off`, `GET /api/v1/schedules/time-off`, `DELETE /api/v1/schedules/time-off/{id}` |
| **R-9** Dynamic Available Slot Calculation | §2 Contracts, §4 Endpoints, §5 Algorithm | `GET /api/v1/schedules/availability` |
| **NFR-2** Availability Query Latency (<100ms) | §5 Algorithm, §9 Test Seams | Evaluated in slot calculation benchmark |
| **NFR-3** Timezone Consistency | §6 State and Hardening | Validated via `CLINIC_TIMEZONE` test suite |

---

## 11. Open Questions / ADRs
- [ADR 0001: Dynamic Slot Computation and Database Overlap Guard](file:///c:/Users/seyi/Documents/Development/Raven/docs/adr/0001-dynamic-slot-computation-and-conflict-prevention.md)
