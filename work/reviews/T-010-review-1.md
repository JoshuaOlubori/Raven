# Review T-010 round 1 — Changes requested
Gates: ruff ✓ · mypy ✓ · pytest ✓ (120 passed)

## Spec — findings (quote the spec line)

### ✅ AC1 — FSM valid lifecycle (R-12)
**Spec:** specs/05-appointments.md#8-state-machine. Verified in service transition logic.

### ✅ AC2 — Terminal-state rejection (R-12)
**Spec:** ticket AC. Service raises InvalidStateTransitionError (400 / INVALID_STATUS_TRANSITION).

### ✅ AC3 — Audit log for every transition (R-14)
**Spec:** ticket AC. _create_audit_log called from transition, reschedule, cancel.

### ✅ AC4 — Audit endpoint chronological (R-14)
**Spec:** ticket AC. Endpoint uses ordered query + joinedload actor.

### ❌ BLOCKER — actorName always empty (R-14 broken)
**File:** schemas.py:467-475; endpoint routers/appointments.py:243-267.
AuditLogRead has no actor field → getattr(self,"actor",None) is always None → actorName always "".
Every audit response returns actorName: "".
Fix: declare actor field in schema or inject actorName manually in endpoint.

### ❌ MAJOR — Audit immutability test missing (NFR-4, AC6)
**File:** work/tickets/T-010-appointment-fsm-audit-log.md test plan item 6.
No repository or API test asserts no update/delete exists for audit logs.
Fix: add repository-level or integration immutability test.

### ⚠️ MINOR — AuditLogRead missing actor binding; deprecated datetime.utcnow(); generic update_appointment; actor_role string literal; schema-level test missing.

## Standards — findings

### ❌ MAJOR — Missing eager-loading binding for actor (Standard §4.5, Spec 05 §3)
ORM joinedload present; schema does not bind — Layer-1 / Layer-2 gap.

### ⚠️ MINOR — Generic update_appointment repository footgun (Standard §4 / Fowler).
Deprecated datetime.utcnow() (Standard §1 / Python 3.13).

### ✅ Layer separation, no scattered role checks, Pydantic v2, no blocking/mutable state, naming correct.

## Tests — findings

### ✅ Every AC has a test at named seam (5 ACs covered).
### ❌ MAJOR — actorName value never asserted (test tautology). Presence only checked ("actorName" in log), not value == staff.full_name. Presence assertion passes silently with empty string.
### ❌ MAJOR — Missing audit-immutability test (plan #6).
### ⚠️ MINOR — actor_role string literal; invalid transition asserts message only; no schema-level AuditLogRead validation test.

## Summary
| Severity | Count | Key |
| Blocker | 1 | actor binding breaks R-14 |
| Major | 2 | missing immutability test; actorName value not asserted |
| Minor | 4 | binding; deprecated utcnow; generic update; literal; schema test |
| Nit | 1 | docstring |

Single worst: actor binding gap — silently breaks audit actor names.

Verdict: Changes requested. Fix blocker; address majors before merge.
