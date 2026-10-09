"""SSE generator and API tests for T-011.

Infinite SSE generators are tested directly: HTTPX ASGITransport buffers an
ASGI response until completion and therefore cannot test an infinite stream.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.sse import ServerSentEvent
from httpx import AsyncClient
from starlette.requests import Request

from app.api.auth import CurrentUser
from app.models import DentalService, Patient, Staff, WorkingShift
from app.routers import live as live_router
from app.services.event_broadcaster import (
    EventBroadcaster,
    get_event_broadcaster,
    reset_event_broadcaster,
)


@pytest.fixture(autouse=True)
def reset_broadcaster() -> None:
    """Ensure fresh broadcaster state for each test."""
    reset_event_broadcaster()
    yield
    reset_event_broadcaster()


def _request() -> Request:
    """Build a minimal Starlette request for the public streaming seam."""
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/v1/appointments/live",
            "raw_path": b"/api/v1/appointments/live",
            "query_string": b"",
            "headers": [],
            "client": ("testclient", 123),
            "server": ("testserver", 80),
            "state": {"correlation_id": "test-sse"},
        }
    )


def _current_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="receptionist@example.com",
        full_name="SSE Receptionist",
        role="RECEPTIONIST",
        is_active=True,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
async def sse_test_dentist(test_session_local, override_dbsession) -> Staff:
    """Create a test dentist with a Monday shift."""
    from datetime import time

    async with test_session_local() as session:
        dentist = Staff(
            email=f"dentist-sse-{uuid4().hex[:8]}@clinic.com",
            hashed_password="irrelevant",
            full_name="Dr. SSE Dentist",
            role="DENTIST",
            is_active=True,
        )
        session.add(dentist)
        await session.flush()
        session.add(
            WorkingShift(
                dentist_id=dentist.id,
                day_of_week=0,
                start_time=time(9, 0),
                end_time=time(12, 0),
            )
        )
        await session.commit()
        await session.refresh(dentist)
        return dentist


@pytest.fixture
async def sse_test_patient(test_session_local, override_dbsession) -> Patient:
    """Create a test patient."""
    from datetime import date

    async with test_session_local() as session:
        patient = Patient(
            first_name="Jane",
            last_name="Doe",
            date_of_birth=date(1990, 1, 1),
            phone="+15551234567",
            email=f"jane-{uuid4().hex[:8]}@example.com",
            is_active=True,
        )
        session.add(patient)
        await session.commit()
        await session.refresh(patient)
        return patient


@pytest.fixture
async def sse_test_service(test_session_local, override_dbsession) -> DentalService:
    """Create a test dental service (45 minutes)."""
    async with test_session_local() as session:
        service = DentalService(
            name=f"Routine Cleaning SSE {uuid4().hex[:8]}",
            description="Standard cleaning",
            duration_minutes=45,
            is_active=True,
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)
        return service


@pytest.fixture
async def sse_receptionist_headers(
    test_session_local,
    override_dbsession,
    auth_headers: callable,
) -> dict[str, str]:
    """Create a receptionist and return auth headers."""
    async with test_session_local() as session:
        staff = Staff(
            email=f"recep-sse-{uuid4().hex[:8]}@clinic.com",
            hashed_password="irrelevant",
            full_name="SSE Receptionist",
            role="RECEPTIONIST",
            is_active=True,
        )
        session.add(staff)
        await session.commit()
        await session.refresh(staff)
        return auth_headers(staff.id, staff.role)


async def _create_appointment(
    client: AsyncClient,
    headers: dict[str, str],
    dentist: Staff,
    patient: Patient,
    service: DentalService,
) -> UUID:
    """Create an appointment through the API and return its ID."""
    start_time = datetime(2026, 1, 5, 9, 0, tzinfo=ZoneInfo("America/New_York"))
    response = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patientId": str(patient.id),
            "dentistId": str(dentist.id),
            "serviceId": str(service.id),
            "startTime": start_time.isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


async def test_sse_stream_emits_appointment_event_on_transition(
    sse_receptionist_headers: dict[str, str],
    sse_test_dentist: Staff,
    sse_test_patient: Patient,
    sse_test_service: DentalService,
    client: AsyncClient,
) -> None:
    """An authenticated stream yields the expected event and payload."""
    appointment_id = await _create_appointment(
        client,
        sse_receptionist_headers,
        sse_test_dentist,
        sse_test_patient,
        sse_test_service,
    )
    broadcaster = get_event_broadcaster()
    stream = live_router.stream_live_appointments(
        _request(), _current_user(), broadcaster
    )

    try:
        pending = asyncio.create_task(anext(stream))
        await asyncio.sleep(0)
        response = await client.post(
            f"/api/v1/appointments/{appointment_id}/status",
            headers=sse_receptionist_headers,
            json={"toStatus": "CONFIRMED", "note": "Patient confirmed"},
        )
        assert response.status_code == 200, response.text
        event = await asyncio.wait_for(pending, timeout=2.0)
        assert isinstance(event, ServerSentEvent)
        assert event.event == "appointment.confirmed"
        assert event.id == str(appointment_id)
        assert event.data["appointmentId"] == str(appointment_id)
        assert event.data["dentistId"] == str(sse_test_dentist.id)
        assert event.data["patientName"] == "Jane Doe"
        assert event.data["status"] == "CONFIRMED"
    finally:
        await stream.aclose()


async def test_sse_stream_emits_keep_alive_ping_comment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An idle stream yields a ping comment at the configured heartbeat interval."""
    monkeypatch.setattr(live_router, "HEARTBEAT_SECONDS", 0.001)
    stream = live_router.stream_live_appointments(
        _request(), _current_user(), get_event_broadcaster()
    )
    try:
        event = await asyncio.wait_for(anext(stream), timeout=0.5)
        assert isinstance(event, ServerSentEvent)
        assert event.comment == "ping"
    finally:
        await stream.aclose()


