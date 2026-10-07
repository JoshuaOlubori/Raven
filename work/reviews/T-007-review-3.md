# Review T-007 round 3 — Changes Requested
Gates: ruff ✓ · mypy ✓ · pytest ✓ (77 passed)

## Spec — findings (quote the spec line)

**Blocker: AC1 (subtract booked appointments) untestable — Appointment model not implemented (T-008)**
Spec line: *"Given a dentist working 09:00–12:00 with an existing appointment 09:00–09:45, When querying slots for a 45-minute service, Then 09:45–10:30 and 10:30–11:15 are returned as available start times (R-9)."*
The unit test `test_dynamic_slots_subtracts_booked_appointments` (test_availability.py:107) does not test appointment subtraction because the Appointment model doesn't exist yet (T-008). The test comment acknowledges "no appointments yet in T-007" and only tests the base shift-to-slots generation. The engine code at lines 92-95 has a comment noting this future work:
```python
# Note: Appointment model not implemented yet (T-008).
# When T-008 is complete, fetch active appointments (status != CANCELLED)
# and include them in busy_intervals.
```
This is a known architectural dependency, not an implementation defect. However, the acceptance criterion remains unverified until T-008.

**Minor: Slot step rationale undocumented**
Spec §5 step 4: *"Segment the shift timeline into candidate intervals [t_i, t_i + duration], advancing in 15-minute slot steps (or full duration steps)."*
The implementation uses `SLOT_STEP = timedelta(minutes=15)` as a class attribute (availability_engine.py:37). No docstring explains why 15 minutes vs. full duration steps. Acceptable but should document the design choice.

**Minor: Endpoint `dentist_id` query param name mismatch with schema**
Spec §2 `AvailabilityQuery` schema defines `dentist_id: UUID | None = None` (schemas.py:344) with camelCase alias. The endpoint uses `dentist_id: Annotated[UUID | None, Query(alias="dentistId")]` (schedules.py:209) — this is correct. The schema's `Field(alias="dentistId")` matches the query parameter naming convention. Verified correct.

## Standards — findings (cite standard § or smell)

**Minor: `SLOT_STEP` class attribute — Primitive Obsession (Fowler)**
`availability_engine.py:37` defines `SLOT_STEP = timedelta(minutes=15)` at class level. While better than a magic number inline and better than module-level constant, a domain constant belongs on the class or in a config object. Not a blocker, but consider `AvailabilityEngine.SLOT_STEP` or a `SlotStep` value object if step size becomes configurable.

**Major: Multiple database roundtrips in "all dentists" query path (N+1 problem)**
`schedules.py:263-300` — when `dentist_id` is omitted, the endpoint:
1. Calls `list_shifts_by_day` (1 roundtrip)
2. For each dentist with shifts, calls `get_staff_by_id` (N roundtrips)
3. For each dentist, calls `engine.get_available_slots` which internally calls `get_service_by_id`, `list_shifts_by_day`, `list_time_off_blocks` (3N roundtrips)
Total: 1 + N + 3N roundtrips. Spec §5 says *"Ensure the slot subtraction algorithm operates entirely in-memory after fetching the day's records in a single database roundtrip."* The single-dentist path achieves this (3 roundtrips); the all-dentists path does not. This is a performance concern for NFR-2 (<100ms) at scale.

**Nit: Docstring slightly overstates in-memory claim**
`availability_engine.py:6` docstring: *"All calculations execute in-memory after fetching required data in minimal database roundtrips."* The single-dentist path uses 3 roundtrips (service, shifts, time-off). "Minimal" is accurate; "single" would not be.

**Fixed since round 2:** `datetime.combine(target_date, time.min)` pattern now extracted to shared utility `app.utils.datetime_utils.date_to_midnight_local` (schedules.py:258, availability_engine.py:69) — DRY and DST consistency achieved.

## Tests — findings

**Blocker: AC1 (appointment subtraction) has no test**
As noted in Spec — the core algorithm (shift minus appointments minus time-off = slots) is unverified because Appointments don't exist yet. The test exists but only exercises the base case.

**Fixed since round 2:** `test_availability_endpoint_success_200` now has exact-value assertions
`test_availability_api.py:115-156` asserts exact 10 slot start times (09:00, 09:15, ..., 11:15) per PRD R-9. Expected values hard-coded in test from spec, not derived from implementation. ✓

**Fixed since round 2:** Pure-unit latency benchmark added
`test_availability_engine_latency_benchmark` (test_availability.py:397) measures engine directly, not HTTP roundtrip. Runs 50 iterations, asserts p95 < 100ms. ✓

**Fixed since round 2:** DST transition tests use actual transition days
`test_dst_spring_forward_availability` uses `date(2026, 3, 8)` (actual DST spring forward day). `test_dst_fall_back_availability` uses `date(2026, 11, 1)` (actual DST fall back day). Both with new `sunday_shift` fixture. ✓

**Fixed since round 2:** `test_dynamic_slots_excludes_time_off_blocks` tests overlapping block
Test now adds time-off block at 10:00-11:00 EST (overlaps 09:00-12:00 shift). Verifies exclusion correctly. ✓

**Format nit: `tests/api/test_availability_api.py:151` line length exceeds 88 chars**
Ruff format would reformat the `expected_end` calculation line. This is a style issue, not a functional one.

## Summary — counts per severity; the single worst issue

| Severity | Count |
|----------|-------|
| blocker | 1 (AC1 untestable - architectural dependency on T-008) |
| major | 1 (N+1 roundtrips in all-dentists path) |
| minor | 2 (slot step primitive obsession, slot step rationale undocumented) |
| nit | 2 (docstring precision, test format line length) |

**Single worst issue:** **Blocker** — AC1 "subtracts booked appointments" is completely untested. The test exists but does not exercise the subtraction logic because the Appointment model (T-008) is not implemented. This is a known dependency, not a code defect, but it means the ticket cannot be fully approved until T-008 provides the Appointment model.

The N+1 roundtrip issue in the "all dentists" query path is a **Major** standards violation that could impact NFR-2 at scale. For a clinic with 20 dentists, this means ~120 roundtrips vs 3 for single-dentist.

**Verdict: changes requested** — Blocker and major must be addressed. The AC1 blocker is architectural (depends on T-008); the N+1 roundtrip is fixable now by batching `get_staff_by_id` and/or reusing shifts/time-off data already fetched. Recommend: optimize the all-dentists path to use a single query for all dentist names and reuse shift/time-off data per dentist. The AC1 gap will be resolved when T-008 lands.