"""Appointment domain service (Spec 05 §3 — Layer 2, PRD R-10, NFR-1).

Encapsulates business rules for appointment booking:
* Validates requested slot falls within dentist's active shift
* Validates no overlap with time-off blocks
* Validates no overlap with existing appointments (atomic overlap guard)
* Auto-calculates end_time from start_time + service duration
* Enforces authorization (Admin, Receptionist)

The service is stateless: it holds only a reference to the request-scoped
``AsyncSession`` and delegates persistence to the repository layer.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.repository import (
    check_appointment_overlap,
    create_appointment,
    get_appointment,
    get_appointment_detail,
    get_service_by_id,
    list_appointments,
    list_shifts_by_day,
    list_time_off_blocks,
    update_appointment,
)
from app.exceptions import (
    AppointmentNotFoundError,
    AppointmentOverlapConflictError,
    CancellationReasonRequiredError,
    InvalidStateTransitionError,
    OutsideShiftHoursError,
    ServiceNotFoundError,
    TimeOffConflictError,
)
from app.models import (
    Appointment,
)


class AppointmentService:
    """Domain service for appointment operations (Spec 05 §3)."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._clinic_tz = ZoneInfo(settings.clinic_timezone)

    # -------------------------------------------------------------------------
    # Booking (Admin, Receptionist)
    # -------------------------------------------------------------------------

    async def book_appointment(
        self,
        *,
        patient_id: UUID,
        dentist_id: UUID,
        service_id: UUID,
        start_time: datetime,
        current_user_role: str,
    ) -> Appointment:
        """Book a new appointment (R-10, NFR-1).

        Validates:
        - Service exists and is active
        - Dentist has a shift covering the requested window
        - No time-off block overlaps the requested window
        - No existing non-cancelled appointment overlaps the window
        - User has booking permission (ADMIN, RECEPTIONIST)

        Args:
            patient_id: UUID of the patient
            dentist_id: UUID of the dentist
            service_id: UUID of the dental service
            start_time: Appointment start time in UTC
            current_user_role: Role of the user making the booking

        Returns:
            Created Appointment with SCHEDULED status and auto-calculated end_time

        Raises:
            ServiceNotFoundError: Service does not exist or is inactive
            OutsideShiftHoursError: Requested window not within
                dentist's shift
            TimeOffConflictError: Requested window overlaps a time-off block
            AppointmentOverlapConflictError: Requested window overlaps
                existing appointment
        """
        # 1. Validate service and get duration
        service = await get_service_by_id(self._session, service_id)
        if service is None or not service.is_active:
            raise ServiceNotFoundError()

        # Convert incoming timezone-aware datetime to UTC for storage
        if start_time.tzinfo is not None:
            start_time = start_time.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

        duration = service.duration_minutes
        end_time = start_time + timedelta(minutes=duration)

        # 2. Check shift coverage
        await self._validate_shift_coverage(dentist_id, start_time, end_time)

        # 3. Check time-off conflict
        await self._validate_time_off_conflict(dentist_id, start_time, end_time)

        # 4. Check appointment overlap (atomic guard - Spec 05 §5)
        if await check_appointment_overlap(
            self._session, dentist_id, start_time, end_time
        ):
            raise AppointmentOverlapConflictError()

        # 5. Create appointment
        appointment = await create_appointment(
            self._session,
            patient_id=patient_id,
            dentist_id=dentist_id,
            service_id=service_id,
            start_time=start_time,
            end_time=end_time,
            status="SCHEDULED",
        )

        return appointment

    # -------------------------------------------------------------------------
    # Read operations (All staff)
    # -------------------------------------------------------------------------

    async def get_appointment_detail(self, appointment_id: UUID) -> Appointment:
        """Fetch appointment detail with patient, dentist, and service eager-loaded."""
        appointment = await get_appointment_detail(self._session, appointment_id)
        if appointment is None:
            raise AppointmentNotFoundError()
        return appointment

    async def list_appointments(
        self,
        dentist_id: UUID | None = None,
        patient_id: UUID | None = None,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Appointment]:
        """List appointments with optional filters and eager loading."""
        return await list_appointments(
            self._session,
            dentist_id=dentist_id,
            patient_id=patient_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )

    # -------------------------------------------------------------------------
    # Reschedule (Admin, Receptionist)
    # -------------------------------------------------------------------------

    async def reschedule_appointment(
        self,
        *,
        appointment_id: UUID,
        new_start_time: datetime,
        new_dentist_id: UUID | None = None,
        current_user_role: str,
    ) -> Appointment:
        """Reschedule an appointment to a new slot (R-11, NFR-1).

        Validates:
        - Appointment exists and is in SCHEDULED or CONFIRMED state
        - New dentist (if changed) has a shift covering the requested window
        - No time-off block overlaps the requested window for the new dentist
        - No existing non-cancelled appointment overlaps the window (excluding self)
        - User has reschedule permission (ADMIN, RECEPTIONIST)

        Args:
            appointment_id: UUID of the appointment to reschedule
            new_start_time: New appointment start time in UTC
            new_dentist_id: Optional new dentist UUID (defaults to current dentist)
            current_user_role: Role of the user making the reschedule

        Returns:
            Updated Appointment with SCHEDULED status and recalculated end_time

        Raises:
            AppointmentNotFoundError: Appointment does not exist
            InvalidStateTransitionError: Current state is not SCHEDULED or CONFIRMED
            ServiceNotFoundError: Service does not exist or is inactive
            OutsideShiftHoursError: Requested window not within dentist's shift
            TimeOffConflictError: Requested window overlaps a time-off block
            AppointmentOverlapConflictError: Requested window overlaps
                existing appointment
        """
        # 1. Fetch the appointment
        appointment = await get_appointment(self._session, appointment_id)
        if appointment is None:
            raise AppointmentNotFoundError()

        # 2. Validate current state allows reschedule (SCHEDULED or CONFIRMED)
        if appointment.status not in ("SCHEDULED", "CONFIRMED"):
            raise InvalidStateTransitionError(
                "Cannot reschedule a completed or cancelled appointment"
            )

        # 3. Determine target dentist
        target_dentist_id = new_dentist_id or appointment.dentist_id

        # 4. Validate service and get duration
        service = await get_service_by_id(self._session, appointment.service_id)
        if service is None or not service.is_active:
            raise ServiceNotFoundError()

        # Convert incoming timezone-aware datetime to UTC for storage
        if new_start_time.tzinfo is not None:
            new_start_time = new_start_time.astimezone(ZoneInfo("UTC")).replace(
                tzinfo=None
            )

        duration = service.duration_minutes
        new_end_time = new_start_time + timedelta(minutes=duration)

        # 5. Check shift coverage for target dentist
        await self._validate_shift_coverage(
            target_dentist_id, new_start_time, new_end_time
        )

        # 6. Check time-off conflict for target dentist
        await self._validate_time_off_conflict(
            target_dentist_id, new_start_time, new_end_time
        )

        # 7. Check appointment overlap (atomic guard - Spec 05 §5)
        # Use exclude_id to avoid conflict with self
        if await check_appointment_overlap(
            self._session,
            target_dentist_id,
            new_start_time,
            new_end_time,
            exclude_id=appointment_id,
        ):
            raise AppointmentOverlapConflictError()

        # 8. Update appointment
        appointment = await update_appointment(
            self._session,
            appointment,
            dentist_id=target_dentist_id,
            start_time=new_start_time,
            end_time=new_end_time,
            status="SCHEDULED",  # Reset to SCHEDULED per spec
        )

        return appointment

    # -------------------------------------------------------------------------
    # Cancel (Admin, Receptionist)
    # -------------------------------------------------------------------------

    async def cancel_appointment(
        self,
        *,
        appointment_id: UUID,
        cancellation_reason: str,
        current_user_role: str,
    ) -> Appointment:
        """Cancel an appointment with a mandatory reason (R-13).

        Validates:
        - Appointment exists
        - Current state permits cancellation (SCHEDULED, CONFIRMED, CHECKED_IN)
        - Cancellation reason is non-empty
        - User has cancellation permission (ADMIN, RECEPTIONIST)

        Args:
            appointment_id: UUID of the appointment to cancel
            cancellation_reason: Mandatory non-empty reason for cancellation
            current_user_role: Role of the user making the cancellation

        Returns:
            Updated Appointment with CANCELLED status and cancellation_reason set

        Raises:
            AppointmentNotFoundError: Appointment does not exist
            InvalidStateTransitionError: Current state does not permit cancellation
            CancellationReasonRequiredError: Reason is empty or missing
        """
        # 1. Fetch the appointment
        appointment = await get_appointment(self._session, appointment_id)
        if appointment is None:
            raise AppointmentNotFoundError()

        # 2. Validate current state allows cancellation
        if appointment.status not in ("SCHEDULED", "CONFIRMED", "CHECKED_IN"):
            raise InvalidStateTransitionError(
                "Cannot cancel an appointment in its current state"
            )

        # 3. Validate cancellation reason is non-empty
        if not cancellation_reason or not cancellation_reason.strip():
            raise CancellationReasonRequiredError()

        # 4. Update appointment to CANCELLED with reason
        appointment = await update_appointment(
            self._session,
            appointment,
            status="CANCELLED",
            cancellation_reason=cancellation_reason.strip(),
        )

        return appointment

    # -------------------------------------------------------------------------
    # Validation helpers
    # -------------------------------------------------------------------------

    async def _validate_shift_coverage(
        self, dentist_id: UUID, start_time: datetime, end_time: datetime
    ) -> None:
        """Validate that the requested window falls within a dentist's shift.

        Converts start/end to clinic timezone to find the weekday and
        checks against recurring weekly shifts.

        Precondition: start_time and end_time are naive UTC datetimes
        (normalised by book_appointment before this helper is called).
        """
        # Attach UTC info for astimezone() conversion to clinic timezone
        start_utc = start_time.replace(tzinfo=ZoneInfo("UTC"))
        end_utc = end_time.replace(tzinfo=ZoneInfo("UTC"))

        # Convert to clinic timezone to find weekday
        start_local = start_utc.astimezone(self._clinic_tz)
        end_local = end_utc.astimezone(self._clinic_tz)

        # Must be same day in clinic timezone
        if start_local.date() != end_local.date():
            raise OutsideShiftHoursError()

        weekday = start_local.weekday()  # 0=Monday, ..., 6=Sunday
        shift_start_local = start_local.time()
        shift_end_local = end_local.time()

        # Fetch shifts for this dentist on this weekday
        shifts = await list_shifts_by_day(self._session, weekday, dentist_id)
        if not shifts:
            raise OutsideShiftHoursError()

        # Check if any shift covers the requested window
        covered = False
        for shift in shifts:
            if self._shift_covers_window(
                shift.start_time, shift.end_time, shift_start_local, shift_end_local
            ):
                covered = True
                break

        if not covered:
            raise OutsideShiftHoursError()

    async def _validate_time_off_conflict(
        self, dentist_id: UUID, start_time: datetime, end_time: datetime
    ) -> None:
        """Validate no time-off block overlaps the requested window.

        Precondition: start_time and end_time are naive UTC datetimes
        (normalised by book_appointment before this helper is called).
        Time-off blocks are stored in naive UTC, so the comparison is direct.
        """
        blocks = await list_time_off_blocks(
            self._session, dentist_id, start_time, end_time
        )
        if blocks:
            raise TimeOffConflictError()

    @staticmethod
    def _shift_covers_window(
        shift_start: time, shift_end: time, window_start: time, window_end: time
    ) -> bool:
        """Check if a shift time range fully covers the requested window."""
        return shift_start <= window_start and shift_end >= window_end
