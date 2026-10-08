"""Domain model package — re-exports all ORM models so their tables are
registered on ``Base.metadata`` at import time (required by ``init_db``)."""

from app.models.appointment import Appointment
from app.models.audit import AppointmentAuditLog
from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.patient import Patient
from app.models.schedule import TimeOffBlock, WorkingShift
from app.models.service import DentalService
from app.models.staff import Staff

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "Appointment",
    "AppointmentAuditLog",
    "Patient",
    "Staff",
    "DentalService",
    "WorkingShift",
    "TimeOffBlock",
]
