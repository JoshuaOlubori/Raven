"""Staff management endpoints (Spec 01 §4 — Layer 3, PRD R-2).

Thin handlers that receive dependencies, delegate to repository functions and
``AuthService`` for password hashing, and return Pydantic response models.
No business logic lives here.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.auth import require_roles
from app.api.deps import AuthServiceDep, DbSessionDep
from app.db.repository import (
    create_staff,
    get_staff_by_email,
    get_staff_by_id,
    list_staff,
    update_staff,
)
from app.exceptions import EmailAlreadyExistsError, StaffNotFoundError
from app.models.staff import Staff
from app.schemas import StaffCreate, StaffRead, StaffRole, StaffUpdate

router = APIRouter(prefix="/api/v1/staff", tags=["staff"])


@router.post(
    "/",
    response_model=StaffRead,
    status_code=201,
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def create_staff_endpoint(
    request: StaffCreate,
    session: DbSessionDep,
    auth_service: AuthServiceDep,
) -> StaffRead:
    """Create a new staff account (Admin only) (PRD R-2)."""
    existing = await get_staff_by_email(session, request.email)
    if existing is not None:
        raise EmailAlreadyExistsError()

    hashed = await auth_service.hash_password(request.password)
    staff = await create_staff(
        session,
        email=request.email,
        hashed_password=hashed,
        full_name=request.full_name,
        role=request.role,
    )
    return _staff_read(staff)


def _staff_read(staff: Staff) -> StaffRead:
    """Project a ``Staff`` ORM object to ``StaffRead`` (excludes hashed_password)."""
    return StaffRead.model_validate(
        {
            "id": staff.id,
            "email": staff.email,
            "full_name": staff.full_name,
            "role": staff.role,
            "is_active": staff.is_active,
            "created_at": staff.created_at,
        }
    )


@router.get(
    "/",
    response_model=list[StaffRead],
    dependencies=[Depends(require_roles("ADMIN", "RECEPTIONIST"))],
)
async def list_staff_endpoint(
    session: DbSessionDep,
    role: Annotated[StaffRole | None, Query()] = None,
) -> list[StaffRead]:
    """List staff, optionally filtered by role (Admin, Receptionist) (Spec 01 §4)."""
    staff_list = await list_staff(session, role=role, active_only=True)
    return [_staff_read(s) for s in staff_list]


@router.get(
    "/{staff_id}",
    response_model=StaffRead,
    dependencies=[Depends(require_roles("ADMIN", "RECEPTIONIST"))],
)
async def get_staff_endpoint(
    staff_id: UUID,
    session: DbSessionDep,
) -> StaffRead:
    """Get a staff member by ID (Admin, Receptionist) (Spec 01 §4)."""
    staff = await get_staff_by_id(session, staff_id)
    if staff is None:
        raise StaffNotFoundError()
    return _staff_read(staff)


@router.patch(
    "/{staff_id}",
    response_model=StaffRead,
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def update_staff_endpoint(
    staff_id: UUID,
    request: StaffUpdate,
    session: DbSessionDep,
) -> StaffRead:
    """Update a staff member (Admin only) (Spec 01 §4)."""
    staff = await get_staff_by_id(session, staff_id)
    if staff is None:
        raise StaffNotFoundError()
    update_data = request.model_dump(exclude_unset=True)
    updated = await update_staff(session, staff, **update_data)
    return _staff_read(updated)
