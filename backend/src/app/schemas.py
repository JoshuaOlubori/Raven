"""Shared Pydantic schemas and constrained types (Architecture §3 / Standard §3).

Central location for reusable constrained types (``EmailStr``, ``PasswordStr``,
``NonEmptyStr``, ``StaffRole``) and the auth-module request/response models
defined in Spec 01 §2 (Layer 1 — Contracts).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

# ---------------------------------------------------------------------------
# Shared constrained types (Spec 01 §2 — Layer 1)
# ---------------------------------------------------------------------------

StaffRole = Literal["ADMIN", "RECEPTIONIST", "DENTIST"]


def _normalize_email(value: object) -> object:
    """Strip whitespace and lowercase an email string."""
    if isinstance(value, str):
        return value.strip().lower()
    return value


def _strip(value: object) -> object:
    """Strip leading/trailing whitespace from a string."""
    if isinstance(value, str):
        return value.strip()
    return value


EmailStr = Annotated[
    str, BeforeValidator(_normalize_email), Field(min_length=3, max_length=255)
]
PasswordStr = Annotated[str, Field(min_length=8, max_length=128)]
NonEmptyStr = Annotated[
    str, BeforeValidator(_strip), Field(min_length=1, max_length=100)
]

# ---------------------------------------------------------------------------
# Auth schemas (Spec 01 §2 — Layer 1)
# ---------------------------------------------------------------------------


class TokenRequest(BaseModel):
    """Login input body. Uses ``username`` (email) per OAuth2 convention."""

    username: EmailStr
    password: PasswordStr


class TokenResponse(BaseModel):
    """Access token output with camelCase aliases (Spec 01 §2)."""

    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(alias="accessToken")
    token_type: str = Field(default="bearer", alias="tokenType")
    expires_in: int = Field(alias="expiresIn")
    role: StaffRole


class StaffRead(BaseModel):
    """Public staff representation with camelCase aliases (Spec 01 §2)."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    email: EmailStr
    full_name: NonEmptyStr = Field(alias="fullName")
    role: StaffRole
    is_active: bool = Field(alias="isActive")
    created_at: datetime = Field(alias="createdAt")
