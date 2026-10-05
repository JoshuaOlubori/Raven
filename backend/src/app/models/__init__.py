"""Domain model package — re-exports all ORM models so their tables are
registered on ``Base.metadata`` at import time (required by ``init_db``)."""

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.staff import Staff

__all__ = ["Base", "TimestampMixin", "UUIDMixin", "Staff"]
