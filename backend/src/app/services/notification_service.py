"""Notification service protocol and default logging implementation
(Spec 06 §3 — Layer 3).

Defines the abstract port for patient-facing notifications (confirmations,
reminders) and provides a test-friendly logging adapter.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.appointment import Appointment


logger = logging.getLogger("app.notifications")


class RescheduleConfirmationData:
    """Immutable data carrier for reschedule confirmation notifications.

    Contains both old and new appointment times for patient-facing messages.
    """

    def __init__(
        self,
        appointment: Appointment,
        old_start_time: datetime,
        new_start_time: datetime,
    ) -> None:
        self.appointment = appointment
        self.old_start_time = old_start_time
        self.new_start_time = new_start_time


class NotificationService(ABC):
    """Abstract port for sending patient notifications (R-16, R-17).

    Implementations can dispatch via email, SMS, push, or any other channel.
    The default LoggingNotificationService logs to stdout for development/testing.
    """

    @abstractmethod
    async def send_booking_confirmation(self, appointment: Appointment) -> None:
        """Send a booking confirmation to the patient.

        Called after a new appointment is successfully booked.
        Must not block the calling request (fire-and-forget or background task).
        """
        ...

    @abstractmethod
    async def send_reschedule_confirmation(
        self,
        appointment: Appointment,
        old_start_time: datetime,
        new_start_time: datetime,
    ) -> None:
        """Send a rescheduling confirmation to the patient.

        Called after an appointment is successfully rescheduled.
        Must not block the calling request.

        Args:
            appointment: The rescheduled appointment.
            old_start_time: The previous start time (timezone-aware UTC).
            new_start_time: The new start time (timezone-aware UTC).
        """
        ...

    @abstractmethod
    async def send_reminder(self, appointment: Appointment) -> None:
        """Send a 24-hour pre-visit reminder to the patient.

        Called by the reminder dispatcher for appointments in the 23-25h window
        where reminder_sent_at is NULL.
        """
        ...


class LoggingNotificationService(NotificationService):
    """Default implementation that logs notification payloads to stdout / log file.

    Used for development, testing, and as a no-op fallback when no external
    notification provider is configured.
    """

    async def send_booking_confirmation(self, appointment: Appointment) -> None:
        """Log booking confirmation payload."""
        patient_name = (
            f"{appointment.patient.first_name} {appointment.patient.last_name}"
        )
        logger.info(
            "BOOKING_CONFIRMATION: appointment_id=%s patient=%s "
            "dentist=%s service=%s start=%s",
            appointment.id,
            patient_name,
            appointment.dentist.full_name,
            appointment.service.name,
            appointment.start_time.isoformat(),
        )

    async def send_reschedule_confirmation(
        self,
        appointment: Appointment,
        old_start_time: datetime,
        new_start_time: datetime,
    ) -> None:
        """Log reschedule confirmation payload with old and new times."""
        patient_name = (
            f"{appointment.patient.first_name} {appointment.patient.last_name}"
        )
        logger.info(
            "RESCHEDULE_CONFIRMATION: appointment_id=%s patient=%s "
            "dentist=%s service=%s old_start=%s new_start=%s",
            appointment.id,
            patient_name,
            appointment.dentist.full_name,
            appointment.service.name,
            old_start_time.isoformat(),
            new_start_time.isoformat(),
        )

    async def send_reminder(self, appointment: Appointment) -> None:
        """Log reminder dispatch payload."""
        patient_name = (
            f"{appointment.patient.first_name} {appointment.patient.last_name}"
        )
        logger.info(
            "REMINDER_DISPATCH: appointment_id=%s patient=%s "
            "dentist=%s service=%s start=%s",
            appointment.id,
            patient_name,
            appointment.dentist.full_name,
            appointment.service.name,
            appointment.start_time.isoformat(),
        )


# Module-level singleton for dependency injection
_notification_service: NotificationService | None = None


def get_notification_service() -> NotificationService:
    """Return the global NotificationService singleton
    (default: LoggingNotificationService).
    """
    global _notification_service
    if _notification_service is None:
        _notification_service = LoggingNotificationService()
    return _notification_service


def set_notification_service(service: NotificationService) -> None:
    """Override the global notification service (for testing)."""
    global _notification_service
    _notification_service = service
