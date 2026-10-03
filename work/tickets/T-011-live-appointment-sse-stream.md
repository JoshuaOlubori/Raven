---
id: T-011
title: Real-time live appointment SSE stream
status: todo
mode: AFK
blocked_by: T-010
spec_refs: specs/06-notifications-events.md#2-layer-1, specs/06-notifications-events.md#4-layer-3, specs/06-notifications-events.md#5-layer-4
covers: R-15, NFR-5
updated: 2026-10-03
---

## Outcome
Front-desk and operatory screens can subscribe to a live Server-Sent Events (SSE) stream (`GET /api/v1/appointments/live`) to receive instant appointment updates (booked, rescheduled, cancelled, checked in, started, completed) with periodic 15-second keep-alive heartbeats.

## What to build
- `src/app/services/event_broadcaster.py`: `EventBroadcaster` singleton pub-sub managing active subscriber queues (`asyncio.Queue`), protected by `threading.Lock` for subscriber registration and deregistration (Standard §7).
- `src/app/routers/live.py`:
  - `GET /api/v1/appointments/live` using `response_class=EventSourceResponse`, yielding `ServerSentEvent` instances and keep-alive ping comments (`: ping`).
- `src/app/services/appointment_service.py`: Wire event publication into booking, rescheduling, status transition, and cancellation flows.

## Acceptance criteria
- [ ] Given an active SSE connection, When an appointment is booked, rescheduled, cancelled, or transitions status, Then an SSE event is delivered immediately to the client with `event_type` and full payload (R-15).
- [ ] Given an idle SSE connection, When 15 seconds elapse without an appointment event, Then a keep-alive comment (`: ping`) is emitted to prevent connection dropouts (R-15).
- [ ] Given multiple concurrent subscriber connections, When an event occurs, Then all active connections receive the event without deadlock or data race (Standard §7).
- [ ] When a client disconnects, Then the subscriber queue is cleanly unsubscribed and garbage collected.

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | `test_sse_stream_emits_appointment_event_on_transition` | Streaming seam (httpx) | event received, event_type == "appointment.checked_in", payload matches | PRD R-15 |
| 2 | `test_sse_stream_emits_keep_alive_ping_comment` | Streaming seam (httpx) | timeout 15s triggers comment ping `: ping` | PRD R-15 |
| 3 | `test_broadcaster_multiple_subscribers_fan_out` | Service unit | event delivered to queue 1 and queue 2 | Spec 06 §9 |
| 4 | `test_sse_client_disconnect_cleans_up_subscription` | Service unit | broadcaster subscribers count decreases on exit | Spec 06 §5 |
| 5 | `test_broadcaster_thread_safety_under_concurrent_subscribe` | Concurrency seam | threading.Lock protects active subscriber set | Standard §7, NFR-5 |

## Out of scope
External push notifications or SMS/Email reminders (handled in T-012).

## Notes for the implementer
Follow the standard's §6 streaming reference: use `EventSourceResponse` and `ServerSentEvent(data=..., event=..., id=...)`. Close or isolate the DB session before streaming to avoid holding open connections.

## Implementation log

## Review history
