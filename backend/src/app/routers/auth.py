"""Authentication endpoints (Spec 01 §4 — Layer 3, Architecture §4).

Thin handlers that receive dependencies, delegate to ``AuthService`` and the
repository, and return Pydantic response models.  No business logic lives
here — the handler is the *last* stop before the service layer.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.auth import CurrentUserDep
from app.api.deps import AuthServiceDep, DbSessionDep
from app.db.repository import get_staff_by_email
from app.schemas import StaffRead, TokenRequest, TokenResponse
from app.services.auth_service import (
    InactiveAccountError,
    InvalidCredentialsError,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def login(
    request: TokenRequest,
    session: DbSessionDep,
    auth_service: AuthServiceDep,
) -> TokenResponse:
    """Authenticate a staff member and return a signed JWT (PRD R-1)."""
    staff = await get_staff_by_email(session, request.username)
    if staff is None:
        raise InvalidCredentialsError()

    if not await auth_service.verify_password(request.password, staff.hashed_password):
        raise InvalidCredentialsError()

    if not staff.is_active:
        raise InactiveAccountError()

    token = auth_service.create_token(str(staff.id), staff.role)
    return TokenResponse.model_validate(
        {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 1800,
            "role": staff.role,
        }
    )


@router.get("/me", response_model=StaffRead)
async def read_current_user(current_user: CurrentUserDep) -> StaffRead:
    """Return the authenticated staff member's profile (PRD R-1)."""
    return StaffRead.model_validate(
        {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at,
        }
    )