async def test_sse_endpoint_requires_authentication(client: AsyncClient) -> None:
    """Unauthenticated SSE connection is rejected with 401."""
    response = await client.get("/api/v1/appointments/live")
    assert response.status_code == 401


async def test_sse_multiple_concurrent_connections(
    sse_receptionist_headers: dict[str, str],
    sse_test_dentist: Staff,
    sse_test_patient: Patient,
    sse_test_service: DentalService,
    client: AsyncClient,
) -> None:
    """Every active local stream receives a published appointment event."""
    appointment_id = await _create_appointment(
        client,
        sse_receptionist_headers,
        sse_test_dentist,
        sse_test_patient,
        sse_test_service,
    )
    broadcaster = get_event_broadcaster()
    streams = [
        live_router.stream_live_appointments(_request(), _current_user(), broadcaster)
        for _ in range(3)
    ]
    pending = [asyncio.create_task(anext(stream)) for stream in streams]

    try:
        # Each generator subscribes before waiting for the next queue event.
        await asyncio.sleep(0)
        response = await client.post(
            f"/api/v1/appointments/{appointment_id}/status",
            headers=sse_receptionist_headers,
            json={"toStatus": "CONFIRMED", "note": "Fan-out test"},
        )
        assert response.status_code == 200, response.text
        events = await asyncio.wait_for(
            asyncio.gather(*pending),
            timeout=2.0,
        )
        assert len(events) == 3
        assert all(event.event == "appointment.confirmed" for event in events)
        assert all(event.id == str(appointment_id) for event in events)
    finally:
        for task in pending:
            if not task.done():
                task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for stream in streams:
            await stream.aclose()


async def test_sse_disconnect_cleans_up_subscription() -> None:
    """Cancelling a blocked stream unregisters its local queue."""
    broadcaster = get_event_broadcaster()
    initial_count = await broadcaster.subscriber_count
    stream = live_router.stream_live_appointments(
        _request(), _current_user(), broadcaster
    )
    pending = asyncio.create_task(anext(stream))

    try:
        async with asyncio.timeout(1.0):
            while await broadcaster.subscriber_count != initial_count + 1:
                await asyncio.sleep(0)
    finally:
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        await stream.aclose()

    assert await broadcaster.subscriber_count == initial_count


