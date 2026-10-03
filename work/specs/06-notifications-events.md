# Notifications & Real-Time Events Module Spec

_Status: approved · Date: 2026-10-03 · Covers: R-15, R-16, R-17, NFR-5_

## 1. Responsibility
This module owns real-time event distribution to clinic front-desk and operatory screens via Server-Sent Events (SSE), patient confirmation dispatch (booking and rescheduling), and automated 24-hour pre-visit reminder dispatching per ADR 0002.
It does NOT own appointment scheduling or state persistence (which are handled in module 05).

---

## 2. Layer 1 — Contracts (Standard §3)

### Shared Schemas
```python
class AppointmentLiveEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_type: str = Field(alias="eventType")
    appointment_id: UUID = Field(alias="appointmentId")
    dentist_id: UUID = Field(alias="dentistId")
    patient_name: str = Field(alias="patientName")
    status: str
    start_time: datetime = Field(alias="startTime")
    timestamp: datetime = Field(default_factory=utcnow)


class ReminderDispatchResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    dispatched_count: int = Field(alias="dispatchedCount")
    checked_window_start: datetime = Field(alias="checkedWindowStart")
    checked_window_end: datetime = Field(alias="checkedWindowEnd")
```

---

## 3. Layer 2 — Persistence (Standard §4)
- **Reminder Queries (`app/db/repository.py`):**
```python
async def list_pending_reminders(
    session: AsyncSession,
    window_start: datetime,
    window_end: datetime,
) -> list[Appointment]:
    """Fetch appointments in SCHEDULED/CONFIRMED state starting in window with reminder_sent_at IS NULL."""
    stmt = (
        select(Appointment)
        .where(
            Appointment.status.in_(["SCHEDULED", "CONFIRMED"]),
            Appointment.reminder_sent_at.is_(None),
            Appointment.start_time >= window_start,
            Appointment.start_time <= window_end,
        )
        .options(joinedload(Appointment.patient), joinedload(Appointment.dentist))
    )
    result = await session.scalars(stmt)
    return list(result.all())

async def mark_reminder_sent(session: AsyncSession, appointment_id: UUID, sent_at: datetime) -> None:
    stmt = (
        update(Appointment)
        .where(Appointment.id == appointment_id, Appointment.reminder_sent_at.is_(None))
        .values(reminder_sent_at=sent_at)
    )
    await session.execute(stmt)
```

---

## 4. Layer 3 — Wiring (Standard §5)

### Broadcaster & Notification Adapters
- `EventBroadcaster`: Singleton pub-sub managing active client queues. Thread-safe subscription registry with `threading.Lock` (Standard §7).
- `NotificationService`: Protocol defining notification methods.
- `LoggingNotificationService`: Default implementation logging dispatched messages to stdout / log file.
- `get_event_broadcaster() -> EventBroadcaster`
- `EventBroadcasterDep = Annotated[EventBroadcaster, Depends(get_event_broadcaster)]`
- `get_notification_service() -> NotificationService`
- `NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]`

### Endpoints
| Method | Path | Request | Response | Success | Errors | Guard | Covers |
|---|---|---|---|---|---|---|---|
| `GET` | `/api/v1/appointments/live` | None | `EventSourceResponse` (text/event-stream) | 200 | 401 | `CurrentUserDep` | R-15 |
| `POST` | `/api/v1/appointments/reminders/dispatch` | None | `ReminderDispatchResult` | 200 | 401, 403 | `require_roles("ADMIN")` | R-17 |

---

## 5. Layer 4 — Concurrency and Real-Time (Standard §6)

### SSE Endpoint Implementation
Following the standard's §6 streaming guidelines (`response_class=EventSourceResponse`):
```python
@router.get("/live", response_class=EventSourceResponse)
async def stream_live_appointments(
    current_user: CurrentUserDep,
    broadcaster: EventBroadcasterDep,
) -> AsyncIterable[ServerSentEvent]:
    queue = await broadcaster.subscribe()
    try:
        while True:
            try:
                # Wait for next event with a 15-second timeout for keep-alive
                event_data = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield ServerSentEvent(
                    data=event_data.model_dump(by_alias=True, mode="json"),
                    event=event_data.event_type,
                    id=str(event_data.appointment_id),
                )
            except asyncio.TimeoutError:
                # Periodic keep-alive ping comment to prevent client/proxy timeouts
                yield ServerSentEvent(comment="ping")
    finally:
        await broadcaster.unsubscribe(queue)
```

### Confirmation Dispatch (Standard §6)
In `AppointmentService`:
When booking or rescheduling commits, confirmation dispatch runs asynchronously without blocking the client response:
```python
# Dispatched via background task or TaskGroup
await notification_service.send_booking_confirmation(appointment)
```

---

## 6. Layer 5 — State and Hardening (Standard §7, ADR 0002)
- **Thread Safety:** The active subscriber list in `EventBroadcaster` is protected with `threading.Lock` across concurrent connections.
- **Dual-Mode 24h Reminder Dispatcher (ADR 0002, NFR-5):**
  1. **HTTP Maintenance Endpoint:** `POST /api/v1/appointments/reminders/dispatch` callable by external cron runners in multi-worker environments.
  2. **In-Process Lifespan Loop:** Controlled by `settings.ENABLE_IN_PROCESS_REMINDER_WORKER: bool = True`. When enabled, launches a background loop in `main.py` lifespan executing reminder queries every 15 minutes.
  3. **Idempotency:** `WHERE reminder_sent_at IS NULL` ensures that multiple concurrent triggers will never double-send reminders.

---

## 7. Errors
| Exception | Raised when | HTTP Status | Error Code |
|---|---|---|---|
| `NotificationDispatchError` | External provider fails after retries | Logged & tolerated | `NOTIFICATION_FAILED` |

---

## 8. State Machine
N/A.

---

## 9. Test Seams
| Behaviour | Seam | Notes |
|---|---|---|
| SSE stream yields keep-alive pings | Async generator test with timeout | Verifies 15s comment ping |
| Broadcaster fan-out | Broadcaster unit test | Emits event, asserts received by multiple subscriber queues |
| Reminder query window (23–25h) | Repository test against real DB | Test records at 22h, 24h, 26h; exactly the 24h record is returned |
| Reminder idempotency | Integration test | Dispatched twice; second run returns `dispatchedCount=0` |
| Fake notification service captures messages | API test with `dependency_overrides` | Verifies expected payload delivered |

---

## 10. Traceability
| Requirement | Spec Section | Endpoint(s) |
|---|---|---|
| **R-15** Live Server-Sent Events (SSE) Stream | §2 Schemas, §4 Endpoints, §5 Concurrency | `GET /api/v1/appointments/live` |
| **R-16** Automated Booking/Reschedule Confirmation | §4 Wiring, §5 Concurrency | Triggered in `AppointmentService` on booking/reschedule |
| **R-17** Scheduled 24-Hour Pre-Appointment Reminder | §2 Schemas, §3 Persistence, §4 Endpoints, §6 Hardening | `POST /api/v1/appointments/reminders/dispatch` + lifespan loop |
| **NFR-5** Stateless Multi-Worker Operation | §6 State and Hardening, ADR 0002 | Idempotent DB query + external cron trigger support |

---

## 11. Open Questions / ADRs
- [ADR 0002: Dual-Mode 24-Hour Pre-Appointment Reminder Execution](file:///c:/Users/seyi/Documents/Development/Raven/docs/adr/0002-reminder-execution-strategy.md)
