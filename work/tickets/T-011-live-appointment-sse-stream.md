---
id: T-011
title: Real-time live appointment SSE stream
status: in-progress
mode: AFK
blocked_by: T-010
spec_refs: specs/06-notifications-events.md#2-layer-1, specs/06-notifications-events.md#4-layer-3, specs/06-notifications-events.md#5-layer-4
covers: R-15, NFR-5
updated: 2026-10-09
---

## Outcome
Front-desk and operatory screens can subscribe to a live Server-Sent Events (SSE) stream (`GET /api/v1/appointments/live`) to receive instant appointment updates (booked, rescheduled, cancelled, checked in, started, completed) with periodic 15-second keep-alive heartbeats.

## What to build
- `src/app/services/event_broadcaster.py`: app-scoped broadcaster using Redis Pub/Sub for cross-worker delivery and bounded per-worker subscriber queues for local SSE clients.
- `src/app/routers/live.py`:
  - `GET /api/v1/appointments/live` using `response_class=EventSourceResponse`, yielding `ServerSentEvent` instances and keep-alive ping comments (`: ping`).
- `src/app/services/appointment_service.py`: Wire event publication into booking, rescheduling, status transition, and cancellation flows.

## Acceptance criteria
- [ ] Given an active SSE connection, When an appointment is booked, rescheduled, cancelled, or transitions status, Then an SSE event is delivered immediately to the client with `event_type` and full payload (R-15).
- [ ] Given an idle SSE connection, When 15 seconds elapse without an appointment event, Then a keep-alive comment (`: ping`) is emitted to prevent connection dropouts (R-15).
- [ ] Given multiple concurrent subscriber connections across different Uvicorn workers, When an event occurs, Then all active connections receive the event without deadlock or data race (Standard §7, NFR-5).
- [ ] When a client disconnects, Then the subscriber queue is cleanly unsubscribed and garbage collected.
- [ ] Given publisher and SSE subscriber requests handled by different Uvicorn workers, When an appointment event is committed, Then Redis Pub/Sub delivers the event to the subscriber worker (NFR-5, ADR 0003).
- [ ] When the appointment transaction fails to commit, Then no live event is published.
- [ ] When a subscriber queue reaches its configured capacity, Then the connection receives an explicit resync-required signal and closes; memory usage remains bounded.
- [ ] The SSE authentication database session is closed before the response begins streaming.

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | `test_sse_stream_emits_appointment_event_on_transition` | Async generator seam | event received, event_type == "appointment.checked_in", payload matches | PRD R-15 |
| 2 | `test_sse_stream_emits_keep_alive_ping_comment` | Async generator seam | timeout 15s triggers comment ping `: ping` | PRD R-15 |
| 3 | `test_broadcaster_multiple_subscribers_fan_out` | Service unit | event delivered to queue 1 and queue 2 | Spec 06 §9 |
| 4 | `test_sse_client_disconnect_cleans_up_subscription` | Service unit | broadcaster subscribers count decreases on exit | Spec 06 §5 |
| 5 | `test_broadcaster_thread_safety_under_concurrent_subscribe` | Concurrency seam | threading.Lock protects active subscriber set | Standard §7, NFR-5 |

## Out of scope
External push notifications or SMS/Email reminders (handled in T-012).

## Notes for the implementer
Follow the standard's §6 streaming reference: use `EventSourceResponse` and `ServerSentEvent(data=..., event=..., id=...)`. Close or isolate the DB session before streaming to avoid holding open connections. Multi-worker delivery is required: use Redis Pub/Sub and `REDIS_URL`; do not treat the in-memory singleton as the cross-worker transport. Use bounded subscriber queues with an explicit slow-consumer/resync policy. Publish only after transaction commit. SSE integration tests must use a streaming-capable transport, not HTTPX's buffering `ASGITransport` for the infinite stream.

