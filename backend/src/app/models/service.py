"""Dental service (procedure) ORM model (Architecture §3 / Spec 03 §3).

A dental service is a named procedure with a standard duration in minutes
and an active/inactive flag.  Inactive services are excluded from booking
queries but preserved for historical appointment integrity (Spec 03 §6).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.appointment import Appointment


class DentalService(Base, UUIDMixin, TimestampMixin):
    """Dental procedure / service catalog entry."""

    __tablename__ = "dental_services"

    name: Mapped[str] = mapped_column(unique=True, index=True)
    description: Mapped[str | None] = mapped_column(default=None)
    duration_minutes: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True, index=True)

    # Appointment relationship (Spec 05 §3)
    appointments: Mapped[list[Appointment]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )
