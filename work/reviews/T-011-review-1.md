# Review T-011 round 1 — changes-requested
Gates: ruff ✓ · mypy ✓ · pytest ✓ (121 passed)
## Spec — findings (quote the spec line)

### Blocker: Missing tests for all acceptance criteria
**Spec lines (ticket test plan):**
- Test 1: "`test_sse_stream_emits_appointment_event_on_transition` | Streaming seam (httpx) | event received, event_type == 'appointment.checked_in', payload matches | PRD R-15"
- Test 2: "`test_sse_stream_emits_keep_alive_ping_comment` | Streaming seam (httpx) | timeout 15s triggers comment ping `: ping` | PRD R-15"
- Test 3: "`test_broadcaster_multiple_subscribers_fan_out` | Service unit | event delivered to queue 1 and queue 2 | Spec 06 §9"
- Test 4: "`test_sse_client_disconnect_cleans_up_subscription` | Service unit | broadcaster subscribers count decreases on exit | Spec 06 §5"
- Test 5: "`test_broadcaster_thread_safety_under_concurrent_subscribe` | Concurrency seam | threading.Lock protects active subscriber set | Standard §7, NFR-5"

**Problem:** None of these 5 tests exist in the codebase. The ticket's "Commands run" section claims "pytest -q ✅ (121 tests passed)" but those are pre-existing tests — zero tests exercise the new SSE/broadcaster functionality.

**Fix:** Implement all 5 tests per the test plan before approval.

---

### Major: NotificationService wired but not used for R-16
**Spec line (06-notifications-events.md §5):** "When booking or rescheduling commits, confirmation dispatch runs asynchronously without blocking the client response: `await notification_service.send_booking_confirmation(appointment)`"

**Problem:** `NotificationService` protocol, `LoggingNotificationService`, DI wiring, and `NotificationServiceDep` are all implemented, but `AppointmentService` never calls `send_booking_confirmation` or `send_reschedule_confirmation`. The `notification_service` dependency is not injected into `AppointmentService`.

**Fix:** Inject `NotificationService` into `AppointmentService` and call the confirmation methods after successful booking/rescheduling (fire-and-forget per spec).

---

### Minor: Event type strings not validated/enum
**Spec line (06-notifications-events.md §2):** `event_type: str = Field(alias="eventType")` — defined as raw string.

**Problem:** `AppointmentService._publish_event` passes raw strings like `"appointment.booked"`, `"appointment.rescheduled"`, etc. No central enum or constant defines these; a typo would silently produce an unknown event type.

**Fix:** Define an `EventType` enum or module-level constants in `schemas.py` and use them consistently.

---

## Standards — findings (cite standard § or smell)

### Blocker: Module-level mutable global singletons (Layer 5 smell)
**Files:** `event_broadcaster.py:74-85`, `notification_service.py:109-126`

**Standard smell (§9 checklist):** "module-level mutable state (Layer 5)"

Both services use module-level globals (`_event_broadcaster`, `_notification_service`) with double-checked locking for singleton access. This creates hidden shared state, makes testing harder (requires `set_notification_service` override), and violates the standard's preference for explicit dependency injection.

**Fix direction:** Keep singleton pattern if required by spec, but document why it overrides the standard. At minimum, add a `reset_event_broadcaster()` for test isolation (mirroring `set_notification_service`).

---

### Major: `threading.Lock` in async hot path
**File:** `event_broadcaster.py:28, 37, 47, 59, 69`

**Standard §7 (State and Hardening) + §6 (Concurrency):** For async code, `asyncio.Lock` is the correct primitive; `threading.Lock` blocks the event loop if contended. The spec explicitly mandates `threading.Lock` ("per Standard §7, NFR-5"), but Standard §7 actually recommends `asyncio.Lock` for async contexts — the spec may be misreading the standard.

**Fix direction:** Replace `threading.Lock` with `asyncio.Lock` and make `subscribe`/`unsubscribe`/`publish`/`subscriber_count` async (they already are). The lock contention window is tiny (set add/discard/list-copy), so async lock overhead is negligible.

---

