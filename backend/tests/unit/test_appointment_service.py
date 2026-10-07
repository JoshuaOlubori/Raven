"""Unit tests for appointment booking domain logic (Spec 05 §3, §9).

Tests cover:
- Booking validation (shift coverage, time-off conflict, overlap guard)
- Auto-calculation of end_time from service duration
- FSM state machine transitions (future tickets)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from app.exceptions import (
    AppointmentOverlapConflictError,
    OutsideShiftHoursError,
    ServiceNotFoundError,
    TimeOffConflictError,
)
from app.models import (
    DentalService,
    Staff,
    WorkingShift,
)
from app.services.appointment_service import AppointmentService

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def clinic_tz() -> ZoneInfo:
    return ZoneInfo("America/New_York")


@pytest.fixture
async def appointment_service(test_session_local, clinic_tz) -> AppointmentService:
    """Create an AppointmentService with a test session and settings."""
    from app.config import Settings

    settings = Settings()
    settings.clinic_timezone = "America/New_York"
    async with test_session_local() as session:
        yield AppointmentService(session=session, settings=settings)


@pytest.fixture
async def test_dentist(test_session_local, override_dbsession) -> Staff:
    """Create a test dentist."""
    async with test_session_local() as session:
        dentist = Staff(
            email=f"dentist-{uuid4().hex[:8]}@clinic.com",
            hashed_password="irrelevant",
            full_name="Dr. Test Dentist",
            role="DENTIST",
            is_active=True,
        )
        session.add(dentist)
        await session.commit()
        await session.refresh(dentist)
        return dentist


@pytest.fixture
async def test_patient(test_session_local, override_dbsession):
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
async def test_service(test_session_local, override_dbsession) -> DentalService:
    """Create a test dental service (45 minutes)."""
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


@pytest.fixture
async def monday_shift(
    test_session_local, test_dentist: Staff, override_dbsession
) -> WorkingShift:
    """Create a Monday 09:00-12:00 shift for the test dentist."""
    from datetime import time

    async with test_session_local() as session:
        shift = WorkingShift(
            dentist_id=test_dentist.id,
            day_of_week=0,  # Monday
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        session.add(shift)
        await session.commit()
        await session.refresh(shift)
        return shift


# ---------------------------------------------------------------------------
# AC1: test_book_appointment_success_201
# ---------------------------------------------------------------------------


async def test_book_appointment_success(
    appointment_service: AppointmentService,
    test_dentist: Staff,
    test_patient,
    test_service: DentalService,
    monday_shift: WorkingShift,
    clinic_tz: ZoneInfo,
) -> None:
    """R-10: Given an open available slot, booking creates appointment
    with SCHEDULED status and auto-calculated end_time.
    """
    # Target date: Monday Jan 5, 2026 (non-DST)
    target_date = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).astimezone(
        ZoneInfo("UTC")
    )

    appointment = await appointment_service.book_appointment(
        patient_id=test_patient.id,
        dentist_id=test_dentist.id,
        service_id=test_service.id,
        start_time=target_date,
        current_user_role="RECEPTIONIST",
    )

    assert appointment.status == "SCHEDULED"
    assert appointment.patient_id == test_patient.id
    assert appointment.dentist_id == test_dentist.id
    assert appointment.service_id == test_service.id
    # Service converts to naive UTC; compare as naive UTC
    expected_start_utc = target_date.replace(tzinfo=None)
    assert appointment.start_time == expected_start_utc
    # end_time = start_time + 45 minutes
    expected_end_utc = expected_start_utc + timedelta(minutes=45)
    assert appointment.end_time == expected_end_utc


# ---------------------------------------------------------------------------
# AC2: test_booking_outside_shift_rejected_400
# ---------------------------------------------------------------------------


async def test_booking_outside_shift_rejected(
    appointment_service: AppointmentService,
    test_dentist: Staff,
    test_patient,
    test_service: DentalService,
    monday_shift: WorkingShift,
    clinic_tz: ZoneInfo,
) -> None:
    """Request outside dentist's shift hours returns 400 OUTSIDE_SHIFT_HOURS."""
    # Target date: Monday Jan 5, 2026 - try to book at 08:00 (before 09:00 shift)
    target_date = datetime(2026, 1, 5, 8, 0, 0, tzinfo=clinic_tz).astimezone(
        ZoneInfo("UTC")
    )

    with pytest.raises(OutsideShiftHoursError):
        await appointment_service.book_appointment(
            patient_id=test_patient.id,
            dentist_id=test_dentist.id,
            service_id=test_service.id,
            start_time=target_date,
            current_user_role="RECEPTIONIST",
        )


async def test_booking_on_non_shift_day_rejected(
    appointment_service: AppointmentService,
    test_dentist: Staff,
    test_patient,
    test_service: DentalService,
    clinic_tz: ZoneInfo,
) -> None:
    """Given a request on a day with no shifts, returns 400 OUTSIDE_SHIFT_HOURS."""
    # Target date: Tuesday Jan 6, 2026 (no shift for Tuesday)
    target_date = datetime(2026, 1, 6, 9, 0, 0, tzinfo=clinic_tz).astimezone(
        ZoneInfo("UTC")
    )

    with pytest.raises(OutsideShiftHoursError):
        await appointment_service.book_appointment(
            patient_id=test_patient.id,
            dentist_id=test_dentist.id,
            service_id=test_service.id,
            start_time=target_date,
            current_user_role="RECEPTIONIST",
        )


