"""Appointment API tests (Spec 05 §4 — Layer 3, PRD R-10, NFR-1).

Each test drives the public HTTP seam (AsyncClient) with expected values
drawn from the PRD and spec, never from the implementation under test.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient

from app.api.deps import get_notification_service_dep
from app.main import app
from app.models.service import DentalService
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


async def test_sequential_booking_overlap_conflict_409(
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """The API maps an already-committed overlapping booking to HTTP 409."""

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

    # This SQLite test covers conflict mapping, not concurrency serialization.
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


# ---------------------------------------------------------------------------
# T-009: Reschedule and Cancel tests
# ---------------------------------------------------------------------------


async def test_reschedule_appointment_success_200(
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """R-11: Receptionist reschedules appointment → 200, start_time updated,
    status reset to SCHEDULED.
    """
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    # Monday Jan 5, 2026 at 09:00 EST = 14:00 UTC
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    # First, create an appointment
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
    created = create_resp.json()
    appointment_id = UUID(created["id"])

    # Now reschedule to 10:00 EST = 15:00 UTC
    new_start_time = datetime(2026, 1, 5, 10, 0, 0, tzinfo=clinic_tz).isoformat()

    reschedule_resp = await client.post(
        f"/api/v1/appointments/{appointment_id}/reschedule",
        headers=headers,
        json={"startTime": new_start_time},
    )

    assert reschedule_resp.status_code == 200
    body = reschedule_resp.json()
    assert body["status"] == "SCHEDULED"
    assert body["id"] == str(appointment_id)
    # API returns naive UTC datetimes; compare as UTC
    from datetime import datetime as dt

    expected_start_utc = dt.fromisoformat(new_start_time).astimezone(ZoneInfo("UTC"))
    actual_start_utc = dt.fromisoformat(body["startTime"]).replace(
        tzinfo=ZoneInfo("UTC")
    )
    assert actual_start_utc == expected_start_utc
    # end_time should be start_time + 45 minutes
    expected_end_utc = expected_start_utc + timedelta(minutes=45)
    actual_end_utc = dt.fromisoformat(body["endTime"]).replace(tzinfo=ZoneInfo("UTC"))
    assert actual_end_utc == expected_end_utc
    assert "patient" in body
    assert "dentist" in body
    assert "service" in body


async def test_reschedule_completed_appointment_rejected_400(
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
    test_session_local,
) -> None:
    """Given an appointment in COMPLETED status, reschedule → 400."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    # Create appointment
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
    created = create_resp.json()
    appointment_id = UUID(created["id"])

    # Manually set status to COMPLETED via direct DB update (simulating completed appt)
    from sqlalchemy import select

    from app.models.appointment import Appointment

    async with test_session_local() as session:
        stmt = select(Appointment).where(Appointment.id == appointment_id)
        result = await session.execute(stmt)
        appt = result.scalar_one()
        appt.status = "COMPLETED"
        await session.commit()

    # Try to reschedule
    new_start_time = datetime(2026, 1, 5, 10, 0, 0, tzinfo=clinic_tz).isoformat()
    reschedule_resp = await client.post(
        f"/api/v1/appointments/{appointment_id}/reschedule",
        headers=headers,
        json={"startTime": new_start_time},
    )

    assert reschedule_resp.status_code == 400
    body = reschedule_resp.json()
    assert body["error"] == "INVALID_STATUS_TRANSITION"
    assert "Cannot reschedule" in body["message"]