### Major: Fire-and-forget `asyncio.create_task` without error handling
**File:** `appointment_service.py:89`

```python
asyncio.create_task(self._broadcaster.publish(event))
```

**Standard §6 (Concurrency):** "Fire-and-forget tasks must attach a done-callback or be tracked in a TaskGroup to surface exceptions." An unhandled exception in `publish` (e.g., queue full, serialization error) will be silently logged by the event loop's exception handler but not correlated to the request.

**Fix:** Wrap in a helper that logs exceptions with correlation ID, or use `asyncio.create_task(...).add_done_callback(log_exceptions)`.

---

### Major: Silent event drop on subscriber queue full
**File:** `event_broadcaster.py:63-64`

```python
with contextlib.suppress(asyncio.QueueFull):
    queue.put_nowait(event)
```

**Standard §7 (Hardening):** Dropping events silently violates "instant appointment updates" (R-15). At minimum, log a warning with correlation ID when a subscriber falls behind.

**Fix:** Log a structured warning when `QueueFull` is caught; consider bounded queue with backpressure strategy.

---

### Minor: SSE endpoint missing structured logging / correlation ID
**File:** `live.py:27-59`

**Standard §4 (Error Handling) + §5 (Wiring):** The streaming endpoint yields events for minutes/hours but emits zero log lines. No correlation ID is logged on connect/disconnect, making debugging impossible in production.

**Fix:** Log `info` on subscribe (`correlation_id`, `user_id`, `subscriber_count`) and unsubscribe; use `request.state.correlation_id`.

---

### Minor: `NotificationService` DI singleton but no `reset` for tests
**File:** `notification_service.py:123-126` has `set_notification_service`, but `event_broadcaster.py` has no equivalent.

**Standard §5 (Wiring):** Consistency — if one global service provides a test override, the other should too.

---

### Nit: `AppointmentLiveEvent.timestamp` default factory creates naive ambiguity
**File:** `schemas.py:500`

```python
timestamp: datetime = Field(default_factory=lambda: datetime.now(ZoneInfo("UTC")))
```

The `datetime.now(ZoneInfo("UTC"))` returns an **aware** datetime (UTC). Good. But the field type is just `datetime` — downstream code must not assume naive. Add `Annotated[datetime, Field(..., description="UTC timestamp")]` or a `UTCDateTime` constrained type per §3.

---

## Tests — findings

### Blocker: Zero tests for new SSE/broadcaster functionality
**Test plan (ticket §## Test plan):** 5 tests specified, 0 implemented.

**Current test count:** 121 (all pre-existing). No test file for `live.py`, `event_broadcaster.py`, or `notification_service.py`.

**Failure paths untested:** 401 on `/live`, concurrent subscriber fan-out, keep-alive timing, disconnect cleanup, lock contention.

---

### Minor: Existing tests don't verify event publishing side effects
**File:** `tests/api/test_appointments.py`

Tests like `test_book_appointment_success_201`, `test_reschedule_appointment_success_200`, `test_cancel_appointment_with_reason_success_200` assert HTTP response but **do not assert** that an SSE event was published. They would pass even if `_publish_event` were removed.

**Fix:** Add integration tests using a test double for `EventBroadcaster` (via `dependency_overrides`) that captures published events and asserts on them.

---

## Summary — counts per severity; the single worst issue

| Severity | Count |
|----------|-------|
| blocker  | 2     |
| major    | 4     |
| minor    | 3     |
| nit      | 1     |

**Single worst issue:** **Missing all 5 acceptance-criterion tests** — the implementation cannot be verified against the spec without them. This alone blocks approval.

---

## Verdict

**changes-requested** — The implementer must:
1. Write all 5 tests from the test plan (blocker).
2. Wire `NotificationService` into `AppointmentService` for R-16 confirmations (major).
3. Replace `threading.Lock` with `asyncio.Lock` in `EventBroadcaster` (major).
4. Add error handling/logging to fire-and-forget publish tasks (major).
5. Add structured logging to SSE endpoint (minor).
6. Add `reset_event_broadcaster()` for test parity (minor).
7. Add event-type constants/enum (minor).
8. Log warnings on queue-full drops (major).