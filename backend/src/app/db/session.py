"""Async database engine and session lifecycle.

A single app-scoped async engine is created from ``settings.database_url``.
The ``SessionLocal`` sessionmaker uses ``expire_on_commit=False`` so that
domain objects remain usable after a transaction commits (Standard §4).

``init_db`` creates all tables registered on ``Base`` and is invoked from the
application lifespan.  An optional ``engine`` argument allows callers
(tests, tooling) to target a different engine.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

engine: AsyncEngine = create_async_engine(settings.database_url, echo=False)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


class Base(DeclarativeBase):
    """Declarative base for all domain models."""


async def init_db(target_engine: AsyncEngine | None = None) -> None:
    """Create all declared tables.

    Defaults to the module-level engine; pass an explicit engine (e.g. an
    in-memory test engine) to target a different connection.
    """
    target: AsyncEngine = target_engine or engine
    async with target.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
