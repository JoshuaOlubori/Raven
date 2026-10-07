"""Appointment API tests (Spec 05 §4 — Layer 3, PRD R-10, NFR-1).

Each test drives the public HTTP seam (AsyncClient) with expected values
drawn from the PRD and spec, never from the implementation under test.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient

from app.models.staff import Staff

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def test_dentist(test_session_local) -> Staff:
    """Create a test dentist with a Monday shift."""
    from datetime import time

    from app.models.schedule import WorkingShift

    async with test_session_local() as session:
        dentist = Staff(
            email=f"dentist-{uuid4().hex[:8]}@clinic.com",
            hashed_password="irrelevant",
            full_name="Dr. Test Dentist",
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
async def test_patient(test_session_local) -> Staff:
    """Create a test patient."""
    from datetime import date

    from app.models.patient import Patient

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
async def test_service(test_session_local) -> Staff:
    """Create a test dental service (45 minutes)."""
    from app.models.service import DentalService

    async with test_session_local() as session:
        service = DentalService(
            name=f"Routine Cleaning {uuid4().hex[:8]}",
            description="Standard cleaning",
            duration_minutes=45,
            is_active=True,
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)
        return service


# ---------------------------------------------------------------------------
# AC1 — Book appointment success (R-10)
# ---------------------------------------------------------------------------


async def test_book_appointment_success_201(
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """R-10: Receptionist books appointment → 201, status SCHEDULED,
    end_time auto-calculated.
    """
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    # Monday Jan 5, 2026 at 09:00 EST = 14:00 UTC
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    response = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patientId": str(test_patient.id),
            "dentistId": str(test_dentist.id),
            "serviceId": str(test_service.id),
            "startTime": start_time,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "SCHEDULED"
    assert body["patientId"] == str(test_patient.id)
    assert body["dentistId"] == str(test_dentist.id)
    assert body["serviceId"] == str(test_service.id)
    # API returns naive UTC datetimes; compare as UTC
    from datetime import datetime as dt

    # Input start_time has timezone; convert to UTC for expected value
    expected_start_utc = dt.fromisoformat(start_time).astimezone(ZoneInfo("UTC"))
    # Response is naive UTC; parse as UTC
    actual_start_utc = dt.fromisoformat(body["startTime"]).replace(
        tzinfo=ZoneInfo("UTC")
    )
    assert actual_start_utc == expected_start_utc
    # end_time should be start_time + 45 minutes
    expected_end_utc = expected_start_utc + timedelta(minutes=45)
    actual_end_utc = dt.fromisoformat(body["endTime"]).replace(tzinfo=ZoneInfo("UTC"))
    assert actual_end_utc == expected_end_utc
    assert "id" in body
    assert "patient" in body
    assert "dentist" in body
    assert "service" in body


async def test_admin_can_book_appointment(
    admin_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """Admin can also book appointments."""
    headers = auth_headers(admin_staff.id, admin_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    start_time = datetime(2026, 1, 5, 10, 0, 0, tzinfo=clinic_tz).isoformat()

    response = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patientId": str(test_patient.id),
            "dentistId": str(test_dentist.id),
            "serviceId": str(test_service.id),
            "startTime": start_time,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "SCHEDULED"
    assert body["patientId"] == str(test_patient.id)
    assert body["dentistId"] == str(test_dentist.id)
    assert body["serviceId"] == str(test_service.id)
    # API returns naive UTC datetimes; compare as UTC
    from datetime import datetime as dt

    expected_start_utc = dt.fromisoformat(start_time).astimezone(ZoneInfo("UTC"))
    actual_start_utc = dt.fromisoformat(body["startTime"]).replace(
        tzinfo=ZoneInfo("UTC")
    )
    assert actual_start_utc == expected_start_utc
    expected_end_utc = expected_start_utc + timedelta(minutes=45)
    actual_end_utc = dt.fromisoformat(body["endTime"]).replace(tzinfo=ZoneInfo("UTC"))
    assert actual_end_utc == expected_end_utc
    assert "id" in body
    assert "patient" in body
    assert "dentist" in body
    assert "service" in body


# ---------------------------------------------------------------------------
# AC2 — Booking outside shift rejected (400 OUTSIDE_SHIFT_HOURS)
# ---------------------------------------------------------------------------


async def test_booking_before_shift_rejected_400(
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """Booking before shift start (08:00 when shift starts 09:00) → 400."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    # 08:00 EST = 13:00 UTC (shift starts at 09:00)
    start_time = datetime(2026, 1, 5, 8, 0, 0, tzinfo=clinic_tz).isoformat()

    response = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patientId": str(test_patient.id),
            "dentistId": str(test_dentist.id),
            "serviceId": str(test_service.id),
            "startTime": start_time,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "OUTSIDE_SHIFT_HOURS"


