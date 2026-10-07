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
from app.services.appointment_service import AppointmentService
from app.services.auth_service import AuthService
from app.services.availability_engine import AvailabilityEngine
from app.services.patient_service import PatientService
from app.services.schedule_service import ScheduleService
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


# ---------------------------------------------------------------------------
# Patient service dependency (Spec 02 §4 — Layer 3)
# ---------------------------------------------------------------------------


def get_patient_service(session: DbSessionDep) -> PatientService:
    """Construct a ``PatientService`` with the request-scoped session."""
    return PatientService(session)


PatientServiceDep = Annotated[PatientService, Depends(get_patient_service)]


# ---------------------------------------------------------------------------
# Schedule service dependency (Spec 04 §4 — Layer 3)
# ---------------------------------------------------------------------------


def get_schedule_service(session: DbSessionDep) -> ScheduleService:
    """Construct a ``ScheduleService`` with the request-scoped session."""
    return ScheduleService(session)


ScheduleServiceDep = Annotated[ScheduleService, Depends(get_schedule_service)]


# ---------------------------------------------------------------------------
# Availability engine dependency (Spec 04 §5 — Layer 4)
# ---------------------------------------------------------------------------


def get_availability_engine(
    session: DbSessionDep,
    settings: SettingsDep,
) -> AvailabilityEngine:
    """Construct an ``AvailabilityEngine`` with the request-scoped
    session and settings.
    """
    return AvailabilityEngine(
        session=session,
        settings=settings,
    )


AvailabilityEngineDep = Annotated[AvailabilityEngine, Depends(get_availability_engine)]


# ---------------------------------------------------------------------------
# Appointment service dependency (Spec 05 §4 — Layer 3)
# ---------------------------------------------------------------------------


def get_appointment_service(
    session: DbSessionDep,
    settings: SettingsDep,
) -> AppointmentService:
    """Construct an ``AppointmentService`` with the request-scoped
    session and settings.
    """
    return AppointmentService(session=session, settings=settings)


AppointmentServiceDep = Annotated[AppointmentService, Depends(get_appointment_service)]
