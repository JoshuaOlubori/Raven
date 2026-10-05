"""Staff ORM model (Architecture §3 / Spec 01 §3).

A staff member is an internal user (Admin, Receptionist, or Dentist) with
credentials, a role, and an active/inactive status.  Passwords are never
stored in plaintext — see ``app.services.auth_service.AuthService``.
"""

from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Staff(Base, UUIDMixin, TimestampMixin):
    """Internal clinic staff account."""

    __tablename__ = "staff"

    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]
    full_name: Mapped[str]
    role: Mapped[str] = mapped_column(index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
