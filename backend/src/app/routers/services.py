"""Dental service catalog management endpoints (Spec 03 §4 — Layer 3, PRD R-6).

Thin handlers that receive dependencies, delegate to ``ServiceCatalog``,
and return Pydantic response models.  No business logic lives here — the
handler is the *last* stop before the service layer.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.auth import get_current_user, require_roles
from app.api.deps import ServiceCatalogDep
from app.models.service import DentalService
from app.schemas import ServiceCreate, ServiceRead, ServiceUpdate

router = APIRouter(prefix="/api/v1/services", tags=["services"])


def _service_read(service: DentalService) -> ServiceRead:
    """Project a ``DentalService`` ORM object to ``ServiceRead``."""
    return ServiceRead.model_validate(
        {
            "id": service.id,
            "name": service.name,
            "description": service.description,
            "duration_minutes": service.duration_minutes,
            "is_active": service.is_active,
            "created_at": service.created_at,
        }
    )


@router.post(
    "/",
    response_model=ServiceRead,
    status_code=201,
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def create_service_endpoint(
    request: ServiceCreate,
    catalog: ServiceCatalogDep,
) -> ServiceRead:
    """Create a new dental service (Admin only) (PRD R-6, Spec 03 §4)."""
    service = await catalog.create(
        name=request.name,
        description=request.description,
        duration_minutes=request.duration_minutes,
    )
    return _service_read(service)


@router.get(
    "/",
    response_model=list[ServiceRead],
    dependencies=[Depends(get_current_user)],
)
async def list_services_endpoint(
    catalog: ServiceCatalogDep,
    active_only: Annotated[bool, Query()] = True,
) -> list[ServiceRead]:
    """List dental services, optionally filtered to active-only (Spec 03 §4).

    Any authenticated staff member can view the catalog for booking/consultation.
    """
    services = await catalog.list(active_only=active_only)
    return [_service_read(s) for s in services]


@router.get(
    "/{service_id}",
    response_model=ServiceRead,
    dependencies=[Depends(get_current_user)],
)
async def get_service_endpoint(
    service_id: UUID,
    catalog: ServiceCatalogDep,
) -> ServiceRead:
    """Get a dental service by ID (Spec 03 §4)."""
    service = await catalog.get(service_id)
    return _service_read(service)


@router.patch(
    "/{service_id}",
    response_model=ServiceRead,
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def update_service_endpoint(
    service_id: UUID,
    request: ServiceUpdate,
    catalog: ServiceCatalogDep,
) -> ServiceRead:
    """Update a dental service (Admin only) (Spec 03 §4)."""
    update_data = request.model_dump(exclude_unset=True)
    service = await catalog.update(service_id, **update_data)
    return _service_read(service)
