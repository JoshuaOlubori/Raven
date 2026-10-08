"""Appointment Audit Log ORM model (Spec 05 §3 — Layer 2).

Append-only immutable audit trail capturing every status transition,
reschedule, and cancellation with acting staff ID and timestamps.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, utcnow

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.staff import Staff


class AppointmentAuditLog(Base, UUIDMixin):
    """Immutable audit log record for appointment lifecycle events.

    Records:
    - Status transitions (SCHEDULED -> CONFIRMED -> CHECKED_IN ->
      IN_PROGRESS -> COMPLETED)
    - Reschedules (capturing old_start_time, new_start_time)
    - Cancellations (capturing cancellation_reason as note)

    No UPDATE or DELETE endpoints exist for this table (NFR-4).
    """

    __tablename__ = "appointment_audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_appointment_created", "appointment_id", "created_at"),
    )

    appointment_id: Mapped[UUID] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("staff.id"), index=True)
    from_status: Mapped[str | None]
    to_status: Mapped[str | None]
    old_start_time: Mapped[datetime | None]
    new_start_time: Mapped[datetime | None]
    note: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    appointment: Mapped[Appointment] = relationship(
        back_populates="audit_logs",
    )
    actor: Mapped[Staff] = relationship()
