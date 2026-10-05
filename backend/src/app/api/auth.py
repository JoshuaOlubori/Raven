"""Authentication dependency layer (Spec 01 §4 — Layer 3, Architecture §4).

Provides ``CurrentUser`` and the ``get_current_user`` dependency that extracts
a Bearer JWT from the ``Authorization`` header, validates it, looks up the
staff member, and enforces ``is_active``.

RBAC route guards (``require_roles``) belong in T-003.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, cast
from uuid import UUID

import jwt as pyjwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import AuthServiceDep, DbSessionDep
from app.db.repository import get_staff_by_id
from app.schemas import StaffRole

security = HTTPBearer()


@dataclass(frozen=True)
class CurrentUser:
    """Authenticated staff principal extracted from the JWT and DB lookup."""

    id: UUID
    email: str
    full_name: str
    role: StaffRole
    is_active: bool
    created_at: datetime


async def get_current_user(
    session: DbSessionDep,
    auth_service: AuthServiceDep,
    credentials: HTTPAuthorizationCredentials = Depends(security),  # noqa: B008
) -> CurrentUser:
    """Decode the Bearer token, look up the staff, and return a ``CurrentUser``.

    Raises ``401`` if the token is missing, malformed, expired, or references
    a non-existent / inactive staff member.
    """
    try:
        payload = auth_service.decode_token(credentials.credentials)
    except pyjwt.PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        ) from None

    staff = await get_staff_by_id(session, UUID(payload.staff_id))
    if staff is None or not staff.is_active:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return CurrentUser(
        id=staff.id,
        email=staff.email,
        full_name=staff.full_name,
        role=cast(StaffRole, staff.role),
        is_active=staff.is_active,
        created_at=staff.created_at,
    )


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
