"""Appointment management endpoints (Spec 05 §4 — Layer 3, PRD R-10).

Thin handlers that receive dependencies, delegate to ``AppointmentService``,
and return Pydantic response models.  No business logic lives here — the
handler is the *last* stop before the service layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.auth import CurrentUserDep, get_current_user, require_roles
from app.api.deps import AppointmentServiceDep, ReminderDispatcherDep
from app.models.appointment import Appointment
from app.schemas import (
    AppointmentCancel,
    AppointmentCreate,
    AppointmentDetailRead,
    AppointmentReschedule,
    AppointmentStatusUpdate,
    AuditLogRead,
    ReminderDispatchResult,
)

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _appointment_detail_read(appointment: Appointment) -> AppointmentDetailRead:
    """Project an ``Appointment`` ORM object to ``AppointmentDetailRead``."""
    return AppointmentDetailRead.model_validate(appointment)


# ---------------------------------------------------------------------------
# Booking (Admin, Receptionist)
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=AppointmentDetailRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("ADMIN", "RECEPTIONIST"))],
)
async def create_appointment_endpoint(
    request: AppointmentCreate,
    service: AppointmentServiceDep,
) -> AppointmentDetailRead:
    """Book a new appointment (Admin, Receptionist) (R-10, Spec 05 §4).

    Request body:
    - patientId: UUID of the patient
    - dentistId: UUID of the dentist
    - serviceId: UUID of the dental service
    - startTime: Appointment start time in UTC (ISO 8601)

    Returns 201 with the created appointment including
    patient, dentist, and service details.
    """
    appointment = await service.book_appointment(
        patient_id=request.patient_id,
        dentist_id=request.dentist_id,
        service_id=request.service_id,
        start_time=request.start_time,
    )
    # Fetch full detail with eager-loaded relations
    detail = await service.get_appointment_detail(appointment.id)
    return _appointment_detail_read(detail)


# ---------------------------------------------------------------------------
# Read operations (All staff)
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[AppointmentDetailRead],
    dependencies=[Depends(get_current_user)],
)
async def list_appointments_endpoint(
    service: AppointmentServiceDep,
    dentist_id: Annotated[UUID | None, Query(alias="dentistId")] = None,
    patient_id: Annotated[UUID | None, Query(alias="patientId")] = None,
    status: Annotated[str | None, Query()] = None,
    start_date: Annotated[datetime | None, Query(alias="startDate")] = None,
    end_date: Annotated[datetime | None, Query(alias="endDate")] = None,
) -> list[AppointmentDetailRead]:
    """List appointments with optional filters (All staff) (R-10, Spec 05 §4).

    Query parameters:
    - dentistId: Filter by dentist
    - patientId: Filter by patient
    - status: Filter by appointment status
    - startDate: Filter by start time >= (ISO 8601)
    - endDate: Filter by end time <= (ISO 8601)

    Returns list of appointments with eager-loaded patient, dentist, and service.
    """
    appointments = await service.list_appointments(
        dentist_id=dentist_id,
        patient_id=patient_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )
    return [_appointment_detail_read(a) for a in appointments]


@router.get(
    "/{appointment_id}",
    response_model=AppointmentDetailRead,
    dependencies=[Depends(get_current_user)],
)
async def get_appointment_endpoint(
    appointment_id: UUID,
    service: AppointmentServiceDep,
) -> AppointmentDetailRead:
    """Get appointment detail by ID (All staff) (R-10, Spec 05 §4).

    Returns appointment with eager-loaded patient, dentist, and service.
    """
    appointment = await service.get_appointment_detail(appointment_id)
    return _appointment_detail_read(appointment)


# ---------------------------------------------------------------------------
# Reschedule (Admin, Receptionist)
# ---------------------------------------------------------------------------


@router.post(
    "/{appointment_id}/reschedule",
    response_model=AppointmentDetailRead,
    dependencies=[Depends(require_roles("ADMIN", "RECEPTIONIST"))],
)
async def reschedule_appointment_endpoint(
    appointment_id: UUID,
    request: AppointmentReschedule,
    service: AppointmentServiceDep,
    current_user: CurrentUserDep,
) -> AppointmentDetailRead:
    """Reschedule an appointment to a new slot (Admin, Receptionist) (R-11, Spec 05 §4).

    Path parameters:
    - appointment_id: UUID of the appointment to reschedule

    Request body:
    - startTime: New appointment start time in UTC (ISO 8601)
    - dentistId: Optional new dentist UUID

    Returns 200 with the updated appointment including
    patient, dentist, and service details.
    """
    appointment = await service.reschedule_appointment(
        appointment_id=appointment_id,
        new_start_time=request.start_time,
        new_dentist_id=request.dentist_id,
        actor_id=current_user.id,
    )
    # Fetch full detail with eager-loaded relations
    detail = await service.get_appointment_detail(appointment.id)
    return _appointment_detail_read(detail)


# ---------------------------------------------------------------------------
# Cancel (Admin, Receptionist)
# ---------------------------------------------------------------------------


@router.post(
    "/{appointment_id}/cancel",
    response_model=AppointmentDetailRead,
    dependencies=[Depends(require_roles("ADMIN", "RECEPTIONIST"))],
)
async def cancel_appointment_endpoint(
    appointment_id: UUID,
    request: AppointmentCancel,
    service: AppointmentServiceDep,
    current_user: CurrentUserDep,
) -> AppointmentDetailRead:
    """Cancel an appointment with a mandatory reason (Admin, Receptionist)
    (R-13, Spec 05 §4).

    Path parameters:
    - appointment_id: UUID of the appointment to cancel

    Request body:
    - cancellationReason: Mandatory non-empty reason for cancellation

    Returns 200 with the updated appointment including
    patient, dentist, and service details.
    """
    appointment = await service.cancel_appointment(
        appointment_id=appointment_id,
        cancellation_reason=request.cancellation_reason,
        actor_id=current_user.id,
    )
    # Fetch full detail with eager-loaded relations
    detail = await service.get_appointment_detail(appointment.id)
    return _appointment_detail_read(detail)


# ---------------------------------------------------------------------------
# Status Transition (Admin, Receptionist, Dentist)
# ---------------------------------------------------------------------------


@router.post(
    "/{appointment_id}/status",
    response_model=AppointmentDetailRead,
    dependencies=[Depends(require_roles("ADMIN", "RECEPTIONIST", "DENTIST"))],
)
async def update_appointment_status_endpoint(
    appointment_id: UUID,
    request: AppointmentStatusUpdate,
    service: AppointmentServiceDep,
    current_user: CurrentUserDep,
) -> AppointmentDetailRead:
    """Transition appointment status per FSM (Admin, Receptionist, Dentist)
    (R-12, Spec 05 §4).

    Path parameters:
    - appointment_id: UUID of the appointment to transition

    Request body:
    - toStatus: Target status (CONFIRMED, CHECKED_IN, IN_PROGRESS, COMPLETED, NO_SHOW)
    - note: Optional note for the transition

    Returns 200 with the updated appointment including
    patient, dentist, and service details.

    Errors:
    - 400 INVALID_STATUS_TRANSITION: Terminal state or invalid FSM transition
    - 403: Dentist-only transitions (IN_PROGRESS, COMPLETED) attempted by non-dentist
    """
    appointment = await service.transition_status(
        appointment_id=appointment_id,
        to_status=request.to_status,
        note=request.note,
        actor_id=current_user.id,
        actor_role=current_user.role,
    )
    # Fetch full detail with eager-loaded relations
    detail = await service.get_appointment_detail(appointment.id)
    return _appointment_detail_read(detail)


# ---------------------------------------------------------------------------
# Audit Logs (All staff)
# ---------------------------------------------------------------------------


@router.get(
    "/{appointment_id}/audit-logs",
    response_model=list[AuditLogRead],
    dependencies=[Depends(get_current_user)],
)
async def get_audit_logs_endpoint(
    appointment_id: UUID,
    service: AppointmentServiceDep,
) -> list[AuditLogRead]:
    """Get chronological audit log history for an appointment (All staff)
    (R-14, Spec 05 §4).

    Path parameters:
    - appointment_id: UUID of the appointment

    Returns list of audit log entries with actor details, ordered by created_at.
    """
    audit_logs = await service.get_audit_logs(appointment_id)
    return [AuditLogRead.model_validate(log) for log in audit_logs]


# ---------------------------------------------------------------------------
# Reminder Dispatch (Admin only) — Spec 06 §4, T-012
# ---------------------------------------------------------------------------


@router.post(
    "/reminders/dispatch",
    response_model=ReminderDispatchResult,
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def dispatch_reminders_endpoint(
    dispatcher: ReminderDispatcherDep,
) -> ReminderDispatchResult:
    """Dispatch 24h pre-visit reminders for appointments in 23-25h window (R-17).

    Protected maintenance endpoint for external cron runners in multi-worker
    environments. Returns count of dispatched reminders and the time window checked.

    Idempotent: uses atomic claim (UPDATE ... WHERE reminder_sent_at IS NULL RETURNING)
    to prevent duplicate dispatches under concurrent triggers (ADR 0002).
    """
    return await dispatcher.dispatch()
