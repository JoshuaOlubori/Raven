# Review T-010 round 2 — Changes requested
Gates: ruff ✓ · format ✓ · mypy ✓ · pytest ✓ (121 passed)
## Spec — findings (quote spec line)

### ✅ AC1 — FSM valid lifecycle (R-12)
**Spec:** specs/05-appointments.md §8 (lines 176-185): `SCHEDULED -> CONFIRMED -> CHECKED_IN -> IN_PROGRESS -> COMPLETED`.
**Code:** `appointment_service.py:429-437` (`_VALID_TRANSITIONS`); `router:216-253` (`POST /status`).
**Test:** `test_fsm_valid_lifecycle_transitions` (unit:432) asserts full chain.

### ✅ AC2 — Terminal-state rejection (R-12)
**Spec:** specs/05-appointments.md §8 (lines 173-174): `COMPLETED`, `CANCELLED`, `NO_SHOW` terminal.
**Code:** `service:481-484` rejects terminal; raises `InvalidStateTransitionError` (error code `INVALID_STATUS_TRANSITION`, 400).
**Test:** `test_fsm_terminal_state_rejected_400` (api:946) and `test_fsm_terminal_state_rejects_transition` (unit:483) cover COMPLETED/CANCELLED/NO_SHOW.

### ❌ MAJOR — `AppointmentStatusUpdate` allows CANCELLED, bypassing R-13 reason guard
**Spec:** specs/05-appointments.md §2 line 32: `AppointmentStatusUpdate` — "Target status must not be CANCELLED (cancellation uses dedicated endpoint)." §8 (line 183): Cancel uses `AppointmentCancel` with mandatory non-empty `cancellation_reason`.
**Code:** `schemas.py:443-449` — `AppointmentStatusUpdate` has `to_status: AppointmentStatus` with no validator excluding `CANCELLED`. `_VALID_TRANSITIONS` (service:429-437) allows `SCHEDULED/CONFIRMED/CHECKED_IN -> CANCELLED`. A call to `POST /api/v1/appointments/{id}/status` with `{"toStatus":"CANCELLED","note":"..."}` bypasses `POST /cancel` and its `NonEmptyStr` `cancellation_reason` validation (R-13, spec §2 line 34).
**Fix direction:** Add Pydantic `model_validator` to `AppointmentStatusUpdate` rejecting `to_status == "CANCELLED"` with `ValueError` (or `422`); or add `CANCELLED` exclusion in service and return `400 INVALID_STATUS_TRANSITION`.
**Status:** Unfixed — no test covers this bypass path.

### ✅ AC3 — Audit log for every transition/reschedule/cancel (R-14)
**Spec:** specs/05-appointments.md §2 line 36 (`AuditLogRead` fields), §3 lines 42-46 (`AppointmentAuditLog` model).
**Code:** `service:520-549` (`_create_audit_log`); `service:265-273` (reschedule), `335-343` (cancel), `508-516` (status transition); `db/repository.py:504-532` (`create_audit_log`).
**Test:** `test_status_transition_creates_audit_log_entry` (api:1060) asserts `actorId`, `fromStatus`, `toStatus`, `actorName`, `note`, `createdAt`.

### ✅ AC4 — Audit endpoint chronological with actor names (R-14)
**Spec:** specs/05-appointments.md §4 line 93: `GET /audit-logs` → `list[AuditLogRead]`.
**Code:** `router:261-279` (`GET /audit-logs`); `service:555-565` (`get_audit_logs` uses `joinedload`); `db/repository.py:535-550` (`list_audit_logs_for_appointment` with `joinedload` + `order_by`).
**Schema:** `schemas.py:452-473` (`AuditLogRead` with `actor: StaffRead`, computed `actor_name`).
**Test:** `test_audit_logs_endpoint_returns_chronological_history` (api:1114) asserts `createdAt` ascending and all fields present; `test_status_transition_creates_audit_log_entry` asserts `actorName == staff.full_name` (line 1110) — value assertion, not tautological.

### ✅ AC5 — No mutation endpoints for audit (NFR-4)
**Spec:** specs/05-appointments.md §6 line 135: "No UPDATE or DELETE endpoints exist for `appointment_audit_logs`." §3 line 46: append-only.
**Code:** Router provides only `GET /audit-logs`; repository has `create_audit_log` and `list_audit_logs_for_appointment` — no update/delete.
**Test:** `test_audit_log_immutability_no_update_or_delete` (api:1251) asserts `audit_functions == []`.

### ✅ Previous round 1 fixes verified
- **B1 (actor binding):** `schemas.py:467` (`actor: StaffRead`); endpoint returns real `actorName` via eager-loaded `joinedload`.
- **M2 (audit immutability test):** Added at `test_appointments.py:1251`.
- **M3 (actorName value assertion):** `test_appointments.py:1110` asserts `actorName == receptionist_staff.full_name`.
- **Minor (deprecated utcnow):** `models/audit.py:49` uses `utcnow()` (timezone-aware from `base.py:19`); no `datetime.utcnow()` remains.

