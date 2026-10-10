"""Async database engine and session lifecycle.

A single app-scoped async engine is created from ``settings.database_url``.
The ``SessionLocal`` sessionmaker uses ``expire_on_commit=False`` so that
domain objects remain usable after a transaction commits (Standard §4).

``init_db`` is an explicit test/setup helper that creates all tables registered
on ``Base``. Production schema changes are managed by Alembic migrations.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.models.base import Base

settings = get_settings()

engine: AsyncEngine = create_async_engine(settings.database_url, echo=False)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


async def init_db(target_engine: AsyncEngine | None = None) -> None:
    """Create all declared tables for explicit test/setup use.

    Production deployments must use Alembic for schema changes.
    """
    target: AsyncEngine = target_engine if target_engine is not None else engine
    async with target.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
