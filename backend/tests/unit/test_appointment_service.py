"""Unit tests for appointment booking domain logic (Spec 05 §3, §9).

Tests cover:
- Booking validation (shift coverage, time-off conflict, overlap guard)
- Auto-calculation of end_time from service duration
- FSM state machine transitions (future tickets)
- Confirmation and reminder dispatch (T-012)
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
    Appointment,
    DentalService,
    Staff,
    WorkingShift,
)
from app.services.appointment_service import AppointmentService
from app.services.notification_service import NotificationService

# ---------------------------------------------------------------------------
# Test helper: FakeNotificationService for capturing dispatched notifications
# ---------------------------------------------------------------------------


class FakeNotificationService(NotificationService):
    """Fake notification service that captures dispatched notifications for testing."""

    def __init__(self) -> None:
        self.dispatched_bookings: list[Appointment] = []
        self.dispatched_reschedules: list[tuple[Appointment, datetime, datetime]] = []
        self.dispatched_reminders: list[Appointment] = []

    async def send_booking_confirmation(self, appointment: Appointment) -> None:
        self.dispatched_bookings.append(appointment)

    async def send_reschedule_confirmation(
        self,
        appointment: Appointment,
        old_start_time: datetime,
        new_start_time: datetime,
    ) -> None:
        self.dispatched_reschedules.append(
            (appointment, old_start_time, new_start_time)
        )

    async def send_reminder(self, appointment: Appointment) -> None:
        self.dispatched_reminders.append(appointment)


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
        )


# ---------------------------------------------------------------------------
# Sequential overlap conflict behavior; PostgreSQL concurrency is covered by
# tests/integration/test_postgres_appointment_concurrency.py.
# ---------------------------------------------------------------------------


async def test_sequential_booking_overlap_conflict(
    test_session_local,
    test_dentist: Staff,
    test_patient,
    test_service: DentalService,
    clinic_tz: ZoneInfo,
    monday_shift: WorkingShift,
) -> None:
    """A second booking fails after the first transaction commits."""
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.config import Settings

    settings = Settings()
    settings.clinic_timezone = "America/New_York"
    target_date = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).astimezone(
        ZoneInfo("UTC")
    )

    # Use separate SQLite sessions to check the sequential conflict case.
    async def attempt_booking(session: AsyncSession) -> bool:
        """Try to book the same slot, return True if success."""
        service = AppointmentService(session=session, settings=settings)
        try:
            await service.book_appointment(
                patient_id=test_patient.id,
                dentist_id=test_dentist.id,
                service_id=test_service.id,
                start_time=target_date,
            )
            return True
        except AppointmentOverlapConflictError:
            return False

    # Commit the first booking before the second session checks for overlap.
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
        )


# ---------------------------------------------------------------------------
# FSM State Machine Tests (T-010)
# ---------------------------------------------------------------------------


@pytest.fixture
async def test_receptionist(test_session_local) -> Staff:
    """Create a test receptionist."""
    async with test_session_local() as session:
        receptionist = Staff(
            email=f"receptionist-{uuid4().hex[:8]}@clinic.com",
            hashed_password="irrelevant",
            full_name="Test Receptionist",
            role="RECEPTIONIST",
            is_active=True,
        )
        session.add(receptionist)
        await session.commit()
        await session.refresh(receptionist)
        return receptionist


@pytest.fixture
async def test_admin(test_session_local) -> Staff:
    """Create a test admin."""
    async with test_session_local() as session:
        admin = Staff(
            email=f"admin-{uuid4().hex[:8]}@clinic.com",
            hashed_password="irrelevant",
            full_name="Test Admin",
            role="ADMIN",
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        return admin


@pytest.fixture
async def booked_appointment(
    appointment_service: AppointmentService,
    test_dentist: Staff,
    test_patient,
    test_service: DentalService,
    monday_shift: WorkingShift,
    clinic_tz: ZoneInfo,
) -> Staff:
    """Create a booked appointment in SCHEDULED state."""
    target_date = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).astimezone(
        ZoneInfo("UTC")
    )
    appointment = await appointment_service.book_appointment(
        patient_id=test_patient.id,
        dentist_id=test_dentist.id,
        service_id=test_service.id,
        start_time=target_date,
    )
    return appointment


async def test_fsm_valid_lifecycle_transitions(
    appointment_service: AppointmentService,
    booked_appointment,
    test_dentist: Staff,
    test_receptionist: Staff,
) -> None:
    """Test 1: Valid FSM transitions SCHEDULED -> CONFIRMED ->
    CHECKED_IN -> IN_PROGRESS -> COMPLETED."""
    appointment = booked_appointment

    # SCHEDULED -> CONFIRMED (receptionist)
    appointment = await appointment_service.transition_status(
        appointment_id=appointment.id,
        to_status="CONFIRMED",
        note="Patient confirmed",
        actor_id=test_receptionist.id,
        actor_role="RECEPTIONIST",
    )
    assert appointment.status == "CONFIRMED"

    # CONFIRMED -> CHECKED_IN (receptionist)
    appointment = await appointment_service.transition_status(
        appointment_id=appointment.id,
        to_status="CHECKED_IN",
        note="Patient checked in",
        actor_id=test_receptionist.id,
        actor_role="RECEPTIONIST",
    )
    assert appointment.status == "CHECKED_IN"

    # CHECKED_IN -> IN_PROGRESS (dentist)
    appointment = await appointment_service.transition_status(
        appointment_id=appointment.id,
        to_status="IN_PROGRESS",
        note="Treatment started",
        actor_id=test_dentist.id,
        actor_role="DENTIST",
    )
    assert appointment.status == "IN_PROGRESS"

    # IN_PROGRESS -> COMPLETED (dentist)
    appointment = await appointment_service.transition_status(
        appointment_id=appointment.id,
        to_status="COMPLETED",
        note="Treatment completed",
        actor_id=test_dentist.id,
        actor_role="DENTIST",
    )
    assert appointment.status == "COMPLETED"


async def test_fsm_terminal_state_rejects_transition(
    appointment_service: AppointmentService,
    booked_appointment,
    test_dentist: Staff,
    test_receptionist: Staff,
) -> None:
    """Test 2: Terminal states (COMPLETED, CANCELLED, NO_SHOW)
    reject all transitions."""
    from app.exceptions import InvalidStateTransitionError

    appointment = booked_appointment

    # First transition to COMPLETED
    appointment = await appointment_service.transition_status(
        appointment_id=appointment.id,
        to_status="CONFIRMED",
        note="Confirmed",
        actor_id=test_receptionist.id,
        actor_role="RECEPTIONIST",
    )
    appointment = await appointment_service.transition_status(
        appointment_id=appointment.id,
        to_status="CHECKED_IN",
        note="Checked in",
        actor_id=test_receptionist.id,
        actor_role="RECEPTIONIST",
    )
    appointment = await appointment_service.transition_status(
        appointment_id=appointment.id,
        to_status="IN_PROGRESS",
        note="Treatment started",
        actor_id=test_dentist.id,
        actor_role="DENTIST",
    )
    appointment = await appointment_service.transition_status(
        appointment_id=appointment.id,
        to_status="COMPLETED",
        note="Treatment completed",
        actor_id=test_dentist.id,
        actor_role="DENTIST",
    )
    assert appointment.status == "COMPLETED"

    # Try to transition from COMPLETED - should fail
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        await appointment_service.transition_status(
            appointment_id=appointment.id,
            to_status="CANCELLED",
            note="Trying to cancel",
            actor_id=test_receptionist.id,
            actor_role="RECEPTIONIST",
        )
    assert "terminal state" in str(exc_info.value).lower()

    # Also test CANCELLED terminal state
    # Use a different time slot to avoid overlap
    from datetime import timedelta

    target_date2 = appointment.start_time + timedelta(hours=2)
    appointment2 = await appointment_service.book_appointment(
        patient_id=appointment.patient_id,
        dentist_id=appointment.dentist_id,
        service_id=appointment.service_id,
        start_time=target_date2,
    )
    appointment2 = await appointment_service.transition_status(
        appointment_id=appointment2.id,
        to_status="CONFIRMED",
        note="Confirmed",
        actor_id=test_receptionist.id,
        actor_role="RECEPTIONIST",
    )
    appointment2 = await appointment_service.cancel_appointment(
        appointment_id=appointment2.id,
        cancellation_reason="Patient cancelled",
        actor_id=test_receptionist.id,
    )
    assert appointment2.status == "CANCELLED"

    # Try to transition from CANCELLED - should fail
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        await appointment_service.transition_status(
            appointment_id=appointment2.id,
            to_status="CONFIRMED",
            note="Trying to confirm",
            actor_id=test_receptionist.id,
            actor_role="RECEPTIONIST",
        )
    assert "terminal state" in str(exc_info.value).lower()


async def test_fsm_invalid_transition_rejected(
    appointment_service: AppointmentService,
    booked_appointment,
    test_receptionist: Staff,
) -> None:
    """Test: Invalid transitions (e.g., SCHEDULED -> COMPLETED) are rejected."""
    from app.exceptions import InvalidStateTransitionError

    appointment = booked_appointment

    # Try to skip states: SCHEDULED -> COMPLETED (invalid)
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        await appointment_service.transition_status(
            appointment_id=appointment.id,
            to_status="COMPLETED",
            note="Trying to complete",
            actor_id=test_receptionist.id,
            actor_role="RECEPTIONIST",
        )
    assert "invalid transition" in str(exc_info.value).lower()


async def test_fsm_dentist_only_transitions(
    appointment_service: AppointmentService,
    booked_appointment,
    test_dentist: Staff,
    test_receptionist: Staff,
) -> None:
    """Test 3: Only dentists can transition to IN_PROGRESS and COMPLETED."""
    from app.exceptions import InvalidStateTransitionError

    appointment = booked_appointment

    # Move to CHECKED_IN first (receptionist can do this)
    appointment = await appointment_service.transition_status(
        appointment_id=appointment.id,
        to_status="CONFIRMED",
        note="Confirmed",
        actor_id=test_receptionist.id,
        actor_role="RECEPTIONIST",
    )
    appointment = await appointment_service.transition_status(
        appointment_id=appointment.id,
        to_status="CHECKED_IN",
        note="Checked in",
        actor_id=test_receptionist.id,
        actor_role="RECEPTIONIST",
    )

    # Receptionist tries IN_PROGRESS - should fail (dentist only)
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        await appointment_service.transition_status(
            appointment_id=appointment.id,
            to_status="IN_PROGRESS",
            note="Starting treatment",
            actor_id=test_receptionist.id,
            actor_role="RECEPTIONIST",
        )
    assert "only dentists can transition" in str(exc_info.value).lower()

    # Move to IN_PROGRESS using dentist
    appointment = await appointment_service.transition_status(
        appointment_id=appointment.id,
        to_status="IN_PROGRESS",
        note="Treatment started",
        actor_id=test_dentist.id,
        actor_role="DENTIST",
    )

    # Receptionist tries COMPLETED - should fail (dentist only)
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        await appointment_service.transition_status(
            appointment_id=appointment.id,
            to_status="COMPLETED",
            note="Completing treatment",
            actor_id=test_receptionist.id,
            actor_role="RECEPTIONIST",
        )
    assert "only dentists can transition" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# T-012: Confirmation and Reminder Dispatch Tests
# ---------------------------------------------------------------------------


async def test_booking_dispatches_confirmation_asynchronously(
    appointment_service: AppointmentService,
    test_dentist: Staff,
    test_patient,
    test_service: DentalService,
    monday_shift: WorkingShift,
    clinic_tz: ZoneInfo,
) -> None:
    """T-012 AC1: Booking confirmation dispatched asynchronously
    via NotificationService.

    Given a successful appointment booking, when the database transaction
    commits, then a booking confirmation is dispatched asynchronously
    via NotificationService.
    """
    # Replace notification service with fake
    fake_notifications = FakeNotificationService()
    appointment_service._notification_service = fake_notifications

    target_date = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).astimezone(
        ZoneInfo("UTC")
    )

    appointment = await appointment_service.book_appointment(
        patient_id=test_patient.id,
        dentist_id=test_dentist.id,
        service_id=test_service.id,
        start_time=target_date,
    )

    # Commit the session and run after_commit_callbacks (mimics get_db_session)
    await appointment_service._session.commit()
    callbacks = appointment_service._session.info.pop("after_response_callbacks", [])
    for callback in callbacks:
        await callback()

    # Verify the fake notification service captured the booking confirmation
    assert len(fake_notifications.dispatched_bookings) == 1
    dispatched = fake_notifications.dispatched_bookings[0]
    assert dispatched.id == appointment.id
    assert dispatched.patient_id == test_patient.id
    assert dispatched.dentist_id == test_dentist.id
    assert dispatched.service_id == test_service.id


async def test_booking_confirmation_not_dispatched_on_rollback(
    appointment_service: AppointmentService,
    test_dentist: Staff,
    test_patient,
    test_service: DentalService,
    monday_shift: WorkingShift,
    clinic_tz: ZoneInfo,
) -> None:
    """T-012: Booking confirmation NOT dispatched if transaction rolls back.

    Given a booking that fails validation after the confirmation would be
    queued, when the transaction rolls back, then no confirmation is sent.
    """
    # Replace notification service with fake
    fake_notifications = FakeNotificationService()
    appointment_service._notification_service = fake_notifications

    target_date = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).astimezone(
        ZoneInfo("UTC")
    )

    # Book successfully first
    appointment = await appointment_service.book_appointment(
        patient_id=test_patient.id,
        dentist_id=test_dentist.id,
        service_id=test_service.id,
        start_time=target_date,
    )
    # Commit and run callbacks for first booking
    await appointment_service._session.commit()
    callbacks = appointment_service._session.info.pop("after_response_callbacks", [])
    for callback in callbacks:
        await callback()

    # Now try to book an overlapping appointment (should fail and rollback)
    from app.exceptions import AppointmentOverlapConflictError

    with pytest.raises(AppointmentOverlapConflictError):
        await appointment_service.book_appointment(
            patient_id=test_patient.id,
            dentist_id=test_dentist.id,
            service_id=test_service.id,
            start_time=target_date,
        )
    # The session is rolled back by the service, but the first booking's
    # confirmation was already sent. The second booking's confirmation should
    # not be sent because it rolls back.
    # We verify that only ONE booking confirmation was dispatched (for the first)
    assert len(fake_notifications.dispatched_bookings) == 1
    assert fake_notifications.dispatched_bookings[0].id == appointment.id


async def test_reschedule_dispatches_reschedule_confirmation(
    appointment_service: AppointmentService,
    test_dentist: Staff,
    test_patient,
    test_service: DentalService,
    monday_shift: WorkingShift,
    clinic_tz: ZoneInfo,
) -> None:
    """T-012 AC2: Reschedule confirmation dispatched with old and new slot times.

    Given a successful appointment reschedule, when committed, then a
    reschedule confirmation is dispatched with old and new slot times.
    """
    # First, create an appointment
    target_date = datetime(2026, 1, 5, 9, 0, 0, tzinfo=clinic_tz).astimezone(
        ZoneInfo("UTC")
    )

    appointment = await appointment_service.book_appointment(
        patient_id=test_patient.id,
        dentist_id=test_dentist.id,
        service_id=test_service.id,
        start_time=target_date,
    )
    # Commit and run callbacks for the booking
    await appointment_service._session.commit()
    callbacks = appointment_service._session.info.pop("after_response_callbacks", [])
    for callback in callbacks:
        await callback()

    # Capture the old start time
    old_start_time = appointment.start_time

    # Replace notification service with fake
    fake_notifications = FakeNotificationService()
    appointment_service._notification_service = fake_notifications

    # Reschedule to a new time
    new_start_time = datetime(2026, 1, 5, 10, 0, 0, tzinfo=clinic_tz).astimezone(
        ZoneInfo("UTC")
    )

    appointment = await appointment_service.reschedule_appointment(
        appointment_id=appointment.id,
        new_start_time=new_start_time,
        actor_id=test_dentist.id,
    )

    # Commit the session and run after_commit_callbacks
    await appointment_service._session.commit()
    callbacks = appointment_service._session.info.pop("after_response_callbacks", [])
    for callback in callbacks:
        await callback()

    # Verify the fake notification service captured the reschedule confirmation
    assert len(fake_notifications.dispatched_reschedules) == 1
    dispatched = fake_notifications.dispatched_reschedules[0]
    dispatched_appt, dispatched_old, dispatched_new = dispatched
    assert dispatched_appt.id == appointment.id
    # Verify both old and new times are present
    assert dispatched_old == old_start_time
    assert dispatched_new == new_start_time  # timezone-aware UTC
    # The appointment should have the new start_time (stored as naive UTC)
    assert appointment.start_time == new_start_time.replace(tzinfo=None)