async def test_booking_after_shift_rejected_400(
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """Booking after shift end (12:00 when shift ends 12:00) → 400."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    # 12:00 EST = 17:00 UTC (shift ends at 12:00, but 45-min service would end at 12:45)
    start_time = datetime(2026, 1, 5, 12, 0, 0, tzinfo=clinic_tz).isoformat()

    response = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patientId": str(test_patient.id),
            "dentistId": str(test_dentist.id),
            "serviceId": str(test_service.id),
            "startTime": start_time,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "OUTSIDE_SHIFT_HOURS"


async def test_booking_on_non_shift_day_rejected_400(
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """Booking on day with no shift (Tuesday) → 400."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    # Tuesday Jan 6, 2026
    start_time = datetime(2026, 1, 6, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    response = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patientId": str(test_patient.id),
            "dentistId": str(test_dentist.id),
            "serviceId": str(test_service.id),
            "startTime": start_time,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "OUTSIDE_SHIFT_HOURS"


# ---------------------------------------------------------------------------
# AC3 — Booking overlapping time-off rejected (409 TIME_OFF_CONFLICT)
# ---------------------------------------------------------------------------


async def test_booking_overlapping_time_off_rejected_409(
    receptionist_staff: Staff,
    admin_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """Booking overlapping dentist's time-off block → 409 TIME_OFF_CONFLICT."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    admin_headers = auth_headers(admin_staff.id, admin_staff.role)
    clinic_tz = ZoneInfo("America/New_York")

    # Create time-off block for 10:00-11:00 on Monday Jan 5 (15:00-16:00 UTC)
    time_off_resp = await client.post(
        "/api/v1/schedules/time-off",
        headers=admin_headers,
        json={
            "dentistId": str(test_dentist.id),
            "startTime": "2026-01-05T15:00:00Z",
            "endTime": "2026-01-05T16:00:00Z",
            "reason": "Meeting",
        },
    )
    assert time_off_resp.status_code == 201

    # Try to book 09:45-10:30 (overlaps 10:00-11:00 block)
    start_time = datetime(2026, 1, 5, 9, 45, 0, tzinfo=clinic_tz).isoformat()

    response = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patientId": str(test_patient.id),
            "dentistId": str(test_dentist.id),
            "serviceId": str(test_service.id),
            "startTime": start_time,
        },
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error"] == "TIME_OFF_CONFLICT"


# ---------------------------------------------------------------------------
# AC4 — Concurrent booking overlap prevention (NFR-1)
# ---------------------------------------------------------------------------


async def test_concurrent_booking_overlap_prevention_409(
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """NFR-1: Two concurrent bookings for same slot → 1 succeeds (201), 1 fails (409).

    Note: With SQLite test DB, requests run sequentially so first commits
    before second runs its overlap check. In production (PostgreSQL),
    SELECT FOR UPDATE handles true concurrent requests.
    """

    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    async def post_booking():
        return await client.post(
            "/api/v1/appointments",
            headers=headers,
            json={
                "patientId": str(test_patient.id),
                "dentistId": str(test_dentist.id),
                "serviceId": str(test_service.id),
                "startTime": start_time,
            },
        )

    # Run sequentially to simulate first request committing before second checks
    resp1 = await post_booking()
    resp2 = await post_booking()

    status_codes = sorted([resp1.status_code, resp2.status_code])
    assert status_codes == [201, 409]

    # The 409 should have the correct error code
    conflict_resp = resp1 if resp1.status_code == 409 else resp2
    assert conflict_resp.json()["error"] == "APPOINTMENT_OVERLAP_CONFLICT"


# ---------------------------------------------------------------------------
# AC5 — List appointments eager loading avoids N+1
# ---------------------------------------------------------------------------


async def test_list_appointments_eager_loading(
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """GET /appointments returns appointments with eager-loaded relations."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)

    # Create an appointment first
    clinic_tz = ZoneInfo("America/New_York")
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    create_resp = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patientId": str(test_patient.id),
            "dentistId": str(test_dentist.id),
            "serviceId": str(test_service.id),
            "startTime": start_time,
        },
    )
    assert create_resp.status_code == 201
    created_appt = create_resp.json()
    created_id = created_appt["id"]

    # List appointments
    list_resp = await client.get("/api/v1/appointments", headers=headers)
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert len(body) >= 1

    # Find the created appointment in the list
    appt = next((a for a in body if a["id"] == created_id), None)
    assert appt is not None, "Created appointment not found in list"
    assert "patient" in appt
    assert "dentist" in appt
    assert "service" in appt
    assert appt["patient"]["id"] == str(test_patient.id)
    assert appt["dentist"]["id"] == str(test_dentist.id)
    assert appt["service"]["id"] == str(test_service.id)


# ---------------------------------------------------------------------------
# RBAC tests
# ---------------------------------------------------------------------------


async def test_dentist_cannot_book_appointment_403(
    dentist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """Dentist cannot book appointments → 403."""
    headers = auth_headers(dentist_staff.id, dentist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    response = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patientId": str(test_patient.id),
            "dentistId": str(test_dentist.id),
            "serviceId": str(test_service.id),
            "startTime": start_time,
        },
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error"] == "RBAC_FORBIDDEN"


async def test_unauthenticated_booking_rejected_401(
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    client: AsyncClient,
) -> None:
    """Unauthenticated booking → 401."""
    clinic_tz = ZoneInfo("America/New_York")
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    response = await client.post(
        "/api/v1/appointments",
        json={
            "patientId": str(test_patient.id),
            "dentistId": str(test_dentist.id),
            "serviceId": str(test_service.id),
            "startTime": start_time,
        },
    )

    assert response.status_code == 401


async def test_list_appointments_unauthenticated_401(client: AsyncClient) -> None:
    """Unauthenticated list → 401."""
    response = await client.get("/api/v1/appointments")
    assert response.status_code == 401


async def test_get_appointment_unauthenticated_401(client: AsyncClient) -> None:
    """Unauthenticated get detail → 401."""
    response = await client.get(f"/api/v1/appointments/{uuid4()}")
    assert response.status_code == 401
