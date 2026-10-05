"""Patient ORM model (Architecture §3 / Spec 02 §3 — Layer 2).

A patient is an individual receiving dental care, identified by demographics
and medical alert flags.  Patients have no login accounts in v1 (Glossary).
Soft deletion is performed via the ``is_active`` flag rather than SQL DELETE
so that historical appointment data retains referential integrity (R-5).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Patient(Base, UUIDMixin, TimestampMixin):
    """Patient profile with demographics, contact and medical-alert fields."""

    __tablename__ = "patients"
    __table_args__ = (
        Index("ix_patients_last_first", "last_name", "first_name"),
        Index("ix_patients_phone", "phone"),
        Index("ix_patients_is_active", "is_active"),
    )

    first_name: Mapped[str] = mapped_column(String(length=100))
    last_name: Mapped[str] = mapped_column(String(length=100))
    date_of_birth: Mapped[date] = mapped_column(Date)
    phone: Mapped[str] = mapped_column()
    email: Mapped[str | None] = mapped_column(default=None)
    emergency_contact_name: Mapped[str | None] = mapped_column(default=None)
    emergency_contact_phone: Mapped[str | None] = mapped_column(default=None)
    medical_alerts: Mapped[str | None] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=True)

    # appointment relationship is declared in the appointment model
    # (Spec 05) — referenced here for type-checking convenience only.