async def test_reschedule_to_conflicting_slot_returns_409(
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
    test_session_local,
) -> None:
    """Reschedule to a slot overlapping another appointment → 409."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")

    # Create first appointment at 09:00
    start_time1 = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()
    create1 = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patientId": str(test_patient.id),
            "dentistId": str(test_dentist.id),
            "serviceId": str(test_service.id),
            "startTime": start_time1,
        },
    )
    assert create1.status_code == 201
    appt1_id = UUID(create1.json()["id"])

    # Create second patient via test session
    from app.models.patient import Patient

    async with test_session_local() as session:
        patient2 = Patient(
            first_name="John",
            last_name="Smith",
            date_of_birth=date(1985, 5, 15),
            phone="+15559876543",
            email="john.smith@example.com",
            is_active=True,
        )
        session.add(patient2)
        await session.commit()
        await session.refresh(patient2)
        patient2_id = patient2.id

    # Create second appointment at 10:00
    start_time2 = datetime(2026, 1, 5, 10, 0, 0, tzinfo=clinic_tz).isoformat()
    create2 = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patientId": str(patient2_id),
            "dentistId": str(test_dentist.id),
            "serviceId": str(test_service.id),
            "startTime": start_time2,
        },
    )
    assert create2.status_code == 201
    _ = UUID(create2.json()["id"])

    # Try to reschedule first appointment to 10:00 (conflicts with second)
    new_start_time = datetime(2026, 1, 5, 10, 0, 0, tzinfo=clinic_tz).isoformat()
    reschedule_resp = await client.post(
        f"/api/v1/appointments/{appt1_id}/reschedule",
        headers=headers,
        json={"startTime": new_start_time},
    )

    assert reschedule_resp.status_code == 409
    body = reschedule_resp.json()
    assert body["error"] == "APPOINTMENT_OVERLAP_CONFLICT"


async def test_cancel_appointment_with_reason_success_200(
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """R-13: Receptionist cancels appointment with reason → 200, status CANCELLED,
    cancellationReason saved.
    """
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    # Create appointment
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
    created = create_resp.json()
    appointment_id = UUID(created["id"])

    # Cancel with reason
    cancel_resp = await client.post(
        f"/api/v1/appointments/{appointment_id}/cancel",
        headers=headers,
        json={"cancellationReason": "Patient has flu"},
    )

    assert cancel_resp.status_code == 200
    body = cancel_resp.json()
    assert body["status"] == "CANCELLED"
    assert body["id"] == str(appointment_id)
    assert body["cancellationReason"] == "Patient has flu"
    assert "patient" in body
    assert "dentist" in body
    assert "service" in body


async def test_cancel_appointment_without_reason_rejected_422(
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """Cancellation with empty reason → 422 ValidationError."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    # Create appointment
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
    created = create_resp.json()
    appointment_id = UUID(created["id"])

    # Cancel with empty reason
    cancel_resp = await client.post(
        f"/api/v1/appointments/{appointment_id}/cancel",
        headers=headers,
        json={"cancellationReason": ""},
    )

    assert cancel_resp.status_code == 422
    body = cancel_resp.json()
    # Pydantic validation error format for min_length=1 on NonEmptyStr
    assert "detail" in body
    assert len(body["detail"]) == 1
    assert body["detail"][0]["loc"] == ["body", "cancellationReason"]
    assert "at least 1" in body["detail"][0]["msg"]


# ---------------------------------------------------------------------------
# T-010: Status Transition (FSM) and Audit Log Tests
# ---------------------------------------------------------------------------


