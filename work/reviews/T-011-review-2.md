# Review T-011 round 2 — changes-requested

Gates: ruff — not run · format — not run · mypy — not run · pytest — not run. This review was performed against the merged `master` source at `fd95a9c4eff640a62fd39d3d7164ac477c20292f`. GitHub reports zero check runs and no status contexts for the merge commit; a local clone/test run was not possible in this review environment. Do not treat gates as passing.

## Spec — findings

### BLOCKER B1 — SSE endpoint tests cannot complete with the configured ASGITransport

**Spec:** T-011 Test plan #2 requires a streaming test that verifies the `: ping` comment after 15 seconds. Acceptance criterion #4 requires disconnect cleanup.

**Files:** `backend/tests/conftest.py:132-140`; `backend/tests/api/test_live_sse.py:202-236, 250-355`; `backend/src/app/routers/live.py:42-68`.

The shared `client` fixture uses HTTPX `ASGITransport`. HTTPX's ASGI transport buffers response body parts until the ASGI application completes; this is incompatible with the intentionally infinite SSE generator, which only finishes after disconnect. Consequently, the heartbeat test's `client.stream()` and the concurrent-connection/disconnect tests cannot reliably enter/read the stream and can hang rather than exercise the assertions. See the HTTPX discussion [ASGITransport does not stream response body](https://github.com/encode/httpx/discussions/3391).

**Fix direction:** use a real local ASGI server with a streaming-capable HTTP client for SSE integration tests, or split the endpoint generator into a unit-testable seam and retain a smaller real-server test for wire framing, heartbeat and disconnect behaviour. Ensure test timeouts fail fast instead of hanging the whole suite.

### BLOCKER B2 — The SSE connection holds a request-scoped database session open

**Spec:** T-011 implementation notes explicitly say: “Close or isolate the DB session before streaming to avoid holding open connections.”

**Files:** `backend/src/app/routers/live.py:30-33`; `backend/src/app/api/auth.py:43-60, 75`; `backend/src/app/api/deps.py:39-49, 51`.

The live route depends on `CurrentUserDep`; `get_current_user` depends on `DbSessionDep`, which yields a session and only commits/closes it during dependency cleanup. The project allows FastAPI `>=0.118.0`; in 0.118.0, yield-dependency cleanup runs after the streaming response is sent by default ([FastAPI release notes](https://fastapi.tiangolo.com/release-notes/#01180-2025-09-29), [dependency scope docs](https://fastapi.tiangolo.com/advanced/advanced-dependencies/)). Since this stream is long-lived, each connected staff client can retain its DB connection/transaction until it disconnects, risking pool exhaustion.

**Fix direction:** ensure authentication's database session is closed before the stream begins. Use function-scoped dependency cleanup only if the minimum FastAPI version supports it; otherwise use an authentication dependency with a short-lived, internally managed session that closes before returning the principal. Add a regression test proving the DB session closes while the stream remains open.

### MAJOR M1 — Events can be published before the appointment transaction commits

**Spec:** T-011 Acceptance criterion #1 says updates are delivered when appointments are booked, rescheduled, cancelled or transition status. Spec 06 §5 says booking/reschedule confirmation dispatch occurs “When booking or rescheduling commits.”

**Files:** `backend/src/app/services/appointment_service.py:75-100, 184-203, 323-354, 415-431, 589-619`; `backend/src/app/api/deps.py:39-49`.

`_publish_event` schedules `self._broadcaster.publish(event)` with `asyncio.create_task` inside the service method. The request-scoped `get_db_session` commits after the endpoint returns, so the scheduled task can run before the transaction commit. Clients can receive an event for data that is not yet visible to other transactions, or that is subsequently rolled back if commit fails.

**Fix direction:** publish only after a successful commit (for example, by making the transaction boundary explicit and dispatching after it succeeds, or by using a transactional outbox). Add a test where the commit fails and prove no event is published.

### MAJOR M2 — Acceptance criterion tests do not verify the full SSE payload for all event-producing operations

**Spec:** Acceptance criterion #1 requires an SSE event “with `event_type` and full payload” for booking, rescheduling, cancellation and status transitions. Test plan #1 requires an event through the streaming seam with a matching type and payload.

**Files:** `backend/tests/api/test_live_sse.py:126-194, 250-322`; `backend/tests/services/test_event_broadcaster.py:26-58`; `backend/src/app/services/appointment_service.py:194-203, 345-354, 424-431, 605-619`.

The first API test manually subscribes to the broadcaster queue instead of reading the SSE endpoint. The real stream test only checks for the `event: appointment.checked_in` line; it does not parse/assert the `data:` payload or event ID. The tests also do not verify event publication for booking, rescheduling and cancellation. These tests could pass even if SSE JSON serialization omitted or corrupted required payload fields, or one of those service hooks were removed.

**Fix direction:** through a real streaming-capable client, parse an SSE frame and assert event name, ID and all required JSON payload fields. Add assertions for booked, rescheduled and cancelled events as well as status transitions.

### MAJOR M3 — In-process singleton does not deliver events across worker processes

**Spec:** T-011 declares coverage of NFR-5; Spec 06 §10 maps NFR-5 (“Stateless Multi-Worker Operation”) to the live stream. Architecture spec §4 also discusses a local channel with a broker fallback if scaling out.

**Files:** `backend/src/app/services/event_broadcaster.py:19-30, 90-103`; `backend/src/app/api/deps.py:125-132`.

`get_event_broadcaster()` returns a module-level in-memory singleton. Each Uvicorn worker process has its own instance and subscriber set. If a live client is connected to worker A but the appointment mutation is handled by worker B, worker B publishes only to its own queues and the client on worker A never receives the update. The current implementation therefore cannot claim cross-worker delivery.

**Fix direction:** decide and document whether T-011 is single-worker only, or support multi-worker deployment with a process-shared broker (e.g. Redis Pub/Sub) and an integration test using distinct publisher/subscriber worker processes. Update the NFR/traceability claim to match the chosen guarantee.

### MAJOR M4 — Subscriber queues are unbounded, making the queue-full handling ineffective

**Spec:** Acceptance criterion #3 requires concurrent connections to receive events without data races; NFR-5/Standard §7 calls for hardening shared state.

**File:** `backend/src/app/services/event_broadcaster.py:37-39, 59-81`.

Each subscriber is created with `asyncio.Queue()`, whose default `maxsize=0` means unbounded. Therefore the `asyncio.QueueFull` warning path cannot protect ordinary subscribers. If a client reads very slowly while events continue to publish, queued events can accumulate indefinitely and consume process memory.

**Fix direction:** choose a bounded queue size and explicitly define the slow-consumer policy (drop with a detectable resync signal, disconnect the slow consumer, or apply backpressure). Test queue saturation and verify the chosen behaviour.

## Standards — findings

### MINOR m1 — Background-task failure logging does not include the exception

**File:** `backend/src/app/services/appointment_service.py:103-116`.

The done callback calls `task.exception()` but then uses `logger.exception(...)` outside an active exception handler. This typically logs `NoneType: None` rather than the task's actual traceback/details, undermining the claimed error handling.

**Fix direction:** store the returned exception and log it with `logger.error(..., exc_info=(type(error), error, error.__traceback__))` or include the exception details explicitly.

## Tests — findings

- The SSE heartbeat, real-connection fan-out and disconnect tests are not valid with the repository's current in-process ASGI transport (B1).
- The fan-out service unit tests verify same-event-loop coroutine concurrency, not cross-thread or cross-process delivery. The test called `test_concurrent_publish_while_subscribing` also allows 10% loss (`>= 27` of 30) despite the acceptance criterion expecting all active subscribers to receive an event.
- No quality gates were executed during this review; the merge commit has no GitHub Actions check runs or status contexts available to verify.

## Summary

| Severity | Count | Key |
|---|---:|---|
| Blocker | 2 | SSE tests cannot consume infinite streams with ASGITransport; DB session is retained for stream lifetime |
| Major | 4 | Events published pre-commit; incomplete SSE payload/event-operation assertions; no cross-worker fan-out; unbounded subscriber queues |
| Minor | 1 | Background task exception details are not logged correctly |
| Nit | 0 | — |

**Single worst issue:** B2 — each live SSE connection can retain a database session/connection for its lifetime, risking database pool exhaustion under sustained client connections.

**Verdict: changes-requested.** This is review round 2. Per the repository workflow, stop before another implementation/review loop and ask the owner to resolve the remaining design question: should T-011 guarantee multi-worker delivery (requiring a shared broker), or is the supported deployment explicitly single-worker? The session-lifetime and SSE test-transport blockers should be fixed either way.
