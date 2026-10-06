"""Schedule ORM models: WorkingShift and TimeOffBlock (Spec 04 §3 — Layer 2).

Defines recurring weekly shifts for dentists and ad-hoc time-off blocks
(vacations, lunches, sick leaves). All timestamps are stored in UTC
while shift times are interpreted in CLINIC_TIMEZONE (NFR-3).
"""

from __future__ import annotations

from datetime import datetime, time
from uuid import UUID

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.staff import Staff


class WorkingShift(Base, UUIDMixin):
    """Weekly recurring working shift for a dentist."""

    __tablename__ = "working_shifts"
    __table_args__ = (
        UniqueConstraint(
            "dentist_id", "day_of_week", "start_time", name="uq_dentist_day_start"
        ),
    )

    dentist_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff.id", ondelete="CASCADE"), index=True
    )
    day_of_week: Mapped[int]  # 0=Monday, ..., 6=Sunday
    start_time: Mapped[time]
    end_time: Mapped[time]

    dentist: Mapped[Staff] = relationship(back_populates="working_shifts")


class TimeOffBlock(Base, UUIDMixin, TimestampMixin):
    """Ad-hoc blocked period (vacation, lunch, sick leave) for a dentist."""

    __tablename__ = "time_off_blocks"
    __table_args__ = (
        Index(
            "ix_time_off_blocks_dentist_start_end",
            "dentist_id",
            "start_time",
            "end_time",
        ),
    )

    dentist_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff.id", ondelete="CASCADE"), index=True
    )
    start_time: Mapped[datetime] = mapped_column(index=True)
    end_time: Mapped[datetime] = mapped_column(index=True)
    reason: Mapped[str | None]

    dentist: Mapped[Staff] = relationship(back_populates="time_off_blocks")
