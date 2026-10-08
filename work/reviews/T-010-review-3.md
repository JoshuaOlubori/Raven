# Review T-010 round 3 — Approve (post-fix verification)
Gates: ruff ✓ · format ✓ · mypy ✓ · pytest ✓ (121 passed)

Note: This is the third review round on T-010. The spec/slicing question was confirmed: CANCELLED bypass is an implementation omission (not a spec change); audit datetime should be consistently tz-aware. The omissions from review 2 (CANCELLED exclusion in service `_VALID_TRANSITIONS`; weak audit immutability test) were fixed before this review. All 3 majors from review 2 are now addressed.

## Spec — findings (post-fix verification, quote spec line)

### ✅ AC1 — FSM valid lifecycle (R-12)
**Spec:** specs/05-appointments.md §8 (lines 176-185): `SCHEDULED -> CONFIRMED -> CHECKED_IN -> IN_PROGRESS -> COMPLETED`.
**Code:** `service.py:429-437` (`_VALID_TRANSITIONS` — CANCELLED excluded from allowed transitions); `router:216-253` (`POST /status`).
**Test:** `test_fsm_valid_lifecycle_transitions` asserts full chain.

### ✅ AC2 — Terminal-state rejection (R-12)
**Spec:** specs/05-appointments.md §8 (lines 173-174): `COMPLETED`, `CANCELLED`, `NO_SHOW` terminal.
**Code:** `service:487-491` rejects terminal; raises `InvalidStateTransitionError` (400 / `INVALID_STATUS_TRANSITION`).
**Test:** `test_fsm_terminal_state_rejected_400` (api:946) covers terminal states.

### ✅ AC3 — Audit log for every transition/reschedule/cancel (R-14)
**Spec:** specs/05-appointments.md §2 line 36 (`AuditLogRead` fields), §3 lines 42-46 (`AppointmentAuditLog` model).
**Code:** `service:521-549` (`_create_audit_log`); `service:265-273` (reschedule), `335-343` (cancel), `508-516` (status transition); `repository:504-532` (`create_audit_log`).
**Test:** `test_status_transition_creates_audit_log_entry` (api:1060) asserts `actorId`, `fromStatus`, `toStatus`, `actorName`, `note`, `createdAt`.

### ✅ AC4 — Audit endpoint chronological with actor names (R-14)
**Spec:** specs/05-appointments.md §4 line 93: `GET /audit-logs` -> `list[AuditLogRead]`.
**Code:** `router:261-279` (`GET /audit-logs`); `service:556-566` (`get_audit_logs` uses `joinedload`); `repository:536-551` (`list_audit_logs_for_appointment` with `joinedload` + `order_by`).
**Schema:** `schemas.py:452-473` (`AuditLogRead` with `actor: StaffRead`, computed `actor_name`).
**Test:** `test_audit_logs_endpoint_returns_chronological_history` (api:1114) asserts `createdAt` ascending; `test_status_transition_creates_audit_log_entry` asserts `actorName == staff.full_name`.

### ✅ AC5 — No mutation endpoints for audit (NFR-4)
**Spec:** specs/05-appointments.md §6 line 135: "No UPDATE or DELETE endpoints exist for `appointment_audit_logs`." §3 line 46: append-only.
**Code:** Router provides only `GET /audit-logs`; repository has `create_audit_log` and `list_audit_logs_for_appointment` — no update/delete.
**Test:** `test_audit_log_immutability_no_update_or_delete` (api:1253) asserts absence of mutation functions by inspection and by attribute check.

### ✅ AC6 — CANCELLED bypass fixed (spec deviation resolved)
**Spec:** specs/05-appointments.md §2 line 32: `AppointmentStatusUpdate` — "Target status must not be CANCELLED."
**Fix applied:** `service.py:430-432` — CANCELLED removed from allowed transitions (`SCHEDULED`, `CONFIRMED`, `CHECKED_IN`); schema `model_validator` (line 453-456) already rejects CANCELLED. The bypass via `POST /status` is now blocked at the service layer.

### ✅ AC7 — Audit datetime consistency (NFR-3 / tz-invariant)
**Fix verified:** `service.py:106-107`, `226-227` — `start_time` / `new_start_time` converted with `.astimezone(ZoneInfo("UTC"))` (tz-aware); `audit.py:49` — `created_at` uses `utcnow()` (tz-aware). All audit datetime fields are consistently timezone-aware.

## Standards — findings (post-fix)

### ✅ CANCELLED bypass fixed (Standard §2 / Spec 05 §2)
Service `_VALID_TRANSITIONS` no longer permits `CANCELLED`; only `POST /cancel` with mandatory `NonEmptyStr` `cancellation_reason` (R-13) can transition to CANCELLED.

### ✅ Audit datetime invariant restored (Standard §4 / NFR-3)
All audit fields (`created_at`, `old_start_time`, `new_start_time`) are now consistently timezone-aware UTC; no naive/tz-aware mix remains.

### ✅ Audit immutability test strengthened (Standard §9 / test-plan #6)
Behavioral mutation assertion added confirming no mutation functions exist by design.

### ⚠️ Minor — Generic `update_appointment` repository footgun remains (`db/repository.py:485-496`). Unfixed from T-009; does not affect T-010 audit logic. Not blocking.
### ⚠️ Minor — `actor_role` string literal (`service:494-497`); `_shift_covers_window` data clump (`service:410-415`); missing schema-level `AuditLogRead` validation test; `test_receptionist_..._403` name claims 403 but asserts 400; `.with_for_update` deviation (`repository:452`). Pre-existing; not introduced by this ticket.

### ✅ Layer separation / no scattered role checks / Pydantic v2 / eager loading / no mutable state
Router thin; all FSM rules in service; `require_roles` dependency used; `joinedload` on actor; Pydantic v2; no module-level mutable state.

## Tests — findings

### ✅ All 6 AC tests present and passing (121 passed)
Plan items 1-6 covered (`test_fsm_valid_lifecycle_transitions`, `test_fsm_terminal_state_rejected_400`, `test_fsm_dentist_only_transitions`, `test_status_transition_creates_audit_log_entry`, `test_audit_logs_endpoint_returns_chronological_history`, `test_audit_log_immutability_no_update_or_delete`).

### ✅ Audit immutability test strengthened (behavioral mutation assertion)
Added mutation assertion confirming no mutation functions exist by design.

### ⚠️ Minor — Pre-existing optional test gaps (test name mismatch, missing 404 audit endpoint test, missing schema-level validation test). Not blocking.

## Summary
| Severity | Count | Key |
| Blocker | 0 | — |
| Major | 0 | All 3 majors from round 2 fixed (CANCELLED bypass, tz invariant, immutability test) |
| Minor | 5 | Pre-existing (update footgun, role literal, data clump, missing schema test, test name, `.with_for_update`) |
| Nit | 0 | — |

Single best improvement completed: CANCELLED bypass closed at service layer (`_VALID_TRANSITIONS`) plus schema validator; audit datetime fully tz-aware; audit immutability strengthened with behavioral mutation assertion.

Verdict: **Approve** (all majors fixed; gates green; spec met; no new blockers or majors introduced).
Note: This is the third review round on T-010 (two prior changes-requested rounds). All root-cause omissions confirmed and fixed before this review.
