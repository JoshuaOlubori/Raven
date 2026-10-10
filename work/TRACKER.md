# Tracker

_Generated 2026-10-10 06:09 — 11/12 tickets done._

| ID | Title | Status | Mode | Blocked by |
|---|---|---|---|---|
| [T-001](tickets/T-001-walking-skeleton.md) | Walking skeleton and test infrastructure | done | AFK | - |
| [T-002](tickets/T-002-staff-auth-tokens.md) | Staff authentication and token issuance | done | AFK | T-001 |
| [T-003](tickets/T-003-staff-management-rbac.md) | Staff management and RBAC route guards | done | AFK | T-002 |
| [T-004](tickets/T-004-dental-services-catalog.md) | Dental services catalog management | done | AFK | T-003 |
| [T-005](tickets/T-005-patient-management-search.md) | Patient profile management, search, and soft delete | done | AFK | T-003 |
| [T-006](tickets/T-006-dentist-shifts-time-off.md) | Dentist recurring shifts and time-off blocks | done | AFK | T-003 |
| [T-007](tickets/T-007-availability-engine.md) | Dynamic availability calculation engine | done | AFK | T-004, T-006 |
| [T-008](tickets/T-008-appointment-booking-overlap-lock.md) | Appointment booking and atomic overlap guard | done | AFK | T-005, T-007 |
| [T-009](tickets/T-009-appointment-reschedule-cancel.md) | Appointment reschedule and reasoned cancellation | done | AFK | T-008 |
| [T-010](tickets/T-010-appointment-fsm-audit-log.md) | Appointment lifecycle FSM and immutable audit log | done | AFK | T-009 |
| [T-011](tickets/T-011-live-appointment-sse-stream.md) | Real-time live appointment SSE stream | done | AFK | T-010 |
| [T-012](tickets/T-012-confirmations-reminder-dispatcher.md) | Booking confirmations and 24h reminder dispatcher | in-progress | AFK | T-010 |