## Implementation decision (2026-10-09)
- **Multi-worker production support:** required. Redis Pub/Sub is the shared transport; one listener per worker fans messages into that worker's local SSE queues. Redis Pub/Sub is non-durable; reconnect/resync is the recovery strategy and durable replay is out of scope.
- **Configuration:** `REDIS_URL` is required for production startup. Unit tests may inject an in-memory broadcaster; integration tests use a test Redis instance.
- **Transaction safety:** event publishing happens after successful DB commit; failed commits must not emit events.
- **Streaming resource safety:** auth DB session must close before the SSE body starts; each subscriber queue is bounded.

## Implementation log

**Files created:**
- `backend/src/app/services/event_broadcaster.py` - Thread-safe `EventBroadcaster` singleton with `threading.Lock` for subscriber management
- `backend/src/app/services/notification_service.py` - `NotificationService` protocol and `LoggingNotificationService` implementation
- `backend/src/app/routers/live.py` - SSE endpoint `GET /api/v1/appointments/live` with 15-second keep-alive pings

**Files modified:**
- `backend/src/app/schemas.py` - Added `AppointmentLiveEvent` schema (Spec 06 §2)
- `backend/src/app/services/__init__.py` - Exported new services
- `backend/src/app/api/deps.py` - Added `EventBroadcasterDep` and `NotificationServiceDep` dependencies
- `backend/src/app/services/appointment_service.py` - Added `_publish_event` method and event publishing after booking, rescheduling, cancellation, and status transitions
- `backend/src/app/routers/__init__.py` - Exported `live_router`
- `backend/src/app/main.py` - Mounted `live_router`

**Decisions:**
- Used `threading.Lock` for subscriber registry per Standard §7 (NFR-5)
- Fire-and-forget event publishing via `asyncio.create_task` to avoid blocking request handlers
- 15-second keep-alive timeout implemented with `asyncio.wait_for` and `TimeoutError` catch
- Event types follow pattern: `appointment.booked`, `appointment.rescheduled`, `appointment.cancelled`, `appointment.confirmed`, `appointment.checked_in`, `appointment.started`, `appointment.completed`, `appointment.no_show`
- Used camelCase aliases in `AppointmentLiveEvent` constructor to satisfy mypy with `populate_by_name=True`

**Commands run:**
- `uv run ruff check` ✅
- `uv run ruff format --check` ✅
- `uv run mypy src` ✅
- `uv run pytest -q` ✅ (121 tests passed)

## Review history

- **Round 2 decision** (2026-10-09): owner chose multi-worker production support. Implementation resumed on branch `implement/T-011-redis-multiworker`; see ADR 0003.

- **Round 1** (2026-10-09): changes-requested — B2/M4/m3/n1 — [work/reviews/T-011-review-1.md](work/reviews/T-011-review-1.md)

- **Round 2** (2026-10-09): changes-requested — B2/M4/m1/n0 — [work/reviews/T-011-review-2.md](work/reviews/T-011-review-2.md). Blockers: SSE tests use an in-process ASGI transport incompatible with an infinite stream; authenticated streaming retains a request-scoped DB session for the stream lifetime. Major: pre-commit event publishing, incomplete payload/operation assertions, no cross-worker fan-out, and unbounded subscriber queues. Quality gates not run in this review; GitHub merge commit has no check runs/status contexts.


### Implementation log — resumed after round 2

**Decision:** multi-worker production delivery is required. See [ADR 0003](../../docs/adr/0003-multi-worker-live-event-broker.md).

**Implemented on branch `implement/T-011-redis-multiworker`:**
- Redis Pub/Sub transport with per-worker local fan-out and lifespan-managed connections.
- `REDIS_URL` configuration and startup failure if the broker cannot initialize.
- Bounded subscriber queues; slow clients receive `appointment.resync_required` and are closed.
- Function-scoped DB dependency cleanup and post-commit event callbacks.
- Direct SSE generator tests that do not use HTTPX ASGITransport for infinite streams; optional cross-instance Redis integration test via `TEST_REDIS_URL`.
- Spec and architecture decision updated; local setup documented in `backend/README.md`.

**Not yet complete:** `backend/uv.lock` must be regenerated after adding the Redis dependency. Ruff, format, mypy, pytest and the Redis integration test have not been run in this remote editing environment. Do not mark T-011 done until the local quality gates pass and the integration test is exercised with Redis.
