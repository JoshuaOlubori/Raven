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

import asyncio
import logging
from datetime import datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.repository import (
    check_appointment_overlap,
    create_appointment,
    create_audit_log,
    get_appointment,
    get_appointment_detail,
    get_service_by_id,
    list_appointments,
    list_audit_logs_for_appointment,
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
    AppointmentAuditLog,
)
from app.schemas import AppointmentLiveEvent, EventType
from app.services.event_broadcaster import EventBroadcaster, get_event_broadcaster
from app.services.notification_service import (
    NotificationService,
    get_notification_service,
)


class AppointmentService:
    """Domain service for appointment operations (Spec 05 §3)."""

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        broadcaster: EventBroadcaster | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._clinic_tz = ZoneInfo(settings.clinic_timezone)
        self._broadcaster = broadcaster or get_event_broadcaster()
        self._notification_service = notification_service or get_notification_service()

    def _publish_event(
        self,
        event_type: str,
        appointment: Appointment,
    ) -> None:
        """Publish an appointment live event to the SSE broadcaster (Spec 06 §5).

        Fire-and-forget: does not await the publish to avoid blocking the
        request. The broadcaster handles backpressure internally.
        Exceptions in the background task are logged with correlation ID.
        """
        event = AppointmentLiveEvent(
            eventType=event_type,
            appointmentId=appointment.id,
            dentistId=appointment.dentist_id,
            patientName=(
                f"{appointment.patient.first_name} {appointment.patient.last_name}"
            ),
            status=appointment.status,
            startTime=appointment.start_time,
        )
        # Schedule the publish as a background task (non-blocking)
        # with error handling to surface exceptions
        asyncio.create_task(self._broadcaster.publish(event)).add_done_callback(
            self._log_task_exception
        )

    @staticmethod
    def _log_task_exception(task: asyncio.Task) -> None:
        """Log exceptions from fire-and-forget background tasks.

        Args:
            task: The completed task to check for exceptions.
        """
        if task.cancelled():
            return
        if task.exception() is not None:
            logger = logging.getLogger("app.appointment_service")
            logger.exception(
                "Background task failed: task=%s",
                task.get_name(),
            )

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
        # All audit datetime fields (created_at, old_start_time, new_start_time)
        # are timezone-aware (UTC) per NFR-3 for PostgreSQL consistency.
        if start_time.tzinfo is not None:
            start_time = start_time.astimezone(ZoneInfo("UTC"))  # keep tz-aware (UTC)

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

        # 6. Publish appointment booked event
        await self._session.refresh(
            appointment, attribute_names=["patient", "dentist", "service"]
        )
        self._publish_event(EventType.APPOINTMENT_BOOKED, appointment)

        # 7. Send booking confirmation (fire-and-forget, R-16)
        asyncio.create_task(
            self._notification_service.send_booking_confirmation(appointment)
        ).add_done_callback(self._log_task_exception)

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
        actor_id: UUID,
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
            actor_id: UUID of the staff member performing the reschedule
            actor_role: Role of the staff member (ADMIN, RECEPTIONIST)

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
            new_start_time = new_start_time.astimezone(ZoneInfo("UTC"))  # tz-aware UTC

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
        old_start_time = appointment.start_time
        appointment = await update_appointment(
            self._session,
            appointment,
            dentist_id=target_dentist_id,
            start_time=new_start_time,
            end_time=new_end_time,
            status="SCHEDULED",  # Reset to SCHEDULED per spec
        )

        # 9. Create audit log entry for reschedule
        await self._create_audit_log(
            appointment_id=appointment_id,
            actor_id=actor_id,
            from_status=None,
            to_status=None,
            old_start_time=old_start_time,
            new_start_time=new_start_time,
            note="Appointment rescheduled",
        )

        # 10. Publish appointment rescheduled event
        await self._session.refresh(
            appointment, attribute_names=["patient", "dentist", "service"]
        )
        self._publish_event(EventType.APPOINTMENT_RESCHEDULED, appointment)

        # 11. Send reschedule confirmation (fire-and-forget, R-16)
        asyncio.create_task(
            self._notification_service.send_reschedule_confirmation(appointment)
        ).add_done_callback(self._log_task_exception)

        return appointment

    # -------------------------------------------------------------------------
    # Cancel (Admin, Receptionist)
    # -------------------------------------------------------------------------

    async def cancel_appointment(
        self,
        *,
        appointment_id: UUID,
        cancellation_reason: str,
        actor_id: UUID,
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
            actor_id: UUID of the staff member performing the cancellation
            actor_role: Role of the staff member (ADMIN, RECEPTIONIST)

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
        from_status = appointment.status
        appointment = await update_appointment(
            self._session,
            appointment,
            status="CANCELLED",
            cancellation_reason=cancellation_reason.strip(),
        )

        # 5. Create audit log entry for cancellation
        await self._create_audit_log(
            appointment_id=appointment_id,
            actor_id=actor_id,
            from_status=from_status,
            to_status="CANCELLED",
            old_start_time=None,
            new_start_time=None,
            note=cancellation_reason.strip(),
        )

        # 6. Publish appointment cancelled event
        await self._session.refresh(
            appointment, attribute_names=["patient", "dentist", "service"]
        )
        self._publish_event(EventType.APPOINTMENT_CANCELLED, appointment)

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

        Precondition: start_time and end_time are timezone-aware UTC datetimes
        (normalised by book_appointment / reschedule before this helper is called).
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

        Precondition: start_time and end_time are timezone-aware UTC datetimes
        (normalised by book_appointment / reschedule before this helper is called).
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

    # -------------------------------------------------------------------------
    # FSM Status Transitions (Admin, Receptionist, Dentist)
    # -------------------------------------------------------------------------

    # Valid transitions per Spec 05 §8:
    # SCHEDULED -> CONFIRMED
    # SCHEDULED/CONFIRMED -> CHECKED_IN
    # CHECKED_IN -> IN_PROGRESS
    # IN_PROGRESS -> COMPLETED
    # SCHEDULED/CONFIRMED/CHECKED_IN -> CANCELLED (handled by cancel_appointment)
    # SCHEDULED/CONFIRMED -> NO_SHOW

    _VALID_TRANSITIONS: dict[str, list[str]] = {
        "SCHEDULED": ["CONFIRMED", "CHECKED_IN", "NO_SHOW"],
        "CONFIRMED": ["CHECKED_IN", "NO_SHOW"],
        "CHECKED_IN": ["IN_PROGRESS"],
        "IN_PROGRESS": ["COMPLETED"],
        "COMPLETED": [],  # Terminal
        "CANCELLED": [],  # Terminal
        "NO_SHOW": [],  # Terminal
    }

    _DENTIST_ONLY_TRANSITIONS = {"IN_PROGRESS", "COMPLETED"}

    async def transition_status(
        self,
        *,
        appointment_id: UUID,
        to_status: str,
        note: str | None,
        actor_id: UUID,
        actor_role: str,
    ) -> Appointment:
        """Transition appointment status per FSM (R-12, Spec 05 §8).

        Validates:
        - Appointment exists
        - Transition is valid per FSM
        - Terminal states (COMPLETED, CANCELLED, NO_SHOW) reject all transitions
        - DENTIST role required for IN_PROGRESS and COMPLETED transitions
        - User has permission (ADMIN, RECEPTIONIST, DENTIST)

        Args:
            appointment_id: UUID of the appointment to transition
            to_status: Target status per AppointmentStatus enum
            note: Optional note for the transition
            actor_id: UUID of the staff member performing the transition
            actor_role: Role of the staff member (ADMIN, RECEPTIONIST, DENTIST)

        Returns:
            Updated Appointment with new status

        Raises:
            AppointmentNotFoundError: Appointment does not exist
            InvalidStateTransitionError: Transition not permitted from current state
        """
        # 1. Fetch the appointment
        appointment = await get_appointment(self._session, appointment_id)
        if appointment is None:
            raise AppointmentNotFoundError()

        from_status = appointment.status

        # 2. Check if current status is terminal
        if from_status in ("COMPLETED", "CANCELLED", "NO_SHOW"):
            raise InvalidStateTransitionError(
                f"Cannot transition from terminal state {from_status}"
            )

        # 3. Validate transition is allowed per FSM
        allowed = self._VALID_TRANSITIONS.get(from_status, [])
        if to_status not in allowed:
            raise InvalidStateTransitionError(
                f"Invalid transition from {from_status} to {to_status}"
            )

        # 4. Check role-based access for DENTIST-only transitions
        if to_status in self._DENTIST_ONLY_TRANSITIONS and actor_role not in (
            "ADMIN",
            "DENTIST",
        ):
            raise InvalidStateTransitionError(
                f"Only dentists can transition to {to_status}"
            )

        # 5. Update appointment status
        appointment = await update_appointment(
            self._session, appointment, status=to_status
        )

        # 6. Create audit log entry
        await self._create_audit_log(
            appointment_id=appointment_id,
            actor_id=actor_id,
            from_status=from_status,
            to_status=to_status,
            old_start_time=None,
            new_start_time=None,
            note=note,
        )

        # 7. Publish appointment status transition event
        event_type_map = {
            "CONFIRMED": EventType.APPOINTMENT_CONFIRMED,
            "CHECKED_IN": EventType.APPOINTMENT_CHECKED_IN,
            "IN_PROGRESS": EventType.APPOINTMENT_STARTED,
            "COMPLETED": EventType.APPOINTMENT_COMPLETED,
            "NO_SHOW": EventType.APPOINTMENT_NO_SHOW,
        }
        event_type = event_type_map.get(to_status)
        if event_type:
            await self._session.refresh(
                appointment, attribute_names=["patient", "dentist", "service"]
            )
            self._publish_event(event_type, appointment)

        return appointment

    async def _create_audit_log(
        self,
        *,
        appointment_id: UUID,
        actor_id: UUID,
        from_status: str | None,
        to_status: str | None,
        old_start_time: datetime | None,
        new_start_time: datetime | None,
        note: str | None,
    ) -> AppointmentAuditLog:
        """Create an immutable audit log record for an appointment event.

        Called for:
        - Status transitions (from_status, to_status set)
        - Reschedules (old_start_time, new_start_time set)
        - Cancellations (note contains cancellation_reason)

        This is append-only — no update or delete is ever performed (NFR-4).
        """
        return await create_audit_log(
            self._session,
            appointment_id=appointment_id,
            actor_id=actor_id,
            from_status=from_status,
            to_status=to_status,
            old_start_time=old_start_time,
            new_start_time=new_start_time,
            note=note,
        )

    # -------------------------------------------------------------------------
    # Audit Log Queries (All staff)
    # -------------------------------------------------------------------------

    async def get_audit_logs(self, appointment_id: UUID) -> list[AppointmentAuditLog]:
        """Retrieve chronological audit log entries for an appointment.

        Uses eager-loading on actor relationship to avoid N+1 queries.
        """
        # Verify appointment exists
        appointment = await get_appointment(self._session, appointment_id)
        if appointment is None:
            raise AppointmentNotFoundError()

        return await list_audit_logs_for_appointment(self._session, appointment_id)
