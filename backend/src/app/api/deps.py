"""Dependency-injection graph for the API layer (Standard §5).

Holds the single source of truth for the request-scoped database session and
the ``*Dep`` type aliases that routers consume.  All dependency factory
functions live here; routers only import ``Annotated`` type aliases ending
in ``Dep``.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Annotated

from fastapi import BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import SessionLocal
from app.services.appointment_service import AppointmentService
from app.services.auth_service import AuthService
from app.services.availability_engine import AvailabilityEngine
from app.services.event_broadcaster import (
    EventBroadcaster,
    get_event_broadcaster,
)
from app.services.notification_service import (
    NotificationService,
    get_notification_service,
)
from app.services.patient_service import PatientService
from app.services.reminder_dispatcher import ReminderDispatcher
from app.services.schedule_service import ScheduleService
from app.services.service_catalog import ServiceCatalog

# ---------------------------------------------------------------------------
# Database session (Standard §4)
# ---------------------------------------------------------------------------


async def get_db_session(
    background_tasks: BackgroundTasks,
) -> AsyncGenerator[AsyncSession]:
    """Commit the request and defer registered callbacks until after its response."""
    session = SessionLocal()
    try:
        yield session
        await session.commit()
        callbacks: list[Callable[[], Awaitable[None]]] = session.info.pop(
            "after_commit_callbacks", []
        )
        for callback in callbacks:
            try:
                await callback()
            except Exception:
                logging.getLogger("app.db_session").exception(
                    "Post-commit callback failed"
                )

        response_callbacks: list[Callable[[], Awaitable[None]]] = session.info.pop(
            "after_response_callbacks", []
        )
        for callback in response_callbacks:
            background_tasks.add_task(callback)
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# Function-scoped cleanup is important for streaming endpoints: DB sessions
# must close before the response body starts streaming.
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
    broadcaster: EventBroadcasterDep,
    notification_service: NotificationServiceDep,
) -> AppointmentService:
    """Construct an ``AppointmentService`` with the request-scoped
    session, settings, event broadcaster, and notification service.
    """
    return AppointmentService(
        session=session,
        settings=settings,
        broadcaster=broadcaster,
        notification_service=notification_service,
    )


AppointmentServiceDep = Annotated[AppointmentService, Depends(get_appointment_service)]


# ---------------------------------------------------------------------------
# Event broadcaster dependency (Spec 06 §3 — Layer 3)
# ---------------------------------------------------------------------------


def get_event_broadcaster_dep() -> EventBroadcaster:
    """Return the global ``EventBroadcaster`` singleton (Spec 06 §3, Standard §7)."""
    return get_event_broadcaster()


EventBroadcasterDep = Annotated[EventBroadcaster, Depends(get_event_broadcaster_dep)]


# ---------------------------------------------------------------------------
# Notification service dependency (Spec 06 §3 — Layer 3)
# ---------------------------------------------------------------------------


def get_notification_service_dep() -> NotificationService:
    """Return the global ``NotificationService`` singleton (Spec 06 §3)."""
    return get_notification_service()


NotificationServiceDep = Annotated[
    NotificationService, Depends(get_notification_service_dep)
]


def get_reminder_dispatcher(
    session: DbSessionDep,
    notification_service: NotificationServiceDep,
) -> ReminderDispatcher:
    """Construct the reminder dispatcher with request-scoped dependencies."""
    return ReminderDispatcher(session, notification_service)


ReminderDispatcherDep = Annotated[ReminderDispatcher, Depends(get_reminder_dispatcher)]
