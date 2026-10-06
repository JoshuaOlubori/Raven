---
id: T-007
title: Dynamic availability calculation engine
status: todo
mode: AFK
blocked_by: T-004, T-006
spec_refs: specs/04-schedules.md#2-layer-1, specs/04-schedules.md#4-layer-3, specs/04-schedules.md#5-layer-4
covers: R-9, NFR-2, NFR-3
updated: 2026-10-03
---

## Outcome
Staff can query dynamically computed open booking slots for any dentist and dental service on a given date, correctly accounting for shifts, breaks, and booked appointments with sub-100ms response time.

## What to build
- `src/app/services/availability_engine.py`: Pure domain availability computation algorithm (ADR 0001):
  1. Translates target date in `CLINIC_TIMEZONE` to start/end UTC bounds.
  2. Fetches matching shifts, active appointments ($status \neq \text{CANCELLED}$), and time-off blocks.
  3. Steps through shift time windows in discrete candidate intervals matching the requested service duration.
  4. Filters out intervals intersecting busy appointments or time-off blocks.
- `src/app/routers/schedules.py`:
  - `GET /api/v1/schedules/availability` (All staff; query: `dentist_id`, `service_id`, `date`) returning `AvailabilityResponse`.

## Acceptance criteria
- [ ] Given a dentist working 09:00–12:00 with an existing appointment 09:00–09:45, When querying slots for a 45-minute service, Then 09:45–10:30 and 10:30–11:15 are returned as available start times (R-9).
- [ ] Given a dentist with a time-off block (e.g. lunch 12:00–13:00), When querying slots, Then no slots overlapping 12:00–13:00 are returned.
- [ ] Given a day when the dentist has no working shifts, When querying slots, Then an empty list of slots is returned with `200 OK`.
- [ ] Given a target date spanning a Daylight Saving Time transition, When computing slots, Then slot start times align accurately with clinic wall-clock hours (NFR-3).
- [ ] Availability slot lookups execute in under 100ms latency p95 (NFR-2).

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | `test_dynamic_slots_subtracts_booked_appointments` | Pure domain unit | available slot start times match expected list | PRD R-9 |
| 2 | `test_dynamic_slots_excludes_time_off_blocks` | Pure domain unit | no slot overlaps 12:00–13:00 break | Spec 04 §5 |
| 3 | `test_dst_clock_transition_availability_accuracy` | Pure domain unit | correct wall-clock hours on 23h and 25h DST days | NFR-3 |
| 4 | `test_availability_endpoint_success_200` | API + Staff auth | status 200, slots array populated with start/end | PRD R-9 |
| 5 | `test_availability_latency_benchmark` | Integration | execution time < 100ms under simulated load | NFR-2 |

## Out of scope
Booking the slot and creating appointment records (handled in T-008).

## Notes for the implementer
Ensure the slot subtraction algorithm operates entirely in-memory after fetching the day's records in a single database roundtrip.

## Implementation log
- Created `src/app/services/availability_engine.py` with pure domain availability computation algorithm (ADR 0001)
- Added availability schemas (`AvailabilityQuery`, `TimeSlot`, `AvailabilityResponse`) to `schemas.py`
- Added `AvailabilityEngineDep` dependency to `api/deps.py`
- Implemented `GET /api/v1/schedules/availability` endpoint in `routers/schedules.py`
- Created unit tests in `tests/unit/test_availability.py` covering:
  - Dynamic slot calculation subtracting booked appointments
  - Time-off block exclusion
  - DST clock transition accuracy (spring forward and fall back)
  - Helper method tests for overlap detection and timezone conversion
- Created API tests in `tests/api/test_availability_api.py` covering:
  - Success 200 with slots populated
  - Empty slots when no shifts
  - Required parameters validation
  - Invalid service returns 404
  - Unauthenticated returns 401
  - Latency benchmark (<100ms)
  - Query all dentists when dentist_id omitted (per spec)
- Fixed review round 1 issues:
  - Ruff violations (UP037, B008, E501, F401, I001)
  - Made `dentist_id` optional in endpoint (defaults to all dentists with shifts per spec)
  - Replaced hardcoded 15-minute step with `SLOT_STEP` constant
  - Removed dead code placeholder for appointments
  - Fixed `datetime.min.time()` to `time.min`
  - Fixed test issues (missing imports, line lengths, `zip(strict=True)`, trailing newlines)
  - Fixed timezone handling: engine now accepts `date` objects and returns timezone-aware UTC datetimes
  - Fixed test data conflicts by using unique service names

## Review history