# ---------------------------------------------------------------------------
# AC3: test_booking_overlapping_time_off_rejected_409
# ---------------------------------------------------------------------------


async def test_booking_overlapping_time_off_rejected(
    appointment_service: AppointmentService,
    test_dentist: Staff,
    test_patient,
    test_service: DentalService,
    monday_shift: WorkingShift,
    clinic_tz: ZoneInfo,
) -> None:
    """Given a request overlapping a time-off block, returns 409 TIME_OFF_CONFLICT."""
    from app.db.repository import create_time_off_block

    # Add time-off block for 10:00-11:00 on Monday Jan 5, 2026
    async with appointment_service._session as session:
        block_start = datetime(2026, 1, 5, 15, 0, 0)  # 10:00 EST = 15:00 UTC
        block_end = datetime(2026, 1, 5, 16, 0, 0)  # 11:00 EST = 16:00 UTC
        await create_time_off_block(
            session,
            dentist_id=test_dentist.id,
            start_time=block_start,
            end_time=block_end,
            reason="Meeting",
        )
        await session.commit()

    # Try to book 09:45-10:30 (overlaps 10:00-11:00 block)
    target_date = datetime(2026, 1, 5, 9, 45, 0, tzinfo=clinic_tz).astimezone(
        ZoneInfo("UTC")
    )

    with pytest.raises(TimeOffConflictError):
        await appointment_service.book_appointment(
            patient_id=test_patient.id,
            dentist_id=test_dentist.id,
            service_id=test_service.id,
            start_time=target_date,
            current_user_role="RECEPTIONIST",
        )


# ---------------------------------------------------------------------------
# AC4: test_concurrent_booking_overlap_prevention_409
# ---------------------------------------------------------------------------


async def test_concurrent_booking_overlap_prevention(
    test_session_local,
    test_dentist: Staff,
    test_patient,
    test_service: DentalService,
    clinic_tz: ZoneInfo,
    monday_shift: WorkingShift,
) -> None:
    """NFR-1: Concurrent requests for same slot → one succeeds, one fails 409.

    Note: With SQLite, we commit first so second sees it. In PostgreSQL,
    SELECT FOR UPDATE handles true concurrent requests.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.config import Settings

    settings = Settings()
    settings.clinic_timezone = "America/New_York"
    target_date = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).astimezone(
        ZoneInfo("UTC")
    )

    # Create two separate sessions to simulate concurrent requests
    async def attempt_booking(session: AsyncSession) -> bool:
        """Try to book the same slot, return True if success."""
        service = AppointmentService(session=session, settings=settings)
        try:
            await service.book_appointment(
                patient_id=test_patient.id,
                dentist_id=test_dentist.id,
                service_id=test_service.id,
                start_time=target_date,
                current_user_role="RECEPTIONIST",
            )
            return True
        except AppointmentOverlapConflictError:
            return False

    # Run two bookings sequentially with commit in between to simulate
    # concurrent requests where first commits before second checks
    async with test_session_local() as session1:
        result1 = await attempt_booking(session1)
        await session1.commit()

    async with test_session_local() as session2:
        result2 = await attempt_booking(session2)

    # Exactly one should succeed, one should fail
    assert sum([result1, result2]) == 1


# ---------------------------------------------------------------------------
# Additional validation tests
# ---------------------------------------------------------------------------


async def test_booking_inactive_service_rejected(
    appointment_service: AppointmentService,
    test_dentist: Staff,
    test_patient,
    monday_shift: WorkingShift,
    clinic_tz: ZoneInfo,
) -> None:
    """Booking with inactive service raises ServiceNotFoundError."""
    async with appointment_service._session as session:
        service = DentalService(
            name=f"Inactive Service {uuid4().hex[:8]}",
            duration_minutes=30,
            is_active=False,
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)

    target_date = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).astimezone(
        ZoneInfo("UTC")
    )

    with pytest.raises(ServiceNotFoundError):
        await appointment_service.book_appointment(
            patient_id=test_patient.id,
            dentist_id=test_dentist.id,
            service_id=service.id,
            start_time=target_date,
            current_user_role="RECEPTIONIST",
        )


async def test_booking_nonexistent_service_rejected(
    appointment_service: AppointmentService,
    test_dentist: Staff,
    test_patient,
    clinic_tz: ZoneInfo,
) -> None:
    """Booking with nonexistent service raises ServiceNotFoundError."""
    target_date = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).astimezone(
        ZoneInfo("UTC")
    )

    with pytest.raises(ServiceNotFoundError):
        await appointment_service.book_appointment(
            patient_id=test_patient.id,
            dentist_id=test_dentist.id,
            service_id=uuid4(),
            start_time=target_date,
            current_user_role="RECEPTIONIST",
        )
