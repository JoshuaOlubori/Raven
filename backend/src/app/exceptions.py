"""Domain exception hierarchy (Architecture §4 — Global Error Model).

All application-level errors inherit from ``DomainError`` so that a single
exception handler in ``main.py`` maps them to the standardized error body:

    {"error": "<code_string>", "message": "<str>", "correlation_id": "<str>"}
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain/application exceptions.

    Subclasses set ``error_code`` (the machine-readable error string returned
    in the ``error`` field), ``message`` (human-readable text), and
    ``status_code`` (the HTTP status).  ``main.py`` registers one handler for
    ``DomainError`` that covers all subclasses (Architecture §4).
    """

    error_code: str = "DOMAIN_ERROR"
    message: str = "Domain error"
    status_code: int = 400


class EmailAlreadyExistsError(DomainError):
    """Raised when a staff member is created with an email already in use."""

    error_code = "STAFF_EMAIL_EXISTS"
    message = "A staff member with this email already exists"
    status_code = 409


class StaffNotFoundError(DomainError):
    """Raised when a staff member lookup by ID finds no match."""

    error_code = "STAFF_NOT_FOUND"
    message = "Staff member not found"
    status_code = 404


class ForbiddenError(DomainError):
    """Raised when an authenticated user lacks the role(s) required for a resource."""

    error_code = "RBAC_FORBIDDEN"
    message = "Insufficient role"
    status_code = 403


class ServiceNotFoundError(DomainError):
    """Raised when a dental service lookup by ID finds no match (Spec 03 §7)."""

    error_code = "SERVICE_NOT_FOUND"
    message = "Service not found"
    status_code = 404


class ServiceNameExistsError(DomainError):
    """Raised when a service name is already in use (Spec 03 §7)."""

    error_code = "SERVICE_NAME_EXISTS"
    message = "A service with this name already exists"
    status_code = 409


class PatientNotFoundError(DomainError):
    """Raised when a patient lookup by ID finds no match (Spec 02 §7)."""

    error_code = "PATIENT_NOT_FOUND"
    message = "Patient not found"
    status_code = 404


# ---------------------------------------------------------------------------
# Schedule exceptions (Spec 04 §7)
# ---------------------------------------------------------------------------


class ShiftOverlapError(DomainError):
    """Raised when a new recurring shift overlaps an existing shift
    for that dentist on the same day.
    """

    error_code = "SHIFT_OVERLAP"
    message = "Shift overlaps with an existing shift"
    status_code = 409


class InvalidTimeRangeError(DomainError):
    """Raised when start_time >= end_time."""

    error_code = "INVALID_TIME_RANGE"
    message = "Start time must be before end time"
    status_code = 400


class UnauthorizedScheduleModificationError(DomainError):
    """Raised when a dentist attempts to modify another dentist's schedule."""

    error_code = "SCHEDULE_FORBIDDEN"
    message = "Not authorized to modify this schedule"
    status_code = 403


class DentistNotAvailableError(DomainError):
    """Raised when a dentist has no shifts on the requested date."""

    error_code = "DENTIST_NOT_AVAILABLE"
    message = "Dentist has no shifts on the requested date"
    status_code = 200  # Returns empty slots per spec


# ---------------------------------------------------------------------------
# Appointment exceptions (Spec 05 §7)
# ---------------------------------------------------------------------------


class AppointmentOverlapConflictError(DomainError):
    """Raised when a target booking interval overlaps an existing appointment."""

    error_code = "APPOINTMENT_OVERLAP_CONFLICT"
    message = "The requested time window overlaps an existing appointment"
    status_code = 409


class OutsideShiftHoursError(DomainError):
    """Raised when a target booking interval falls outside dentist's shift hours."""

    error_code = "OUTSIDE_SHIFT_HOURS"
    message = "The requested time is outside the dentist's working hours"
    status_code = 400


class TimeOffConflictError(DomainError):
    """Raised when a target booking interval intersects a dentist's time-off block."""

    error_code = "TIME_OFF_CONFLICT"
    message = "The requested time conflicts with the dentist's time off"
    status_code = 409


class AppointmentNotFoundError(DomainError):
    """Raised when an appointment lookup by ID finds no match."""

    error_code = "APPOINTMENT_NOT_FOUND"
    message = "Appointment not found"
    status_code = 404


class InvalidStateTransitionError(DomainError):
    """Raised when FSM does not permit transition from current status to requested."""

    error_code = "INVALID_STATUS_TRANSITION"
    message = "Invalid appointment state transition"
    status_code = 400


class CancellationReasonRequiredError(DomainError):
    """Raised when cancellation is submitted without a reason."""

    error_code = "CANCELLATION_REASON_REQUIRED"
    message = "Cancellation reason is required"
    status_code = 422
