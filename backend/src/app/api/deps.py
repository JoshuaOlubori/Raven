"""Dependency-injection graph for the API layer (Standard §5).

Holds the single source of truth for the request-scoped database session:
``get_db_session`` yields an ``AsyncSession``, commits on the success path,
rolls back on any exception, and always closes the session (Standard §4).

The ``*Dep`` type-alias pattern lets path operations consume the dependency
through a clean ``Annotated`` declaration rather than repeating
``Depends(...)``.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    session = SessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