## Standards — findings (cite standard § or smell)

### ✅ Layer separation, no handler business logic
Router is thin (`router:216-253`); all FSM rules in `service:429-518`.

### ✅ No scattered role checks / Pydantic v2 / eager loading
`require_roles` dependency (`router:219`); `joinedload` on actor (`repository.py:545`); Pydantic v2 (`ConfigDict`, `computed_field`).

### ❌ MAJOR — Spec deviation: CANCELLED bypass via status endpoint (Standard §2 / Spec 05 §2)
As above: `AppointmentStatusUpdate` does not enforce spec §2 line 32 ("Target status must not be CANCELLED"). This allows an API client to skip the dedicated cancellation endpoint, bypassing the mandatory `NonEmptyStr` `cancellation_reason` validator (spec §2 line 34, R-13). Fix: add validator.

### ❌ MAJOR — NFR-3 tzinfo invariant violation (Standard §4 / audit immutability consistency)
`audit.py:49`: `created_at: Mapped[datetime] = mapped_column(default=utcnow)` — `utcnow()` (base.py:19) returns `datetime.now(UTC)`, which is **timezone-aware** (`tzinfo=UTC`).
`service.py:104-105`, `224-227`: `start_time` / `new_start_time` are converted to **naive** UTC (`.replace(tzinfo=None)`).
`audit.py:46-47`: `old_start_time` / `new_start_time` store these naive UTC values.
`audit.py:49`: `created_at` is tz-aware.
Same row in `appointment_audit_logs` mixes tz-aware (`created_at`) and naive (`old_start_time`, `new_start_time`) `datetime` columns. Under PostgreSQL (`timestamp with time zone` vs `timestamp without time zone`), this causes silent timezone corruption or comparison errors. Fix: make all stored `datetime` fields consistent — either all tz-aware (remove `.replace(tzinfo=None)` in service) or all naive (change `utcnow()` to naive UTC and document); prefer tz-aware consistently per spec.

### ⚠️ Minor — Generic `update_appointment` repository footgun remains
`db/repository.py:485-496`. Unfixed from T-009; does not affect this ticket's audit logic.

### ⚠️ Minor — `actor_role` string literal (`service:494-500`); `_shift_covers_window` data clump (`service:410-415`); missing schema-level `AuditLogRead` validation test (Standard §9 / test-plan #6 gap); `test_receptionist_..._403` name vs 400 behavior; `repository:452` `.with_for_update(nowait=True)` deviation from spec §5.

## Tests — findings

### ✅ All 6 AC tests present
Plan items 1-6 verified (`test_fsm_valid_lifecycle_transitions`, `test_fsm_terminal_state_rejected_400`, `test_fsm_dentist_only_transitions`, `test_status_transition_creates_audit_log_entry`, `test_audit_logs_endpoint_returns_chronological_history`, `test_audit_log_immutability_no_update_or_delete`).

### ❌ MAJOR — Audit immutability test is contract-level, not behavioral
`test_audit_logs_are_immutable` (api:1251) asserts absence of functions named `update_`/`delete_` mentioning "audit" via `inspect.getmembers`. It does not attempt actual SQL mutation (`DELETE FROM ...`, `UPDATE ...`) or ORM mutation (`session.delete(audit_log)`). A malicious or erroneous repository function with a different name (e.g., `modify_audit`) would pass this test. Fix: add integration test that tries to delete/update an audit record and asserts persistence.

### ⚠️ Minor — `test_receptionist_cannot_transition_to_in_progress_403` asserts 400 (correct behavior) but name claims 403; no 404 (NOT_FOUND) test for audit endpoint.

## Summary

| Severity | Count | Key |
|---|---|---|
| Blocker | 0 | — |
| Major | 3 | CANCELLED bypass via `/status` (spec violation); tz-aware/naive datetime mix (NFR-3); weak immutability test |
| Minor | 6 | Generic update_appointment; actor_role literal; data clump; missing schema validation test; test name mismatch; `.with_for_update` deviation |
| Nit | 0 | — |

Single worst: **CANCELLED bypass via `/status` endpoint** breaks R-13's mandatory cancellation-reason guard (spec deviation with security/business-rule impact). Second worst: **tzinfo invariant violation** risks silent database corruption.

This is the **second changes-requested round** on T-010 (round 1 was B1/M2/m4/n1; this round adds M1 new spec deviation + M2 new NFR-3 invariant + M3 weak immutability test). Before proceeding, confirm: is the CANCELLED bypass intended (spec should be updated to allow it), or is it an implementation omission? Same question for the tz-invariant: should audit `created_at` be naive to match other audit fields, or should all fields become tz-aware?

Verdict: **Changes requested** (2 new majors: CANCELLED bypass, tz invariant; 1 strengthened major: weak immutability test). Gates remain green; no regression.
