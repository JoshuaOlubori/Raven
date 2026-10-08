"""Appointment ORM model (Spec 05 §3 — Layer 2).

Defines the core appointment entity with state machine lifecycle,
overlap prevention indexes, and audit log relationship.
All timestamps are stored in UTC.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.patient import Patient
from app.models.schedule import Staff

if TYPE_CHECKING:
    from app.models.audit import AppointmentAuditLog
    from app.models.service import DentalService


class Appointment(Base, UUIDMixin, TimestampMixin):
    """Appointment booking linking patient, dentist, and service to a time window.

    State transitions follow the FSM in Spec 05 §8:
    SCHEDULED -> CONFIRMED -> CHECKED_IN -> IN_PROGRESS -> COMPLETED
    SCHEDULED/CONFIRMED/CHECKED_IN -> CANCELLED (terminal, reason required)
    SCHEDULED/CONFIRMED -> NO_SHOW (terminal)
    """

    __tablename__ = "appointments"
    __table_args__ = (
        Index(
            "ix_appointments_dentist_start_end_status",
            "dentist_id",
            "start_time",
            "end_time",
            "status",
        ),
        Index("ix_appointments_reminder_sent_at", "reminder_sent_at"),
    )

    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    dentist_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff.id", ondelete="CASCADE"), index=True
    )
    service_id: Mapped[UUID] = mapped_column(
        ForeignKey("dental_services.id", ondelete="CASCADE"), index=True
    )
    start_time: Mapped[datetime] = mapped_column(index=True)
    end_time: Mapped[datetime] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(default="SCHEDULED", index=True)
    cancellation_reason: Mapped[str | None]
    reminder_sent_at: Mapped[datetime | None]

    patient: Mapped[Patient] = relationship(back_populates="appointments")
    dentist: Mapped[Staff] = relationship(back_populates="appointments")
    service: Mapped[DentalService] = relationship(back_populates="appointments")
    audit_logs: Mapped[list[AppointmentAuditLog]] = relationship(
        back_populates="appointment", cascade="all, delete-orphan"
    )