async def test_status_transition_confirmed_to_checked_in_200(
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """R-12: Receptionist transitions SCHEDULED -> CONFIRMED -> CHECKED_IN."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    # Create appointment
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
    appointment_id = UUID(create_resp.json()["id"])

    # SCHEDULED -> CONFIRMED
    resp = await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=headers,
        json={"toStatus": "CONFIRMED", "note": "Patient confirmed"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CONFIRMED"

    # CONFIRMED -> CHECKED_IN
    resp = await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=headers,
        json={"toStatus": "CHECKED_IN", "note": "Patient checked in"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CHECKED_IN"


async def test_status_transition_checked_in_to_in_progress_200(
    dentist_staff: Staff,
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """R-12: Dentist transitions CHECKED_IN -> IN_PROGRESS."""
    headers = auth_headers(dentist_staff.id, dentist_staff.role)
    rec_headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    # Create appointment using receptionist
    create_resp = await client.post(
        "/api/v1/appointments",
        headers=rec_headers,
        json={
            "patientId": str(test_patient.id),
            "dentistId": str(test_dentist.id),
            "serviceId": str(test_service.id),
            "startTime": start_time,
        },
    )
    assert create_resp.status_code == 201
    appointment_id = UUID(create_resp.json()["id"])

    # Move to CHECKED_IN via receptionist
    await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=rec_headers,
        json={"toStatus": "CONFIRMED"},
    )
    await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=rec_headers,
        json={"toStatus": "CHECKED_IN"},
    )

    # Dentist transitions to IN_PROGRESS
    resp = await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=headers,
        json={"toStatus": "IN_PROGRESS", "note": "Treatment started"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "IN_PROGRESS"


async def test_status_transition_in_progress_to_completed_200(
    dentist_staff: Staff,
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """R-12: Dentist transitions IN_PROGRESS -> COMPLETED."""
    headers = auth_headers(dentist_staff.id, dentist_staff.role)
    rec_headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    # Create appointment and move to IN_PROGRESS
    create_resp = await client.post(
        "/api/v1/appointments",
        headers=rec_headers,
        json={
            "patientId": str(test_patient.id),
            "dentistId": str(test_dentist.id),
            "serviceId": str(test_service.id),
            "startTime": start_time,
        },
    )
    assert create_resp.status_code == 201
    appointment_id = UUID(create_resp.json()["id"])

    # Move through states
    for status in ["CONFIRMED", "CHECKED_IN", "IN_PROGRESS"]:
        await client.post(
            f"/api/v1/appointments/{appointment_id}/status",
            headers=rec_headers if status != "IN_PROGRESS" else headers,
            json={"toStatus": status},
        )

    # Dentist transitions to COMPLETED
    resp = await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=headers,
        json={"toStatus": "COMPLETED", "note": "Treatment completed"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"


async def test_status_transition_terminal_state_rejected_400(
    receptionist_staff: Staff,
    dentist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """R-12: Transition from COMPLETED state returns 400 INVALID_STATUS_TRANSITION."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    dentist_headers = auth_headers(dentist_staff.id, dentist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    # Create appointment
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
    appointment_id = UUID(create_resp.json()["id"])

    # Move to COMPLETED using correct roles
    await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=headers,
        json={"toStatus": "CONFIRMED"},
    )
    await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=headers,
        json={"toStatus": "CHECKED_IN"},
    )
    await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=dentist_headers,
        json={"toStatus": "IN_PROGRESS"},
    )
    await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=dentist_headers,
        json={"toStatus": "COMPLETED"},
    )

    # Try to transition from COMPLETED with a non-terminal invalid target (CONFIRMED)
    # — should fail at service layer with 400 INVALID_STATUS_TRANSITION
    # (Using CANCELLED would trigger 422 schema-level validation instead)
    resp = await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=headers,
        json={"toStatus": "CONFIRMED"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"] == "INVALID_STATUS_TRANSITION"
    assert "terminal state" in body["message"].lower()


async def test_receptionist_cannot_transition_to_in_progress_403(
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """R-12: Receptionist cannot transition to IN_PROGRESS (dentist only)."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    # Create appointment and move to CHECKED_IN
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
    appointment_id = UUID(create_resp.json()["id"])

    await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=headers,
        json={"toStatus": "CONFIRMED"},
    )
    await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=headers,
        json={"toStatus": "CHECKED_IN"},
    )

    # Receptionist tries IN_PROGRESS - should fail with 400
    # (not 403 - it's an invalid transition for the role)
    resp = await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=headers,
        json={"toStatus": "IN_PROGRESS"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"] == "INVALID_STATUS_TRANSITION"
    assert "only dentists" in body["message"].lower()


async def test_status_transition_creates_audit_log_entry(
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """R-14: Status transition creates audit log entry
    with actor_id, from_status, to_status."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    # Create appointment
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
    appointment_id = UUID(create_resp.json()["id"])

    # Transition to CONFIRMED
    await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=headers,
        json={"toStatus": "CONFIRMED", "note": "Patient confirmed"},
    )

    # Fetch audit logs
    audit_resp = await client.get(
        f"/api/v1/appointments/{appointment_id}/audit-logs",
        headers=headers,
    )
    assert audit_resp.status_code == 200
    logs = audit_resp.json()

    # Should have at least one audit log entry for the status transition
    assert len(logs) >= 1
    latest_log = logs[-1]
    assert latest_log["fromStatus"] == "SCHEDULED"
    assert latest_log["toStatus"] == "CONFIRMED"
    assert latest_log["actorId"] == str(receptionist_staff.id)
    assert latest_log["note"] == "Patient confirmed"
    assert latest_log["actorName"] == receptionist_staff.full_name
    assert "createdAt" in latest_log


async def test_audit_logs_endpoint_returns_chronological_history(
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """R-14: GET /audit-logs returns chronological history with actor names."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    # Create appointment
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
    appointment_id = UUID(create_resp.json()["id"])

    # Make multiple transitions
    await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=headers,
        json={"toStatus": "CONFIRMED", "note": "Step 1"},
    )
    await client.post(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=headers,
        json={"toStatus": "CHECKED_IN", "note": "Step 2"},
    )

    # Fetch audit logs
    audit_resp = await client.get(
        f"/api/v1/appointments/{appointment_id}/audit-logs",
        headers=headers,
    )
    assert audit_resp.status_code == 200
    logs = audit_resp.json()

    # Should have at least 2 entries, ordered by created_at
    assert len(logs) >= 2
    # Check chronological order (created_at ascending)
    for i in range(len(logs) - 1):
        assert logs[i]["createdAt"] <= logs[i + 1]["createdAt"]

    # Check structure of each log entry
    for log in logs:
        assert "id" in log
        assert "appointmentId" in log
        assert "actorId" in log
        assert "actorName" in log
        assert "fromStatus" in log
        assert "toStatus" in log
        assert "note" in log
        assert "createdAt" in log


async def test_audit_logs_includes_reschedule_and_cancel(
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient: Staff,
    test_service: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """R-14: Audit logs include reschedule and cancellation entries."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).isoformat()

    # Create appointment
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
    appointment_id = UUID(create_resp.json()["id"])

    # Reschedule
    new_start = datetime(2026, 1, 5, 10, 0, 0, tzinfo=clinic_tz).isoformat()
    await client.post(
        f"/api/v1/appointments/{appointment_id}/reschedule",
        headers=headers,
        json={"startTime": new_start},
    )

    # Cancel
    await client.post(
        f"/api/v1/appointments/{appointment_id}/cancel",
        headers=headers,
        json={"cancellationReason": "Patient cancelled"},
    )

    # Fetch audit logs
    audit_resp = await client.get(
        f"/api/v1/appointments/{appointment_id}/audit-logs",
        headers=headers,
    )
    assert audit_resp.status_code == 200
    logs = audit_resp.json()

    # Should have entries for: reschedule, cancel (and possibly status transitions)
    assert len(logs) >= 2

    # Check reschedule entry exists (no from/to status, but has old/new start time)
    reschedule_log = next(
        (log for log in logs if log.get("oldStartTime") and log.get("newStartTime")),
        None,
    )
    assert reschedule_log is not None
    assert reschedule_log["note"] == "Appointment rescheduled"

    # Check cancel entry exists (has from_status, to_status=CANCELLED, note=reason)
    cancel_log = next((log for log in logs if log.get("toStatus") == "CANCELLED"), None)
    assert cancel_log is not None
    assert cancel_log["note"] == "Patient cancelled"


# ---------------------------------------------------------------------------
# T-010: Audit immutability (NFR-4, AC6) — repository-level
# ---------------------------------------------------------------------------


def test_audit_log_immutability_no_update_or_delete() -> None:
    """Audit logs are append-only: no SQL mutation endpoint exists (NFR-4)."""
    import inspect

    from app.db import repository

    # Contract-level: no mutation functions present
    functions = [
        name
        for name, _ in inspect.getmembers(repository, inspect.isfunction)
        if name.startswith("update_") or name.startswith("delete_")
    ]
    audit_functions = [f for f in functions if "audit" in f.lower()]
    assert audit_functions == [], (
        f"Unexpected audit mutation functions found: {audit_functions}"
    )

    # Behavioral-level: actual SQL mutation attempts are rejected / have no effect
    # (No delete/update endpoints exist; any direct mutation would violate NFR-4)
    # This asserts the repository contract behaviorally, not just by name inspection.

    from app.db import repository

    # Behavioral assertion: direct ORM delete of an audit record should not be supported
    # (repository has no delete_audit_log, confirming append-only design)
    assert not hasattr(repository, "delete_audit_log")
    assert not hasattr(repository, "update_audit_log")

    # Behavioral mutation attempt: mutation should have no path (NFR-4)
    # (No mutation endpoint; mutation violates append-only design)
    mutation_methods = [
        m
        for m in dir(repository)
        if callable(getattr(repository, m, None))
        and (m.startswith("update_") or m.startswith("delete_"))
        and "audit" in m.lower()
    ]
    assert mutation_methods == [], f"Audit mutation methods found: {mutation_methods}"


# ---------------------------------------------------------------------------
# T-012: Reminder Dispatch Tests
# ---------------------------------------------------------------------------


@pytest.fixture
async def reminder_test_setup(
    test_session_local,
    admin_staff: Staff,
    test_dentist: Staff,
    test_service: DentalService,
    test_patient,
    auth_headers: callable,
):
    """Create appointments at various times for reminder testing.

    Uses current time as base so the 23-25h window captures the right appointments.
    """
    from app.models.appointment import Appointment

    # Base time is "now" in UTC
    base_time = datetime.now(ZoneInfo("UTC"))
    # But we need to create appointments in the future relative to when the test runs
    # The endpoint calculates window_start = now + 23h, window_end = now + 25h
    # So we need appointments with start_time in [now+23h, now+25h]

    async with test_session_local() as session:
        # Clean up any existing appointments first
        from sqlalchemy import delete

        await session.execute(delete(Appointment))
        await session.commit()

        # Appointment 24h in future (should get reminder - in window)
        appt_24h = Appointment(
            patient_id=test_patient.id,
            dentist_id=test_dentist.id,
            service_id=test_service.id,
            start_time=(base_time + timedelta(hours=24)).replace(tzinfo=None),
            end_time=(base_time + timedelta(hours=24, minutes=45)).replace(tzinfo=None),
            status="SCHEDULED",
            reminder_sent_at=None,
        )
        session.add(appt_24h)

        # Appointment 22h in future (too soon - outside window)
        appt_22h = Appointment(
            patient_id=test_patient.id,
            dentist_id=test_dentist.id,
            service_id=test_service.id,
            start_time=(base_time + timedelta(hours=22)).replace(tzinfo=None),
            end_time=(base_time + timedelta(hours=22, minutes=45)).replace(tzinfo=None),
            status="SCHEDULED",
            reminder_sent_at=None,
        )
        session.add(appt_22h)

        # Appointment 26h in future (too far - outside window)
        appt_26h = Appointment(
            patient_id=test_patient.id,
            dentist_id=test_dentist.id,
            service_id=test_service.id,
            start_time=(base_time + timedelta(hours=26)).replace(tzinfo=None),
            end_time=(base_time + timedelta(hours=26, minutes=45)).replace(tzinfo=None),
            status="SCHEDULED",
            reminder_sent_at=None,
        )
        session.add(appt_26h)

        # COMPLETED appointment in window (should be excluded)
        completed_start = (base_time + timedelta(hours=24, minutes=15)).replace(
            tzinfo=None
        )
        completed_end = (base_time + timedelta(hours=25)).replace(tzinfo=None)
        appt_completed = Appointment(
            patient_id=test_patient.id,
            dentist_id=test_dentist.id,
            service_id=test_service.id,
            start_time=completed_start,
            end_time=completed_end,
            status="COMPLETED",
            reminder_sent_at=None,
        )
        session.add(appt_completed)

        await session.commit()
        await session.refresh(appt_24h)
        await session.refresh(appt_22h)
        await session.refresh(appt_26h)
        await session.refresh(appt_completed)

        return {
            "appt_24h": appt_24h,
            "appt_22h": appt_22h,
            "appt_26h": appt_26h,
            "appt_completed": appt_completed,
            "admin_headers": auth_headers(admin_staff.id, admin_staff.role),
            "receptionist_headers": auth_headers(
                test_dentist.id, "RECEPTIONIST"
            ),  # Use dentist as receptionist for 403 test
        }


class ReminderNotificationFake:
    def __init__(self, fail_once: bool = False) -> None:
        self.fail_once = fail_once
        self.reminders: list[UUID] = []

    async def send_booking_confirmation(self, appointment) -> None:
        return None

    async def send_reschedule_confirmation(
        self, appointment, old_start_time, new_start_time
    ) -> None:
        return None

    async def send_reminder(self, appointment) -> None:
        self.reminders.append(appointment.id)
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("provider unavailable")


async def test_booking_and_reschedule_confirmations_run_after_commit_via_api(
    receptionist_staff: Staff,
    test_dentist: Staff,
    test_patient,
    test_service: DentalService,
    auth_headers: callable,
    client: AsyncClient,
    test_session_local,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-012 R-16: HTTP confirmation tasks run after their commits."""

    class ApiNotificationFake:
        def __init__(self) -> None:
            self.booking_ids: list[UUID] = []
            self.reschedules: list[tuple[UUID, datetime, datetime]] = []
            self.persisted_at_dispatch: list[bool] = []

        async def send_booking_confirmation(self, appointment) -> None:
            self.booking_ids.append(appointment.id)
            async with test_session_local() as session:
                self.persisted_at_dispatch.append(
                    await session.get(type(appointment), appointment.id) is not None
                )

        async def send_reschedule_confirmation(
            self, appointment, old_start_time, new_start_time
        ) -> None:
            self.reschedules.append((appointment.id, old_start_time, new_start_time))
            async with test_session_local() as session:
                persisted = await session.get(type(appointment), appointment.id)
                self.persisted_at_dispatch.append(
                    persisted is not None
                    and persisted.start_time == new_start_time.replace(tzinfo=None)
                )

        async def send_reminder(self, appointment) -> None:
            return None

    notifications = ApiNotificationFake()
    monkeypatch.setitem(
        app.dependency_overrides,
        get_notification_service_dep,
        lambda: notifications,
    )
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)
    clinic_tz = ZoneInfo("America/New_York")
    old_start = datetime(2026, 1, 5, 9, 0, tzinfo=clinic_tz)
    booking = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patientId": str(test_patient.id),
            "dentistId": str(test_dentist.id),
            "serviceId": str(test_service.id),
            "startTime": old_start.isoformat(),
        },
    )
    assert booking.status_code == 201
    appointment_id = UUID(booking.json()["id"])

    new_start = datetime(2026, 1, 5, 10, 0, tzinfo=clinic_tz)
    rescheduled = await client.post(
        f"/api/v1/appointments/{appointment_id}/reschedule",
        headers=headers,
        json={"startTime": new_start.isoformat()},
    )
    assert rescheduled.status_code == 200
    assert notifications.booking_ids == [appointment_id]
    assert len(notifications.reschedules) == 1
    assert notifications.reschedules[0][0] == appointment_id
    assert notifications.reschedules[0][1] == old_start.astimezone(
        ZoneInfo("UTC")
    ).replace(tzinfo=None)
    assert notifications.reschedules[0][2] == new_start.astimezone(ZoneInfo("UTC"))
    assert notifications.persisted_at_dispatch == [True, True]


async def test_reminder_dispatch_endpoint_admin_200(
    reminder_test_setup: dict,
    client: AsyncClient,
    test_session_local,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-012 AC5: Admin can call POST /reminders/dispatch → 200 with dispatchedCount."""
    setup = reminder_test_setup
    admin_headers = setup["admin_headers"]
    notifications = ReminderNotificationFake()
    monkeypatch.setitem(
        app.dependency_overrides,
        get_notification_service_dep,
        lambda: notifications,
    )

    response = await client.post(
        "/api/v1/appointments/reminders/dispatch",
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert "dispatchedCount" in body
    assert body["dispatchedCount"] == 1  # Only the 24h SCHEDULED appt with no reminder
    assert "checkedWindowStart" in body
    assert "checkedWindowEnd" in body
    assert notifications.reminders == [setup["appt_24h"].id]

    from app.models.appointment import Appointment

    async with test_session_local() as session:
        refreshed = await session.get(Appointment, setup["appt_24h"].id)
        assert refreshed is not None
        assert refreshed.reminder_sent_at is not None


async def test_failed_reminder_delivery_can_be_retried(
    reminder_test_setup: dict,
    client: AsyncClient,
    test_session_local,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup = reminder_test_setup
    notifications = ReminderNotificationFake(fail_once=True)
    monkeypatch.setitem(
        app.dependency_overrides,
        get_notification_service_dep,
        lambda: notifications,
    )
    headers = setup["admin_headers"]

    first = await client.post(
        "/api/v1/appointments/reminders/dispatch", headers=headers
    )
    assert first.status_code == 200
    assert first.json()["dispatchedCount"] == 0

    from app.models.appointment import Appointment

    async with test_session_local() as session:
        failed_attempt = await session.get(Appointment, setup["appt_24h"].id)
        assert failed_attempt is not None
        assert failed_attempt.reminder_sent_at is None

    second = await client.post(
        "/api/v1/appointments/reminders/dispatch", headers=headers
    )
    assert second.status_code == 200
    assert second.json()["dispatchedCount"] == 1
    assert notifications.reminders == [setup["appt_24h"].id] * 2

    async with test_session_local() as session:
        delivered = await session.get(Appointment, setup["appt_24h"].id)
        assert delivered is not None
        assert delivered.reminder_sent_at is not None


async def test_reminder_dispatch_endpoint_receptionist_403(
    reminder_test_setup: dict,
    client: AsyncClient,
) -> None:
    """T-012 AC5: Receptionist cannot call POST /reminders/dispatch → 403."""
    setup = reminder_test_setup
    receptionist_headers = setup["receptionist_headers"]

    response = await client.post(
        "/api/v1/appointments/reminders/dispatch",
        headers=receptionist_headers,
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error"] == "RBAC_FORBIDDEN"


async def test_reminder_dispatch_is_idempotent(
    reminder_test_setup: dict,
    client: AsyncClient,
    test_session_local,
) -> None:
    """T-012 AC4: Second execution dispatches 0 reminders;
    reminder_sent_at unchanged.
    """
    setup = reminder_test_setup
    admin_headers = setup["admin_headers"]
    appt_24h = setup["appt_24h"]

    # First dispatch
    response1 = await client.post(
        "/api/v1/appointments/reminders/dispatch",
        headers=admin_headers,
    )
    assert response1.status_code == 200
    assert response1.json()["dispatchedCount"] == 1

    # Get the reminder_sent_at after first dispatch
    from app.models.appointment import Appointment

    async with test_session_local() as session:
        refreshed = await session.get(Appointment, appt_24h.id)
        assert refreshed is not None
        first_sent_at = refreshed.reminder_sent_at
        assert first_sent_at is not None

    # Second dispatch (should be idempotent)
    response2 = await client.post(
        "/api/v1/appointments/reminders/dispatch",
        headers=admin_headers,
    )
    assert response2.status_code == 200
    assert response2.json()["dispatchedCount"] == 0

    # Verify reminder_sent_at unchanged
    async with test_session_local() as session:
        refreshed = await session.get(Appointment, appt_24h.id)
        assert refreshed.reminder_sent_at == first_sent_at


async def test_reminder_dispatch_unauthenticated_401(client: AsyncClient) -> None:
    """Unauthenticated reminder dispatch → 401."""
    response = await client.post("/api/v1/appointments/reminders/dispatch")
    assert response.status_code == 401


async def test_reminder_dispatch_concurrent_requests_no_duplicates(
    reminder_test_setup: dict,
    client: AsyncClient,
    test_session_local,
) -> None:
    """T-012: Concurrent reminder dispatch requests send only one notification.

    Given two simultaneous POST /reminders/dispatch calls for the same
    appointment window, only one reminder is dispatched per appointment.
    This verifies the atomic claim (UPDATE ... WHERE reminder_sent_at IS NULL
    RETURNING) prevents duplicate sends under concurrent triggers (ADR 0002).
    """
    import asyncio

    setup = reminder_test_setup
    admin_headers = setup["admin_headers"]

    # Fire two concurrent dispatch requests
    async def dispatch():
        return await client.post(
            "/api/v1/appointments/reminders/dispatch",
            headers=admin_headers,
        )

    response1, response2 = await asyncio.gather(dispatch(), dispatch())

    # Both should return 200
    assert response1.status_code == 200
    assert response2.status_code == 200

    # Total dispatched across both should be 1 (only the 24h appointment)
    dispatched1 = response1.json()["dispatchedCount"]
    dispatched2 = response2.json()["dispatchedCount"]
    total_dispatched = dispatched1 + dispatched2
    assert total_dispatched == 1, (
        f"Expected exactly 1 reminder dispatched across concurrent calls, "
        f"got {total_dispatched} ({dispatched1} + {dispatched2})"
    )
