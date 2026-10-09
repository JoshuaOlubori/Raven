"""SSE live appointment stream API tests (T-011 Test Plan #1, #2).

Tests the GET /api/v1/appointments/live endpoint via streaming seam.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient

from app.models import DentalService, Patient, Staff, WorkingShift
from app.services.event_broadcaster import (
    get_event_broadcaster,
    reset_event_broadcaster,
)


@pytest.fixture(autouse=True)
def reset_broadcaster() -> None:
    """Ensure fresh broadcaster state for each test."""
    reset_event_broadcaster()
    yield
    reset_event_broadcaster()


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


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

        shift = WorkingShift(
            dentist_id=dentist.id,
            day_of_week=0,  # Monday
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        session.add(shift)
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
            email="jane.doe@example.com",
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


# ---------------------------------------------------------------------------
# Test 1: test_sse_stream_emits_appointment_event_on_transition
# ---------------------------------------------------------------------------


async def test_sse_stream_emits_appointment_event_on_transition(
    sse_receptionist_headers: dict[str, str],
    sse_test_dentist: Staff,
    sse_test_patient: Patient,
    sse_test_service: DentalService,
    client: AsyncClient,
) -> None:
    """R-15: SSE stream emits appointment event when status transitions.

    Given an active SSE connection,
    When an appointment transitions to CHECKED_IN,
    Then an SSE event is delivered with event_type == 'appointment.checked_in'.
    """
    clinic_tz = ZoneInfo("America/New_York")
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    # 1. Create an appointment via API
    create_resp = await client.post(
        "/api/v1/appointments",
        headers=sse_receptionist_headers,
        json={
            "patientId": str(sse_test_patient.id),
            "dentistId": str(sse_test_dentist.id),
            "serviceId": str(sse_test_service.id),
            "startTime": start_time,
        },
    )
    assert create_resp.status_code == 201
    appointment = create_resp.json()
    appointment_id = UUID(appointment["id"])

    # 2. Start SSE stream in background
    broadcaster = get_event_broadcaster()
    queue = await broadcaster.subscribe()

    # 3. Trigger status transition to CHECKED_IN
    # Need to go through CONFIRMED first
    await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=sse_receptionist_headers,
        json={"toStatus": "CONFIRMED", "note": "Patient confirmed"},
    )
    await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=sse_receptionist_headers,
        json={"toStatus": "CHECKED_IN", "note": "Patient checked in"},
    )

    # 4. Wait for CHECKED_IN event on the queue (may receive CONFIRMED first)
    try:
        event_data = None
        async with asyncio.timeout(5.0):
            while True:
                event_data = await queue.get()
                if event_data.event_type == "appointment.checked_in":
                    break
    except TimeoutError:
        pytest.fail("No SSE event received within 5 seconds after status transition")

    # 5. Verify event structure
    assert event_data.event_type == "appointment.checked_in"
    assert event_data.appointment_id == appointment_id
    assert event_data.dentist_id == sse_test_dentist.id
    expected_name = f"{sse_test_patient.first_name} {sse_test_patient.last_name}"
    assert event_data.patient_name == expected_name
    assert event_data.status == "CHECKED_IN"

    # 6. Cleanup
    await broadcaster.unsubscribe(queue)


# ---------------------------------------------------------------------------
# Test 2: test_sse_stream_emits_keep_alive_ping_comment
# ---------------------------------------------------------------------------


async def test_sse_stream_emits_keep_alive_ping_comment(
    sse_receptionist_headers: dict[str, str],
    client: AsyncClient,
) -> None:
    """R-15: SSE stream emits keep-alive ping comment every 15 seconds.

    Given an idle SSE connection,
    When 15 seconds elapse without an appointment event,
    Then a keep-alive comment (': ping') is emitted.
    """
    # Connect to SSE endpoint
    async with client.stream(
        "GET",
        "/api/v1/appointments/live",
        headers=sse_receptionist_headers,
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Read lines until we get a ping comment
        ping_received = False
        lines_read = 0

        async for line in response.aiter_lines():
            lines_read += 1
            if line.startswith(": ping"):
                ping_received = True
                break
            # Safety: don't read forever
            if lines_read > 500:
                break

        assert ping_received, "SSE stream did not emit a : ping comment after 15 seconds"



# ---------------------------------------------------------------------------
# Additional: SSE endpoint authentication
# ---------------------------------------------------------------------------


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
    """Multiple concurrent SSE connections all receive events."""
    clinic_tz = ZoneInfo("America/New_York")
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    # Create appointment
    create_resp = await client.post(
        "/api/v1/appointments",
        headers=sse_receptionist_headers,
        json={
            "patientId": str(sse_test_patient.id),
            "dentistId": str(sse_test_dentist.id),
            "serviceId": str(sse_test_service.id),
            "startTime": start_time,
        },
    )
    assert create_resp.status_code == 201
    appointment_id = UUID(create_resp.json()["id"])

    # Create 3 SSE connections
    connections = []
    responses = []
    for _ in range(3):
        conn = client.stream(
            "GET",
            "/api/v1/appointments/live",
            headers=sse_receptionist_headers,
        )
        response = await conn.__aenter__()
        responses.append(response)
        connections.append(conn)

    # Wait for connections to be fully established
    await asyncio.sleep(0.2)

    async def wait_for_checked_in(response) -> bool:
        """Wait for checked_in event on a single connection."""
        async for line in response.aiter_lines():
            if line.startswith("event: appointment.checked_in"):
                return True
        return False

    try:
        # Trigger event
        confirmed_resp = await client.post(
            f"/api/v1/appointments/{appointment_id}/status",
            headers=sse_receptionist_headers,
            json={"toStatus": "CONFIRMED"},
        )
        assert confirmed_resp.status_code == 200
        checked_in_resp = await client.post(
            f"/api/v1/appointments/{appointment_id}/status",
            headers=sse_receptionist_headers,
            json={"toStatus": "CHECKED_IN"},
        )
        assert checked_in_resp.status_code == 200

        # Read from all connections concurrently
        results = await asyncio.gather(*[wait_for_checked_in(r) for r in responses])
        events_received = sum(results)
        assert events_received == len(responses), (
            f"Expected all {len(responses)} SSE subscribers to receive the event; "
            f"only {events_received} did"
        )
    finally:
        for conn in connections:
            await conn.__aexit__(None, None, None)


async def test_sse_disconnect_cleans_up_subscription(
    sse_receptionist_headers: dict[str, str],
    client: AsyncClient,
) -> None:
    """Client disconnect cleans up subscription (broadcaster count decreases)."""
    broadcaster = get_event_broadcaster()
    initial_count = await broadcaster.subscriber_count

    # Open SSE connection
    conn = client.stream(
        "GET",
        "/api/v1/appointments/live",
        headers=sse_receptionist_headers,
    )
    await conn.__aenter__()

    try:
        # Retry subscriber count with longer wait (endpoint may take time to register)
        for _ in range(10):
            await asyncio.sleep(0.2)
            if await broadcaster.subscriber_count == initial_count + 1:
                break
        else:
            pytest.fail("SSE endpoint did not register a subscriber within 2 seconds")
    finally:
        # Close connection
        await conn.__aexit__(None, None, None)

    # Wait a moment for cleanup
    await asyncio.sleep(0.1)
    assert await broadcaster.subscriber_count == initial_count
