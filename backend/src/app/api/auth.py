"""Authentication and RBAC dependency layer (Spec 01 §4 — Layer 3).

Provides ``CurrentUser`` and the ``get_current_user`` dependency that extracts
a Bearer JWT from the ``Authorization`` header, validates it, looks up the
staff member, and enforces ``is_active``.

Also provides ``require_roles`` — a closure-based dependency factory that
enforces role-based access control (RBAC) on protected endpoints (T-003).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, cast
from uuid import UUID

import jwt as pyjwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import AuthServiceDep, DbSessionDep
from app.config import get_settings
from app.db.repository import get_staff_by_id
from app.db.session import SessionLocal
from app.exceptions import ForbiddenError
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


async def get_current_user_for_stream(
    credentials: HTTPAuthorizationCredentials = Depends(security),  # noqa: B008
) -> CurrentUser:
    """Authenticate SSE clients with a short-lived session closed before streaming.

    This owns a short-lived session instead of depending on the request-scoped
    DB dependency, whose cleanup would otherwise wait for the infinite stream.
    """
    auth_service_settings = get_settings()
    async with SessionLocal() as session:
        auth_service = AuthService(session=session, settings=auth_service_settings)
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


CurrentUserStreamDep = Annotated[
    CurrentUser, Depends(get_current_user_for_stream, scope="function")
]


# ---------------------------------------------------------------------------
# RBAC route guards (Spec 01 §4 — Layer 3, T-003)
# ---------------------------------------------------------------------------


def require_roles(*roles: str) -> Callable[[CurrentUser], Awaitable[CurrentUser]]:
    """Closure-based dependency factory that enforces RBAC (Spec 01 §4).

    Returns an async dependency that resolves the authenticated
    ``CurrentUser`` and raises ``ForbiddenError`` (→ 403 standardized body)
    when the user's role is not among the permitted ``roles``.

    Typical usage::

        @router.post("/", dependencies=[Depends(require_roles("ADMIN"))])
        async def create_staff(...): ...
    """

    async def role_guard(current_user: CurrentUserDep) -> CurrentUser:
        if current_user.role not in roles:
            raise ForbiddenError()
        return current_user

    return role_guard
