"""Dependency-injection graph for the API layer (Standard §5).

Holds the single source of truth for the request-scoped database session and
the ``*Dep`` type aliases that routers consume.  All dependency factory
functions live here; routers only import ``Annotated`` type aliases ending
in ``Dep``.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import SessionLocal
from app.services.auth_service import AuthService
from app.services.service_catalog import ServiceCatalog

# ---------------------------------------------------------------------------
# Database session (Standard §4)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Settings dependency
# ---------------------------------------------------------------------------

SettingsDep = Annotated[Settings, Depends(get_settings)]


# ---------------------------------------------------------------------------
# Auth service dependency (Spec 01 §4 — Layer 3)
# ---------------------------------------------------------------------------


def get_auth_service(
    session: DbSessionDep,
    settings: SettingsDep,
) -> AuthService:
    """Construct an ``AuthService`` with the request-scoped session and settings."""
    return AuthService(session=session, settings=settings)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


# ---------------------------------------------------------------------------
# Service catalog dependency (Spec 03 §4 — Layer 3)
# ---------------------------------------------------------------------------


def get_service_catalog(session: DbSessionDep) -> ServiceCatalog:
    """Construct a ``ServiceCatalog`` with the request-scoped session."""
    return ServiceCatalog(session)


ServiceCatalogDep = Annotated[ServiceCatalog, Depends(get_service_catalog)]
