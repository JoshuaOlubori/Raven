"""Service catalog domain service (Spec 03 §3 — Layer 2).

Encapsulates business rules for dental service (procedure) management:
* name uniqueness (duplicate-name conflict, Spec 03 §6)
* existence validation (service-not-found, Spec 03 §7)
* active-status filtering for booking queries (Spec 03 §4)

The service is stateless with respect to application state (NFR-5): it holds
only a reference to the request-scoped ``AsyncSession``.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import (
    create_service,
    get_service_by_id,
    get_service_by_name,
    list_services,
    update_service,
)
from app.exceptions import ServiceNameExistsError, ServiceNotFoundError
from app.models.service import DentalService


class ServiceCatalog:
    """Domain service for dental service catalog operations (Spec 03 §3)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        name: str,
        description: str | None,
        duration_minutes: int,
    ) -> DentalService:
        """Create a new dental service, enforcing name uniqueness (Spec 03 §6).

        Raises ``ServiceNameExistsError`` (→ 409) if ``name`` is already taken.
        """
        existing = await get_service_by_name(self._session, name)
        if existing is not None:
            raise ServiceNameExistsError()
        return await create_service(
            self._session,
            name=name,
            description=description,
            duration_minutes=duration_minutes,
        )

    async def get(self, service_id: UUID) -> DentalService:
        """Retrieve a service by ID (Spec 03 §7).

        Raises ``ServiceNotFoundError`` if the ID does not match a service.
        """
        service = await get_service_by_id(self._session, service_id)
        if service is None:
            raise ServiceNotFoundError()
        return service

    async def list(self, active_only: bool = True) -> list[DentalService]:
        """List services, optionally filtering to active-only (Spec 03 §4)."""
        return await list_services(self._session, active_only=active_only)

    async def update(self, service_id: UUID, **kwargs: object) -> DentalService:
        """Update a service by ID, enforcing existence and name uniqueness.

        Raises ``ServiceNotFoundError`` (→ 404) if the service does not exist.
        Raises ``ServiceNameExistsError`` (→ 409) if the new name is taken.
        """
        service = await self.get(service_id)
        if "name" in kwargs:
            new_name = kwargs["name"]
            if isinstance(new_name, str) and new_name != service.name:
                existing = await get_service_by_name(self._session, new_name)
                if existing is not None:
                    raise ServiceNameExistsError()
        return await update_service(self._session, service, **kwargs)
