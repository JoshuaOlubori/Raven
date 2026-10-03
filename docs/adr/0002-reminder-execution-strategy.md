# 2. Dual-Mode 24-Hour Pre-Appointment Reminder Execution

- **Status:** Accepted
- **Date:** 2026-10-03
- **Deciders:** Product Owner, Engineering

## Context
Functional requirement R-17 requires the system to periodically scan for upcoming appointments starting within 23–25 hours that have not yet had a reminder sent (`reminder_sent_at` is null), and dispatch reminders.
Non-functional requirement NFR-5 dictates stateless multi-worker operations. If multiple Uvicorn worker processes are launched, running uncontrolled in-memory periodic background loops across all workers could cause duplicate reminders or lock contention.

## Decision
We chose a **Dual Execution Pattern**:
1. **Protected Maintenance Endpoint:** `POST /api/v1/appointments/reminders/dispatch` protected by `ADMIN` role or a dedicated system API key (`X-Internal-Token`). External schedulers (Kubernetes CronJob, AWS EventBridge, systemd timer) can invoke this endpoint periodically (e.g. every 15 minutes) in multi-worker environments.
2. **Optional In-Process Lifespan Loop:** When running in single-worker / development mode (`ENABLE_IN_PROCESS_REMINDER_WORKER=true`), a lightweight asyncio background task is launched during the FastAPI `lifespan` manager that executes the reminder service once every 15 minutes.
3. **Idempotent Database Claiming:** The database query selects eligible appointments and updates `reminder_sent_at` atomically (or uses row-level locking `SELECT ... FOR UPDATE SKIP LOCKED` / atomic update) so that even if invoked simultaneously, no appointment receives duplicate reminders.

## Consequences
### Positive
- Works seamlessly out-of-the-box for local development and single-container deployments without external tooling.
- Production multi-worker deployments can disable the internal loop (`ENABLE_IN_PROCESS_REMINDER_WORKER=false`) and trigger the endpoint safely via external cron.
- Atomic database updates guarantee idempotency regardless of trigger source.

### Negative / Trade-offs
- Requires documenting configuration toggles for production deployments (`ENABLE_IN_PROCESS_REMINDER_WORKER`).
