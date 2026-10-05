"""Patient domain service (Spec 02 §3 — Layer 2, PRD R-3/R-4/R-5).

Encapsulates business rules for patient profile management:
* existence validation — raises ``PatientNotFoundError`` (→ 404) on missing IDs
* active-only filtering for search queries (soft-deleted excluded by default)
* soft deletion that flips ``is_active`` rather than SQL DELETE (R-5)

The service is stateless with respect to application state (NFR-5): it holds
only a reference to the request-scoped ``AsyncSession``.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import (
    create_patient,
    get_patient_by_id,
    list_patients,
    soft_delete_patient,
    update_patient,
)
from app.exceptions import PatientNotFoundError
from app.models.patient import Patient


class PatientService:
    """Domain service for patient profile operations (Spec 02 §3)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        first_name: str,
        last_name: str,
        date_of_birth: date,
        phone: str,
        email: str | None = None,
        emergency_contact_name: str | None = None,
        emergency_contact_phone: str | None = None,
        medical_alerts: str | None = None,
    ) -> Patient:
        """Create a new patient profile (R-3)."""
        return await create_patient(
            self._session,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            phone=phone,
            email=email,
            emergency_contact_name=emergency_contact_name,
            emergency_contact_phone=emergency_contact_phone,
            medical_alerts=medical_alerts,
        )

    async def get(self, patient_id: UUID) -> Patient:
        """Retrieve a patient by ID (R-4).

        Raises ``PatientNotFoundError`` (→ 404) if the ID does not match a patient.
        """
        patient = await get_patient_by_id(self._session, patient_id)
        if patient is None:
            raise PatientNotFoundError()
        return patient

    async def list(
        self,
        search: str | None = None,
        include_inactive: bool = False,
        page: int = 1,
        size: int = 50,
    ) -> tuple[list[Patient], int]:
        """Search and paginate patients (R-4).

        By default only active (non-soft-deleted) patients are returned.
        """
        return await list_patients(
            self._session,
            search=search,
            include_inactive=include_inactive,
            page=page,
            size=size,
        )

    async def update(self, patient_id: UUID, **kwargs: object) -> Patient:
        """Update a patient by ID (R-3).

        Raises ``PatientNotFoundError`` (→ 404) if the patient does not exist.
        """
        patient = await self.get(patient_id)
        return await update_patient(self._session, patient, **kwargs)

    async def soft_delete(self, patient_id: UUID) -> Patient:
        """Soft-delete a patient by ID (R-5).

        Raises ``PatientNotFoundError`` (→ 404) if the patient does not exist.
        """
        patient = await self.get(patient_id)
        return await soft_delete_patient(self._session, patient)
