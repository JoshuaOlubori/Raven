# Review T-007 round 2 — changes requested
Gates: ruff ✓ · mypy ✓ · pytest ✓ (all tests pass)

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

**Major: `test_availability_endpoint_success_200` uses tautological assertion**
Spec line: PRD R-9 defines exact expected slots for 09:00-12:00 shift with 45-min service and 15-min steps.
The API test `test_availability_endpoint_success_200` (test_availability_api.py:77) only asserts `len(body["slots"]) > 0` and validates slot structure. It does not verify the exact 10 expected slot start times (09:00, 09:15, ..., 11:15). Expected value should come from the spec, not from "some slots exist" — this would pass even if the algorithm is wrong.

**Minor: `AvailabilityQuery` schema allows optional `dentist_id` but endpoint now supports "all dentists" query correctly**
Spec §4 endpoint table: query params `dentist_id`, `service_id`, `date` — "Optional UUID of the dentist (defaults to all dentists with shifts)".
The endpoint implementation (schedules.py:204-311) correctly handles `dentist_id=None` by querying all dentists with shifts on the target weekday. This was fixed since round 1 — no longer a deviation.

**Minor: Slot step rationale undocumented**
Spec §5 step 4: *"Segment the shift timeline into candidate intervals [t_i, t_i + duration], advancing in 15-minute slot steps (or full duration steps)."*
The implementation uses `SLOT_STEP = timedelta(minutes=15)` (availability_engine.py:25) as a module constant. No docstring explains why 15 minutes vs. full duration steps. Acceptable but should document the design choice.

## Standards — findings (cite standard § or smell)

**Minor: `SLOT_STEP` module constant — Primitive Obsession (Fowler)**
`availability_engine.py:25` defines `SLOT_STEP = timedelta(minutes=15)` at module level. While better than a magic number inline, a domain constant belongs on the class or in a config object. Not a blocker, but consider `AvailabilityEngine.SLOT_STEP` or a `SlotStep` value object if step size becomes configurable.

**Minor: Multiple database roundtrips in "all dentists" query path**
`schedules.py:263-300` — when `dentist_id` is omitted, the endpoint:
1. Calls `list_shifts_by_day` (1 roundtrip)
2. For each dentist with shifts, calls `get_staff_by_id` (N roundtrips)
3. For each dentist, calls `engine.get_available_slots` which internally calls `get_service_by_id`, `list_shifts_by_day`, `list_time_off_blocks` (3N roundtrips)
Total: 1 + N + 3N roundtrips. Spec §5 says *"Ensure the slot subtraction algorithm operates entirely in-memory after fetching the day's records in a single database roundtrip."* The single-dentist path achieves this (3 roundtrips); the all-dentists path does not. This is a performance concern for NFR-2 (<100ms).

**Nit: Docstring slightly overstates in-memory claim**
`availability_engine.py:6` docstring: *"All calculations execute in-memory after fetching required data in minimal database roundtrips."* The single-dentist path uses 3 roundtrips (service, shifts, time-off). "Minimal" is accurate; "single" would not be.

**Nit: `datetime.combine(target_date, time.min)` pattern repeated**
`schedules.py:258`, `availability_engine.py:69` — both construct a timezone-aware midnight datetime. Could extract to a shared utility (`date_to_midnight_utc(date, tz)`) for DRY and DST consistency.

## Tests — findings

**Blocker: AC1 (appointment subtraction) has no test**
As noted in Spec — the core algorithm (shift minus appointments minus time-off = slots) is unverified because Appointments don't exist yet. The test exists but only exercises the base case.

**Major: `test_availability_endpoint_success_200` lacks exact-value assertions**
`test_availability_api.py:77-118` asserts `len(body["slots"]) > 0` but does not verify the exact 10 slot start times specified in R-9. Expected values must come from the spec (hard-coded in test), not from the implementation.

**Major: Latency test measures HTTP roundtrip, not pure computation**
`test_availability_latency_benchmark` (test_availability_api.py:305) uses `time.perf_counter()` around the `client.get()` call. NFR-2 requires *"execution time < 100ms under simulated load"* for the slot calculation itself. Should add a unit test calling `AvailabilityEngine.get_available_slots` directly with a benchmark fixture.

**Minor: DST transition tests use day after transition, not the actual transition day**
`test_dst_spring_forward_availability` uses `date(2026, 3, 9)` (Monday after DST spring forward on March 8). `test_dst_fall_back_availability` uses `date(2026, 11, 2)` (Monday after DST fall back on November 1). Should test the actual 23-hour day (March 8) and 25-hour day (November 1) to verify wall-clock alignment on the transition day itself.

**Minor: `test_dynamic_slots_excludes_time_off_blocks` doesn't test overlapping block**
`test_availability.py:162-209` adds a time-off block at 12:00-13:00 EST (17:00-18:00 UTC) but the shift ends at 12:00 EST (17:00 UTC). The block starts exactly when the shift ends — no overlap. The test should add a block that actually overlaps the shift (e.g., 10:00-11:00 EST) to verify exclusion logic.

**Minor: No test for unauthenticated 401 on availability endpoint** — actually exists: `test_availability_unauthenticated_rejected_401` ✓

## Summary — counts per severity; the single worst issue

| Severity | Count |
|----------|-------|
| blocker | 2 (AC1 untestable, API test tautological) |
| major | 2 (latency test measures wrong thing, no exact-value assertions) |
| minor | 4 (slot step primitive obsession, N+1 roundtrips in all-dentists path, DST test day, time-off overlap test) |
| nit | 2 (docstring precision, repeated datetime combine) |

**Single worst issue:** **Blocker** — AC1 "subtracts booked appointments" is completely untested. The test exists but does not exercise the subtraction logic because the Appointment model (T-008) is not implemented. This means the core algorithm (shift − appointments − time-off = slots) is unverified. This is a known dependency, not a code defect, but it means the ticket cannot be fully approved until T-008 provides the Appointment model.

**Verdict: changes requested** — Blockers and majors must be addressed. The AC1 blocker is architectural (depends on T-008); the tautological test and latency test are fixable now. Recommend: add exact-value assertions to `test_availability_endpoint_success_200`, add a pure-unit latency benchmark for the engine, and fix the time-off overlap test. The AC1 gap will be resolved when T-008 lands.