async def test_sse_stream_emits_booking_reschedule_and_cancellation_events(
    sse_receptionist_headers: dict[str, str],
    sse_test_dentist: Staff,
    sse_test_patient: Patient,
    sse_test_service: DentalService,
    client: AsyncClient,
) -> None:
    """Booking, rescheduling and cancellation publish complete live payloads."""
    broadcaster = get_event_broadcaster()
    stream = live_router.stream_live_appointments(
        _request(), _current_user(), broadcaster
    )
    pending: asyncio.Task[ServerSentEvent] | None = None

    try:
        pending = asyncio.create_task(anext(stream))
        await asyncio.sleep(0)
        appointment_id = await _create_appointment(
            client,
            sse_receptionist_headers,
            sse_test_dentist,
            sse_test_patient,
            sse_test_service,
        )
        booked = await asyncio.wait_for(pending, timeout=2.0)
        assert booked.event == "appointment.booked"
        assert booked.id == str(appointment_id)
        assert booked.data["status"] == "SCHEDULED"
        assert booked.data["patientName"] == "Jane Doe"

        pending = asyncio.create_task(anext(stream))
        await asyncio.sleep(0)
        rescheduled_response = await client.post(
            f"/api/v1/appointments/{appointment_id}/reschedule",
            headers=sse_receptionist_headers,
            json={"startTime": "2026-01-05T10:00:00-05:00"},
        )
        assert rescheduled_response.status_code == 200, rescheduled_response.text
        rescheduled = await asyncio.wait_for(pending, timeout=2.0)
        assert rescheduled.event == "appointment.rescheduled"
        assert rescheduled.id == str(appointment_id)
        assert rescheduled.data["startTime"].startswith("2026-01-05T15:00:00")

        pending = asyncio.create_task(anext(stream))
        await asyncio.sleep(0)
        cancelled_response = await client.post(
            f"/api/v1/appointments/{appointment_id}/cancel",
            headers=sse_receptionist_headers,
            json={"cancellationReason": "Patient requested cancellation"},
        )
        assert cancelled_response.status_code == 200, cancelled_response.text
        cancelled = await asyncio.wait_for(pending, timeout=2.0)
        assert cancelled.event == "appointment.cancelled"
        assert cancelled.id == str(appointment_id)
        assert cancelled.data["status"] == "CANCELLED"
    finally:
        if pending is not None and not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        await stream.aclose()



async def test_sse_slow_consumer_gets_resync_signal() -> None:
    """A full queue terminates a slow stream with an explicit refetch signal."""
    broadcaster = EventBroadcaster(queue_maxsize=1)
    stream = live_router.stream_live_appointments(
        _request(), _current_user(), broadcaster
    )
    pending = asyncio.create_task(anext(stream))

    try:
        async with asyncio.timeout(1.0):
            while await broadcaster.subscriber_count != 1:
                await asyncio.sleep(0)

        from app.schemas import AppointmentLiveEvent

        event = AppointmentLiveEvent(
            eventType="appointment.booked",
            appointmentId=uuid4(),
            dentistId=uuid4(),
            patientName="Jane Doe",
            status="SCHEDULED",
            startTime=datetime.now(UTC),
        )
        await broadcaster.publish(event)
        delivered = await asyncio.wait_for(pending, timeout=1.0)
        assert delivered.event == "appointment.booked"

        # The generator is paused at yield; these fill and overflow its queue.
        await broadcaster.publish(event)
        await broadcaster.publish(event)
        resync = await asyncio.wait_for(anext(stream), timeout=1.0)
        assert resync.event == "appointment.resync_required"
        assert resync.data == {"reason": "slow_consumer", "action": "refetch"}
    finally:
        if not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        await stream.aclose()
