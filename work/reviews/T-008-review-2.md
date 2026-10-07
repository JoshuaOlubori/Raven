# Review T-008 round 2 — changes-requested

Gates: ruff ? · mypy ? · pytest ? (103 passed)

> **Note:** No fix commit was found between round 1 and round 2. The single commit `1440ac2` (T-008: Appointment booking and atomic overlap guard) is the only T-008 commit. All findings from round 1 are therefore **still present and unaddressed**.

---

## Spec — findings

### ? AC1 — Happy-path booking (R-10)
`test_book_appointment_success_201` drives the public API seam. Status 201, `SCHEDULED`, `end_time = start_time + duration` all asserted. Satisfied.

### ? AC2 — Outside shift hours ? 400 `OUTSIDE_SHIFT_HOURS`
Covered by `test_booking_before_shift_rejected_400`, `_after_`, `_on_non_shift_day_`. Satisfied.

### ? AC3 — Time-off overlap ? 409 `TIME_OFF_CONFLICT`
`test_booking_overlapping_time_off_rejected_409` satisfied.

### ?? BLOCKER — AC4 — Concurrent overlap prevention (NFR-1) — NOT FIXED
**File:** `backend/src/app/db/repository.py:868`
Round-1 finding repeated verbatim: The comment reads
> `# Under PostgreSQL: .with_for_update() ensures serializable conflict rejection`

but `.with_for_update()` is **not called**. Line 869 executes `session.scalar(stmt)` without the lock.
Two concurrent transactions can both read zero overlapping rows, both proceed, and both insert — violating NFR-1.

**Fix direction:** Change to `stmt = stmt.with_for_update(nowait=True)` before the scalar call.

### ? AC5 — No N+1 on list
`test_list_appointments_eager_loading` satisfied.

---

## Standards — findings

### ?? BLOCKER — Missing `with_for_update()` — NOT FIXED
Same as Spec AC4 above. `backend/src/app/db/repository.py:868`.

### ?? MAJOR — `__import__("datetime").timedelta` pattern — NOT FIXED
**File:** `backend/src/app/services/appointment_service.py:102`
Non-idiomatic runtime import. Standard `from datetime import timedelta` import should be at the module top.

**Fix direction:** Add `from datetime import timedelta` to top-level imports.

### ?? MAJOR — Timezone handling inconsistency in helpers — NOT FIXED
**File:** `backend/src/app/services/appointment_service.py:171-174, 211-214`
Both `_validate_shift_coverage` and `_validate_time_off_conflict` re-attach UTC tzinfo defensively, but the caller already strips tzinfo to naive UTC. No clarifying comment was added.

**Fix direction:** Remove redundant tzinfo re-attachment in both helpers; add docstring to `book_appointment` stating helpers receive naive UTC datetimes.

### MINOR — Redundant inner `from sqlalchemy import select` — NOT FIXED
**File:** `backend/src/app/db/repository.py:858`
`select` already imported at module scope (line 12).

---

## Tests — findings

All 103 tests pass. Coverage observations from round 1 unchanged.

### MINOR — Concurrent test relies on unfixed blocker
`backend/tests/api/test_appointments.py:359-361` — test passes vacuously because SQLite serialises requests. Will be meaningful once `.with_for_update()` is added.

---

## Summary — counts per severity; the single worst issue

| Severity | Count | Issues |
|---|---|---|
| **Blocker** | 1 | `check_appointment_overlap` missing `.with_for_update()` — NFR-1 violated |
| **Major** | 2 | `__import__` pattern; redundant tzinfo handling (no clarifying comment) |
| **Minor** | 2 | Redundant inner import; concurrent test relies on unfixed blocker |
| **Nit** | 0 | (Round-1 nits still present but not re-listed) |

**Single worst issue:** `backend/src/app/db/repository.py:868` — `.with_for_update()` absent despite the comment explicitly acknowledging it is required. Breaks NFR-1 in production PostgreSQL.

> ?? This is the second consecutive changes-requested verdict for T-008. If a third round is needed, escalate to the user — the spec or ticket slicing may need revisiting.
