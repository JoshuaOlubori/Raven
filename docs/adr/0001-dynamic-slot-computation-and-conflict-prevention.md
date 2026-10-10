# 1. Dynamic Slot Computation and Database Overlap Guard

- **Status:** Accepted
- **Date:** 2026-10-03
- **Deciders:** Product Owner, Engineering

## Context
In a dental clinic appointment scheduling system, appointments have varying durations depending on the procedure (e.g. 30-minute checkup vs. 90-minute root canal). The system must allow staff to query available appointment slots and guarantee zero double-booking across concurrent booking operations.

Two main approaches were considered:
1. **Pre-generated discrete slot table:** Pre-populating a database table with fixed interval slots (e.g. 15-minute or 30-minute blocks) and reserving rows.
2. **Dynamic interval computation with transaction-level overlap checking:** Calculating availability on-the-fly based on dentist shifts minus booked appointments and time-off blocks, and enforcing collision prevention during booking via database transactions and conflict queries.

## Decision
We chose **Dynamic Interval Computation with Database Overlap Enforcement**:
- Available slots are generated on-the-fly when queried: Dentist working shifts minus active (non-cancelled) appointments and blocked intervals, chunked into intervals matching the requested service duration.
- Booking and rescheduling transactions perform an atomic overlap check within the database transaction (using pessimistic locking or temporal range exclusion). Any concurrent write attempting to book an overlapping interval for the same dentist is rejected with HTTP `409 Conflict`.
- The implementation locks the stable dentist row before checking appointments. This serializes overlapping checks even when the appointment query returns no rows; booking and rescheduling hold that lock through commit.

## Consequences
### Positive
- Flexible appointment durations without table bloat or arbitrary slot discretization.
- Shift changes and ad-hoc time-off blocks take immediate effect without needing batch table regeneration.
- Works reliably across multiple worker processes without external distributed locks.

### Negative / Trade-offs
- Slot query calculation requires runtime interval subtraction rather than a simple `SELECT * FROM slots WHERE is_booked = false`. For clinic scale (up to 20 providers, 200 appointments/day), this runtime cost is negligible (<5ms).
