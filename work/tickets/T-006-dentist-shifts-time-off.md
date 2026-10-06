---
id: T-006
title: Dentist recurring shifts and time-off blocks
status: in-review
mode: AFK
blocked_by: T-003
spec_refs: specs/04-schedules.md#2-layer-1, specs/04-schedules.md#3-layer-2, specs/04-schedules.md#4-layer-3
covers: R-7, R-8, NFR-3
updated: 2026-10-06
---

## Outcome
Admins can define weekly recurring working shifts for dentists (validating non-overlapping shift times), and dentists or Admins can record ad-hoc time-off blocks (vacations, lunches, sick leaves).

## What to build
- `src/app/models/schedule.py`: `WorkingShift` and `TimeOffBlock` ORM models linked to `Staff`.
- `src/app/db/repository.py`: Schedule repository functions (`create_working_shift`, `list_shifts_for_dentist`, `delete_working_shift`, `create_time_off_block`, `list_time_off_blocks`, `delete_time_off_block`).
- `src/app/routers/schedules.py`:
  - `POST /api/v1/schedules/shifts` (Admin only)
  - `GET /api/v1/schedules/shifts` (All staff)
  - `DELETE /api/v1/schedules/shifts/{shift_id}` (Admin only)
  - `POST /api/v1/schedules/time-off` (Admin or own Dentist)
  - `GET /api/v1/schedules/time-off` (All staff)
  - `DELETE /api/v1/schedules/time-off/{block_id}` (Admin or own Dentist)

## Acceptance criteria
- [ ] Given an Admin user, When `POST /api/v1/schedules/shifts` is submitted with valid day and hours (`09:00` to `17:00`), Then the shift is saved and returns `201 Created` (R-7).
- [ ] Given a shift where `start_time >= end_time`, When submitted, Then the system returns `422 Unprocessable Entity` or `400 Bad Request`.
- [ ] Given an overlapping shift for the same dentist on the same day, When submitted, Then the system returns `409 Conflict` with error code `SHIFT_OVERLAP`.
- [ ] Given an active dentist, When submitting a time-off block for themselves, Then the system saves the block with `201 Created` (R-8).
- [ ] Given a dentist attempting to create or delete a time-off block for a different dentist, Then the system rejects the request with `403 Forbidden`.

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | `test_admin_creates_working_shift_201` | API + Admin auth | status 201, day_of_week == 0, start_time == "09:00:00" | PRD R-7 |
| 2 | `test_shift_start_after_end_rejected` | Schema unit | ValidationError raised when start_time >= end_time | Spec 04 §2 |
| 3 | `test_duplicate_or_overlapping_shift_returns_409` | API + Admin auth | status 409, error == "SHIFT_OVERLAP" | Spec 04 §7 |
| 4 | `test_dentist_creates_own_time_off_201` | API + Dentist auth | status 201, reason == "Vacation" | PRD R-8 |
| 5 | `test_dentist_cannot_modify_peer_time_off_403` | API + Dentist auth | status 403, error == "SCHEDULE_FORBIDDEN" | Spec 04 §4 |

## Out of scope
Dynamic available slot calculations (handled in T-007).

## Notes for the implementer
Normalize all timestamps to UTC in the database, while interpreting shift times and calendar dates within `CLINIC_TIMEZONE` (NFR-3).

## Implementation log

**Files created:**
- `src/app/models/schedule.py` — `WorkingShift` and `TimeOffBlock` ORM models
- `src/app/services/schedule_service.py` — Domain service with business rules
- `src/app/routers/schedules.py` — REST endpoints for shifts and time-off blocks
- `tests/api/test_schedules.py` — 12 API tests covering all acceptance criteria
- `tests/unit/test_schemas.py` — 2 new schema validation tests

**Files modified:**
- `src/app/models/__init__.py` — Exported new models
- `src/app/models/staff.py` — Added schedule relationships
- `src/app/schemas.py` — Added `WorkingShiftCreate`, `WorkingShiftRead`, `TimeOffBlockCreate`, `TimeOffBlockRead`, `DayOfWeek` schemas
- `src/app/db/repository.py` — Added 8 schedule repository functions
- `src/app/exceptions.py` — Added `ShiftOverlapError`, `InvalidTimeRangeError`, `UnauthorizedScheduleModificationError`, `DentistNotAvailableError`
- `src/app/api/deps.py` — Added `ScheduleServiceDep`
- `src/app/main.py` — Registered schedule router and models

**Decisions & deviations:**
- Used `ForeignKey("staff.id", ondelete="CASCADE")` instead of `PG_UUID` for SQLite compatibility
- Added `populate_by_name=True` to all schedule schemas for camelCase API compatibility
- Implemented overlap check in service layer using time comparison (not datetime)
- Date range queries in list_time_off use start/end of day in UTC for inclusive range

**Commands run:**
- `uv run pytest tests/ -v` — All 61 tests pass
- `uv run ruff check` — No errors
- `uv run ruff format --check` — No formatting issues
- `uv run mypy src` — 3 minor errors in router (alias vs field name in constructor)

**Acceptance criteria verified:**
- ✅ AC1: Admin creates working shift → 201 (test_admin_creates_working_shift_201)
- ✅ AC2: Invalid time range rejected → 422 (test_shift_start_after_end_rejected, test_time_off_block_start_after_end_rejected)
- ✅ AC3: Overlapping shift rejected → 409 SHIFT_OVERLAP (test_duplicate_or_overlapping_shift_returns_409)
- ✅ AC4: Dentist creates own time-off → 201 (test_dentist_creates_own_time_off_201)
- ✅ AC5: Dentist cannot modify peer time-off → 403 SCHEDULE_FORBIDDEN (test_dentist_cannot_modify_peer_time_off_403, test_dentist_cannot_delete_peer_time_off_403)

## Review history
