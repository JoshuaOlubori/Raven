# Review T-007 round 1 — Changes Requested
Gates: ruff ✗ · mypy ✓ · pytest ? (not run due to classifier)

## Spec — findings (quote the spec line)

**Blocker:** AC1 not fully tested — spec line "Given a dentist working 09:00–12:00 with an existing appointment 09:00–09:45, When querying slots for a 45-minute service, Then 09:45–10:30 and 10:30–11:15 are returned as available start times (R-9)." The unit test `test_dynamic_slots_subtracts_booked_appointments` (line 108) does not actually test appointment subtraction because the Appointment model doesn't exist yet (T-008) — it only tests the base shift-to-slots generation. The test comment acknowledges "no appointments yet in T-007" but this means the acceptance criterion is untested. The engine code has a placeholder `appointments: list[Appointment] = []` (line 91) with commented-out logic.

**Major:** `AvailabilityQuery` schema defines `dentist_id: UUID | None = None` (schemas.py:344) but the endpoint requires `dentist_id` and returns 400 if missing (schedules.py:234-240). Spec §4 endpoint table lists query params as `dentist_id`, `service_id`, `date` — all three should be required per the endpoint implementation. Either the schema should make `dentist_id` required, or the endpoint should support "all dentists" query. Spec says "Optional UUID of the dentist (defaults to all dentists with shifts)" but this is not implemented.

**Major:** Spec §5 algorithm step 4: "Segment the shift timeline into candidate intervals [t_i, t_i + duration], advancing in 15-minute slot steps (or full duration steps)." The implementation uses hardcoded `step = timedelta(minutes=15)` (availability_engine.py:144) but does not make this configurable or document why 15 minutes. Spec says "or full duration steps" — no rationale for 15 min choice.

**Minor:** Spec §4 endpoint table lists errors as `400, 401, 404, 422` for availability. The implementation returns 400 for missing dentist_id (correct), 422 for missing service_id/date (correct), 404 for invalid service (correct), 401 for unauthenticated (correct). However, the `DentistNotAvailableError` from spec §7 should return 200 with empty slots — this is correctly implemented (returns empty list, 200 OK).

## Standards — findings (cite standard § or smell)

**Blocker:** `availability_engine.py:105` uses quoted forward reference `list["Appointment"]` — UP037 violation. Should be `list[Appointment]` since `from __future__ import annotations` is present (line 9). Ruff flags this.

**Major:** `routers/schedules.py:207-209` uses `Query(...)` calls in argument defaults — B008 violation (do not perform function call in argument defaults). FastAPI pattern: move Query into `Annotated[UUID, Query(...)]` per fastapi-production-architecture §Dependency Injection. Same issue in deps.py:116 (line too long E501).

**Major:** `routers/schedules.py:19` imports unused `AvailabilityQuery` — F401 violation.

**Major:** `availability_engine.py` lines 78, 81, 157 exceed 88 chars — E501 violations. Need line breaks.

**Major:** `tests/unit/test_availability.py` has multiple issues:
- `async_sessionmaker` undefined (F821) — missing import from `sqlalchemy.ext.asyncio`
- Unused imports: `UUID`, `AsyncSession`, `TimeOffBlock` (F401)
- Line 145 exceeds 88 chars (E501)
- `zip()` without `strict=` (B905)
- Missing trailing newline (W292)

**Minor:** `availability_engine.py:144` hardcodes `step = timedelta(minutes=15)` as magic number — Primitive Obsession (Fowler). Should be a class constant or configurable.

**Minor:** `availability_engine.py:91` has placeholder `appointments: list[Appointment] = []` with commented-out logic — Dead Code / Speculative Generality. Since Appointment model doesn't exist, this should be removed or clearly marked as future work with TODO referencing T-008.

**Minor:** `schedules.py:243` uses `datetime.combine(target_date, datetime.min.time())` — `datetime.min.time()` is odd, should be `time.min` or `time(0, 0)`.

**Nit:** `availability_engine.py:8` docstring says "All calculations execute in-memory after a single database roundtrip" — but there are multiple roundtrips (get_service_by_id, list_shifts_by_day, list_time_off_blocks). Should say "after fetching required data in minimal roundtrips".

## Tests — findings

**Blocker:** AC1 (subtract booked appointments) has no test because Appointment model not implemented yet. Test exists but only tests base case without appointments.

**Major:** `test_availability_endpoint_success_200` (test_availability.py:76) asserts `len(body["slots"]) > 0` but does not verify exact expected slot times from the spec. Expected value should come from PRD R-9 (09:00-12:00 shift, 45-min service, 15-min steps = 10 slots), not just "some slots exist". This is a tautological assertion — it would pass even if the algorithm is wrong.

**Major:** `test_availability_endpoint_no_shifts_returns_empty` (line 119) creates a dentist with no shifts but the fixture `availability_dentist` already has a Monday shift. Test creates a second dentist — correct isolation, but test name suggests "no shifts on requested date" which is different from "dentist has no shifts ever". The test correctly queries Tuesday (no shift), so passes.

**Major:** Latency test `test_availability_latency_benchmark` (line 278) uses `time.perf_counter()` around the HTTP call — this measures network + server time, not pure computation. NFR-2 requires "execution time < 100ms under simulated load" for the slot calculation itself. Should test the engine directly in unit test.

**Minor:** No test for DST spring forward on the actual transition day (March 8, 2026) — test uses March 9 (day after). Same for fall back — uses Nov 2 (day after). Should test the actual 23h and 25h days.

**Minor:** `test_dynamic_slots_excludes_time_off_blocks` (line 153) adds time-off block at 12:00-13:00 UTC but shift is 09:00-12:00. The block is outside shift hours so test doesn't actually verify exclusion. The test converts 12:00-13:00 EST to 17:00-18:00 UTC, but shift ends at 12:00 EST = 17:00 UTC. Block starts exactly when shift ends — no overlap. Should test a block that actually overlaps (e.g., 10:00-11:00 EST).

**Minor:** No test for 403 when dentist queries another dentist's schedule (should be allowed per auth matrix "Any staff can query slots for booking").

## Summary — counts per severity; the single worst issue

Blockers: 2 (AC1 untested, ruff failures)
Majors: 6 (unused import, B008 defaults, line length, test gaps, missing imports, undefined names)
Minors: 4 (magic number, dead code, datetime.min.time, test coverage gaps)
Nits: 2 (docstring accuracy, missing DST day test)

**Single worst issue:** AC1 acceptance criterion "subtracts booked appointments" is completely untested — the test exists but does not exercise the subtraction logic because Appointments don't exist yet. This means the core algorithm (shift minus appointments minus time-off = slots) is unverified.