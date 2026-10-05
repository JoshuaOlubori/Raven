"""Patient management endpoints (Spec 02 §4 — Layer 3, PRD R-3, R-4, R-5).

Thin handlers that receive dependencies, delegate to ``PatientService``,
and return Pydantic response models.  No business logic lives here — the
handler is the *last* stop before the service layer.
"""

from __future__ import annotations

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.auth import get_current_user, require_roles
from app.api.deps import PatientServiceDep
from app.models.patient import Patient
from app.schemas import PatientCreate, PatientPage, PatientRead, PatientUpdate

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


def _patient_read(patient: Patient) -> PatientRead:
    """Project a ``Patient`` ORM object to ``PatientRead``."""
    return PatientRead.model_validate(
        {
            "id": patient.id,
            "firstName": patient.first_name,
            "lastName": patient.last_name,
            "dateOfBirth": patient.date_of_birth,
            "phone": patient.phone,
            "email": patient.email,
            "emergencyContactName": patient.emergency_contact_name,
            "emergencyContactPhone": patient.emergency_contact_phone,
            "medicalAlerts": patient.medical_alerts,
            "isActive": patient.is_active,
            "createdAt": patient.created_at,
            "updatedAt": patient.updated_at,
        }
    )


@router.post(
    "/",
    response_model=PatientRead,
    status_code=201,
    dependencies=[Depends(require_roles("ADMIN", "RECEPTIONIST"))],
)
async def create_patient_endpoint(
    request: PatientCreate,
    service: PatientServiceDep,
) -> PatientRead:
    """Create a new patient profile (Admin, Receptionist) (PRD R-3, Spec 02 §4)."""
    patient = await service.create(
        first_name=request.first_name,
        last_name=request.last_name,
        date_of_birth=request.date_of_birth,
        phone=request.phone,
        email=request.email,
        emergency_contact_name=request.emergency_contact_name,
        emergency_contact_phone=request.emergency_contact_phone,
        medical_alerts=request.medical_alerts,
    )
    return _patient_read(patient)


@router.get(
    "/",
    response_model=PatientPage,
    dependencies=[Depends(get_current_user)],
)
async def list_patients_endpoint(
    service: PatientServiceDep,
    search: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PatientPage:
    """Search and paginate active patients (All staff) (PRD R-4, Spec 02 §4).

    Any authenticated clinical staff member may search patient records.
    Soft-deleted (inactive) patients are excluded by default.
    """
    patients, total = await service.list(search=search, page=page, size=size)
    pages = math.ceil(total / size) if size > 0 else 0
    return PatientPage(
        items=[_patient_read(p) for p in patients],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get(
    "/{patient_id}",
    response_model=PatientRead,
    dependencies=[Depends(get_current_user)],
)
async def get_patient_endpoint(
    patient_id: UUID,
    service: PatientServiceDep,
) -> PatientRead:
    """Get a patient by ID (All staff) (Spec 02 §4)."""
    patient = await service.get(patient_id)
    return _patient_read(patient)


@router.patch(
    "/{patient_id}",
    response_model=PatientRead,
    dependencies=[Depends(require_roles("ADMIN", "RECEPTIONIST"))],
)
async def update_patient_endpoint(
    patient_id: UUID,
    request: PatientUpdate,
    service: PatientServiceDep,
) -> PatientRead:
    """Update a patient profile (Admin, Receptionist) (PRD R-3, Spec 02 §4)."""
    update_data = request.model_dump(exclude_unset=True)
    patient = await service.update(patient_id, **update_data)
    return _patient_read(patient)


@router.delete(
    "/{patient_id}",
    status_code=204,
    dependencies=[Depends(require_roles("ADMIN", "RECEPTIONIST"))],
)
async def delete_patient_endpoint(
    patient_id: UUID,
    service: PatientServiceDep,
) -> None:
    """Soft-delete a patient (Admin, Receptionist) (PRD R-5, Spec 02 §4).

    Sets ``is_active = false``; historical appointment records are preserved.
    """
    await service.soft_delete(patient_id)
