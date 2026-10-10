"""Repository tests for appointments (Spec 05 §3 — Layer 2, §9).

Tests cover:
- CRUD operations
- Eager loading avoids N+1
- Overlap check
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.repository import (
    check_appointment_overlap,
    create_appointment,
    get_appointment_detail,
    list_appointments,
    list_pending_reminders,
    mark_reminder_sent,
)
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.schedule import WorkingShift
from app.models.service import DentalService
from app.models.staff import Staff

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def repo_dentist(test_session_local: async_sessionmaker) -> Staff:
    """Create a dentist with a Monday shift."""
    async with test_session_local() as session:
        dentist = Staff(
            email=f"repo-dentist-{uuid4().hex[:8]}@clinic.com",
            hashed_password="irrelevant",
            full_name="Dr. Repo Test",
            role="DENTIST",
            is_active=True,
        )
        session.add(dentist)
        await session.flush()

        shift = WorkingShift(
            dentist_id=dentist.id,
            day_of_week=0,  # Monday
            start_time=datetime.min.time().replace(hour=9),
            end_time=datetime.min.time().replace(hour=12),
        )
        session.add(shift)
        await session.commit()
        await session.refresh(dentist)
        return dentist


@pytest.fixture
async def repo_patient(test_session_local: async_sessionmaker) -> Patient:
    """Create a test patient."""
    from datetime import date

    async with test_session_local() as session:
        patient = Patient(
            first_name="Repo",
            last_name="Patient",
            date_of_birth=date(1990, 1, 1),
            phone="+15551234567",
            is_active=True,
        )
        session.add(patient)
        await session.commit()
        await session.refresh(patient)
        return patient


@pytest.fixture
async def repo_service(test_session_local: async_sessionmaker) -> DentalService:
    """Create a test service."""
    async with test_session_local() as session:
        service = DentalService(
            name=f"Repo Service {uuid4().hex[:8]}",
            duration_minutes=45,
            is_active=True,
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)
        return service


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_create_and_get_appointment(
    test_session_local: async_sessionmaker,
    repo_dentist: Staff,
    repo_patient: Patient,
    repo_service: DentalService,
) -> None:
    """Create appointment and fetch by ID."""
    async with test_session_local() as session:
        clinic_tz = ZoneInfo("America/New_York")
        start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).astimezone(
            ZoneInfo("UTC")
        )
        end_time = start_time + timedelta(minutes=45)

        appointment = await create_appointment(
            session,
            patient_id=repo_patient.id,
            dentist_id=repo_dentist.id,
            service_id=repo_service.id,
            start_time=start_time,
            end_time=end_time,
        )
        await session.commit()

        # Fetch by ID
        fetched = await get_appointment_detail(session, appointment.id)
        assert fetched is not None
        assert fetched.id == appointment.id
        assert fetched.patient_id == repo_patient.id
        assert fetched.dentist_id == repo_dentist.id
        assert fetched.service_id == repo_service.id
        # Repository stores naive UTC; compare as naive UTC
        assert fetched.start_time == start_time.replace(tzinfo=None)
        assert fetched.end_time == end_time.replace(tzinfo=None)
        assert fetched.status == "SCHEDULED"

        # Verify eager-loaded relations
        assert fetched.patient is not None
        assert fetched.patient.id == repo_patient.id
        assert fetched.dentist is not None
        assert fetched.dentist.id == repo_dentist.id
        assert fetched.service is not None
        assert fetched.service.id == repo_service.id


async def test_list_appointments_eager_loading_no_n_plus_one(
    test_session_local: async_sessionmaker,
    repo_dentist: Staff,
    repo_patient: Patient,
    repo_service: DentalService,
) -> None:
    """List appointments with eager loading - no N+1 queries."""
    async with test_session_local() as session:
        clinic_tz = ZoneInfo("America/New_York")
        start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).astimezone(
            ZoneInfo("UTC")
        )
        end_time = start_time + timedelta(minutes=45)

        # Create multiple appointments
        for i in range(3):
            await create_appointment(
                session,
                patient_id=repo_patient.id,
                dentist_id=repo_dentist.id,
                service_id=repo_service.id,
                start_time=start_time + timedelta(minutes=60 * i),
                end_time=end_time + timedelta(minutes=60 * i),
            )
        await session.commit()

        # List appointments - should eager load patient, dentist, service
        appointments = await list_appointments(session)
        assert len(appointments) >= 3

        for appt in appointments:
            # These should not trigger additional queries
            assert appt.patient is not None
            assert appt.dentist is not None
            assert appt.service is not None


async def test_check_appointment_overlap_true(
    test_session_local: async_sessionmaker,
    repo_dentist: Staff,
    repo_patient: Patient,
    repo_service: DentalService,
) -> None:
    """check_appointment_overlap returns True when overlap exists."""
    async with test_session_local() as session:
        clinic_tz = ZoneInfo("America/New_York")
        start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).astimezone(
            ZoneInfo("UTC")
        )
        end_time = start_time + timedelta(minutes=45)

        # Create first appointment
        await create_appointment(
            session,
            patient_id=repo_patient.id,
            dentist_id=repo_dentist.id,
            service_id=repo_service.id,
            start_time=start_time,
            end_time=end_time,
        )
        await session.commit()

        # Check for overlap - exact same time
        has_overlap = await check_appointment_overlap(
            session, repo_dentist.id, start_time, end_time
        )
        assert has_overlap is True

        # Check for overlap - partial overlap (starts during existing)
        partial_start = start_time + timedelta(minutes=15)
        partial_end = partial_start + timedelta(minutes=45)
        has_overlap = await check_appointment_overlap(
            session, repo_dentist.id, partial_start, partial_end
        )
        assert has_overlap is True

        # Check for overlap - partial overlap (ends during existing)
        partial_start = start_time - timedelta(minutes=15)
        partial_end = start_time + timedelta(minutes=15)
        has_overlap = await check_appointment_overlap(
            session, repo_dentist.id, partial_start, partial_end
        )
        assert has_overlap is True

        # Check for overlap - existing contained in new window
        big_start = start_time - timedelta(minutes=30)
        big_end = end_time + timedelta(minutes=30)
        has_overlap = await check_appointment_overlap(
            session, repo_dentist.id, big_start, big_end
        )
        assert has_overlap is True


async def test_check_appointment_overlap_false(
    test_session_local: async_sessionmaker,
    repo_dentist: Staff,
    repo_patient: Patient,
    repo_service: DentalService,
) -> None:
    """check_appointment_overlap returns False when no overlap."""
    async with test_session_local() as session:
        clinic_tz = ZoneInfo("America/New_York")
        start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).astimezone(
            ZoneInfo("UTC")
        )
        end_time = start_time + timedelta(minutes=45)

        # Create first appointment
        await create_appointment(
            session,
            patient_id=repo_patient.id,
            dentist_id=repo_dentist.id,
            service_id=repo_service.id,
            start_time=start_time,
            end_time=end_time,
        )
        await session.commit()

        # Check for non-overlap - before existing
        before_start = start_time - timedelta(hours=2)
        before_end = start_time
        has_overlap = await check_appointment_overlap(
            session, repo_dentist.id, before_start, before_end
        )
        assert has_overlap is False

        # Check for non-overlap - after existing
        after_start = end_time
        after_end = after_start + timedelta(minutes=45)
        has_overlap = await check_appointment_overlap(
            session, repo_dentist.id, after_start, after_end
        )
        assert has_overlap is False

        # Check for non-overlap - different dentist
        other_dentist = Staff(
            email=f"other-{uuid4().hex[:8]}@clinic.com",
            hashed_password="irrelevant",
            full_name="Dr. Other",
            role="DENTIST",
            is_active=True,
        )
        session.add(other_dentist)
        await session.flush()
        has_overlap = await check_appointment_overlap(
            session, other_dentist.id, start_time, end_time
        )
        assert has_overlap is False


async def test_check_appointment_overlap_excludes_cancelled(
    test_session_local: async_sessionmaker,
    repo_dentist: Staff,
    repo_patient: Patient,
    repo_service: DentalService,
) -> None:
    """check_appointment_overlap ignores CANCELLED appointments."""
    async with test_session_local() as session:
        clinic_tz = ZoneInfo("America/New_York")
        start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).astimezone(
            ZoneInfo("UTC")
        )
        end_time = start_time + timedelta(minutes=45)

        # Create CANCELLED appointment
        cancelled = Appointment(
            patient_id=repo_patient.id,
            dentist_id=repo_dentist.id,
            service_id=repo_service.id,
            start_time=start_time,
            end_time=end_time,
            status="CANCELLED",
        )
        session.add(cancelled)
        await session.commit()

        # Should not detect overlap with cancelled appointment
        has_overlap = await check_appointment_overlap(
            session, repo_dentist.id, start_time, end_time
        )
        assert has_overlap is False


async def test_check_appointment_overlap_exclude_id(
    test_session_local: async_sessionmaker,
    repo_dentist: Staff,
    repo_patient: Patient,
    repo_service: DentalService,
) -> None:
    """check_appointment_overlap can exclude an appointment by ID (for reschedule)."""
    async with test_session_local() as session:
        clinic_tz = ZoneInfo("America/New_York")
        start_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).astimezone(
            ZoneInfo("UTC")
        )
        end_time = start_time + timedelta(minutes=45)

        # Create appointment
        appointment = await create_appointment(
            session,
            patient_id=repo_patient.id,
            dentist_id=repo_dentist.id,
            service_id=repo_service.id,
            start_time=start_time,
            end_time=end_time,
        )
        await session.commit()

        # Check overlap excluding this appointment's ID
        has_overlap = await check_appointment_overlap(
            session, repo_dentist.id, start_time, end_time, exclude_id=appointment.id
        )
        assert has_overlap is False

        # Without exclude_id, should detect overlap
        has_overlap = await check_appointment_overlap(
            session, repo_dentist.id, start_time, end_time
        )
        assert has_overlap is True


# ---------------------------------------------------------------------------
# Reminder query tests (Spec 06 §3, T-012)
# ---------------------------------------------------------------------------


async def test_list_pending_reminders_selects_23_to_25h_window(
    test_session_local: async_sessionmaker,
    repo_dentist: Staff,
    repo_patient: Patient,
    repo_service: DentalService,
) -> None:
    """T-012 AC3: list_pending_reminders selects appointments in 23-25h
    window with reminder_sent_at NULL.

    - 24h appointment (in window) should be included
    - 22h appointment (too soon) should be excluded
    - 26h appointment (too far) should be excluded
    """
    from datetime import timedelta

    async with test_session_local() as session:
        clinic_tz = ZoneInfo("America/New_York")
        # Base time: Monday Jan 5, 2026 at 09:00 EST = 14:00 UTC
        base_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).astimezone(
            ZoneInfo("UTC")
        )

        # Create 3 appointments at different offsets from base_time
        # 24h in the future (within 23-25h window) - SHOULD BE INCLUDED
        appt_24h = await create_appointment(
            session,
            patient_id=repo_patient.id,
            dentist_id=repo_dentist.id,
            service_id=repo_service.id,
            start_time=base_time + timedelta(hours=24),
            end_time=base_time + timedelta(hours=24, minutes=45),
            status="SCHEDULED",
        )

        # 22h in the future (outside window - too soon) - SHOULD BE EXCLUDED
        _appt_22h = await create_appointment(
            session,
            patient_id=repo_patient.id,
            dentist_id=repo_dentist.id,
            service_id=repo_service.id,
            start_time=base_time + timedelta(hours=22),
            end_time=base_time + timedelta(hours=22, minutes=45),
            status="SCHEDULED",
        )

        # 26h in the future (outside window - too far) - SHOULD BE EXCLUDED
        _appt_26h = await create_appointment(
            session,
            patient_id=repo_patient.id,
            dentist_id=repo_dentist.id,
            service_id=repo_service.id,
            start_time=base_time + timedelta(hours=26),
            end_time=base_time + timedelta(hours=26, minutes=45),
            status="SCHEDULED",
        )

        # 24h but reminder already sent - SHOULD BE EXCLUDED
        appt_24h_sent = await create_appointment(
            session,
            patient_id=repo_patient.id,
            dentist_id=repo_dentist.id,
            service_id=repo_service.id,
            start_time=base_time + timedelta(hours=24, minutes=30),
            end_time=base_time + timedelta(hours=25, minutes=15),
            status="SCHEDULED",
        )
        appt_24h_sent.reminder_sent_at = base_time.replace(tzinfo=None)
        session.add(appt_24h_sent)

        # COMPLETED appointment in window - SHOULD BE EXCLUDED
        _appt_completed = await create_appointment(
            session,
            patient_id=repo_patient.id,
            dentist_id=repo_dentist.id,
            service_id=repo_service.id,
            start_time=base_time + timedelta(hours=24, minutes=15),
            end_time=base_time + timedelta(hours=25),
            status="COMPLETED",
        )

        await session.commit()

        # Query with window: 23-25 hours from base_time
        window_start = base_time + timedelta(hours=23)
        window_end = base_time + timedelta(hours=25)

        pending = await list_pending_reminders(session, window_start, window_end)

        # Only the 24h SCHEDULED appointment with
        # reminder_sent_at NULL should be returned
        assert len(pending) == 1
        assert pending[0].id == appt_24h.id
        assert pending[0].reminder_sent_at is None
        assert pending[0].status == "SCHEDULED"

        # Verify eager-loaded relations
        assert pending[0].patient is not None
        assert pending[0].dentist is not None
        assert pending[0].service is not None


async def test_mark_reminder_sent_idempotent(
    test_session_local: async_sessionmaker,
    repo_dentist: Staff,
    repo_patient: Patient,
    repo_service: DentalService,
) -> None:
    """T-012 AC4: mark_reminder_sent is idempotent - second call affects zero rows."""
    from datetime import timedelta

    async with test_session_local() as session:
        clinic_tz = ZoneInfo("America/New_York")
        base_time = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).astimezone(
            ZoneInfo("UTC")
        )

        appointment = await create_appointment(
            session,
            patient_id=repo_patient.id,
            dentist_id=repo_dentist.id,
            service_id=repo_service.id,
            start_time=base_time + timedelta(hours=24),
            end_time=base_time + timedelta(hours=24, minutes=45),
            status="SCHEDULED",
        )
        await session.commit()

        # First call - should set reminder_sent_at
        sent_at_1 = base_time + timedelta(hours=1)
        await mark_reminder_sent(session, appointment.id, sent_at_1)
        await session.commit()

        # Verify it was set
        refreshed = await session.get(Appointment, appointment.id)
        assert refreshed.reminder_sent_at is not None
        # Database stores timezone-aware UTC; compare with timezone-aware value
        assert refreshed.reminder_sent_at == sent_at_1

        # Second call - should NOT change reminder_sent_at (idempotent)
        sent_at_2 = base_time + timedelta(hours=2)
        await mark_reminder_sent(session, appointment.id, sent_at_2)
        await session.commit()

        # Verify reminder_sent_at is unchanged (still first timestamp)
        refreshed = await session.get(Appointment, appointment.id)
        assert refreshed.reminder_sent_at == sent_at_1
