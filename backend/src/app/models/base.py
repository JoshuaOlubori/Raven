"""Declarative base, mixins, and shared model primitives (Standard §2 / §4).

``Base`` is the single ``DeclarativeBase`` subclass every domain model inherits
from.  ``init_db`` in ``app/db/session.py`` calls ``Base.metadata.create_all``,
so all model modules must be imported before that runs — the package-level
import in ``app/models/__init__.py`` ensures registration.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Return the current UTC timestamp (timezone-aware)."""
    return datetime.now(UTC)


class Base(AsyncAttrs, DeclarativeBase):
    """Declarative base for all domain models."""


class UUIDMixin:
    """Mixin providing a UUID primary key with a random default."""

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)


class TimestampMixin:
    """Mixin providing ``created_at`` and ``updated_at`` UTC timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
