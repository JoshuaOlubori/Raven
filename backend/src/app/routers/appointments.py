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
from app.api.deps import AppointmentServiceDep
from app.models.appointment import Appointment
from app.schemas import (
    AppointmentCancel,
    AppointmentCreate,
    AppointmentDetailRead,
    AppointmentReschedule,
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
    current_user: CurrentUserDep,
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
        current_user_role=current_user.role,
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
        current_user_role=current_user.role,
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
        current_user_role=current_user.role,
    )
    # Fetch full detail with eager-loaded relations
    detail = await service.get_appointment_detail(appointment.id)
    return _appointment_detail_read(detail)
