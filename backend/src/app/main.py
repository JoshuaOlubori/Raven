"""Application bootstrap.

Thin wiring only (Standard §2): lifespan-managed DB initialization,
correlation-ID propagation middleware, structured logging on unhandled
errors, the standardized error handlers (Architecture §4), and router
mounting.  No business logic lives here.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings
from app.db.session import SessionLocal, init_db
from app.exceptions import DomainError
from app.models.appointment import (  # noqa: F401 — register table on Base.metadata
    Appointment,
)
from app.models.patient import (  # noqa: F401 — register table on Base.metadata
    Patient,
)
from app.models.schedule import (  # noqa: F401 — register table on Base.metadata
    TimeOffBlock,
    WorkingShift,
)
from app.models.service import (
    DentalService,  # noqa: F401 — register table on Base.metadata
)
from app.models.staff import Staff  # noqa: F401 — register table on Base.metadata
from app.routers.appointments import router as appointments_router
from app.routers.auth import router as auth_router
from app.routers.live import router as live_router
from app.routers.patients import router as patients_router
from app.routers.schedules import router as schedules_router
from app.routers.services import router as services_router
from app.routers.staff import router as staff_router
from app.services.event_broadcaster import get_event_broadcaster
from app.services.notification_service import (
    NotificationService,
    get_notification_service,
)
from app.services.reminder_dispatcher import ReminderDispatcher

logger = logging.getLogger("app")


async def _reminder_worker_loop() -> None:
    """Background task that dispatches 24h reminders every 15 minutes (ADR 0002).

    Runs when ENABLE_IN_PROCESS_REMINDER_WORKER=true.
    """
    settings = get_settings()
    if not getattr(settings, "enable_in_process_reminder_worker", True):
        return

    notification_service = get_notification_service()
    logger.info("In-process reminder worker started (interval: 15 minutes)")

    while True:
        try:
            await asyncio.sleep(15 * 60)  # 15 minutes
            await _dispatch_reminders_once(notification_service)
        except asyncio.CancelledError:
            logger.info("In-process reminder worker cancelled")
            break
        except Exception:
            logger.exception("In-process reminder worker error")


async def _dispatch_reminders_once(notification_service: NotificationService) -> None:
    """Execute a single reminder dispatch cycle."""
    async with SessionLocal() as session:
        dispatcher = ReminderDispatcher(session, notification_service)
        await dispatcher.dispatch()
        await session.commit()


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    """Initialize shared resources and release them during application shutdown."""
    await init_db()
    broadcaster = get_event_broadcaster()
    await broadcaster.start(get_settings().redis_url)

    # Start in-process reminder worker if enabled (ADR 0002)
    reminder_worker_task = None
    settings = get_settings()
    if getattr(settings, "enable_in_process_reminder_worker", True):
        reminder_worker_task = asyncio.create_task(_reminder_worker_loop())

    try:
        yield
    finally:
        if reminder_worker_task:
            reminder_worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reminder_worker_task
        await broadcaster.stop()


app = FastAPI(title="Dental Clinic Appointment Tracker", lifespan=lifespan)

# Mount API routers
# live_router must come before appointments_router to avoid route conflict:
# appointments_router has GET /{appointment_id} which would catch /live
app.include_router(auth_router)
app.include_router(services_router)
app.include_router(staff_router)
app.include_router(patients_router)
app.include_router(schedules_router)
app.include_router(live_router)
app.include_router(appointments_router)


@app.middleware("http")
async def correlation_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Extract or generate a correlation ID and propagate it on the response."""
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Map ``DomainError`` subclasses to the standardized error body (Architecture §4).

    ``AuthError``, ``EmailAlreadyExistsError``, ``StaffNotFoundError``, and
    ``ForbiddenError`` all inherit from ``DomainError``, so this single
    handler covers every domain exception.
    """
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        headers={"X-Correlation-ID": correlation_id},
        content={
            "error": exc.error_code,
            "message": exc.message,
            "correlation_id": correlation_id,
        },
    )


@app.exception_handler(Exception)
async def internal_server_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Map every unhandled exception to the standardized 500 error body.

    Also logs the exception with structured context (T-001 review: missing
    structured exception logging, Architecture §4).

    The response body is sanitized: only ``error`` and ``correlation_id`` are
    returned — ``str(exc)`` is logged server-side but never leaked to the
    client (concurrency-and-ops.md §Global Middleware, T-002 review minor).
    """
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    logger.exception(
        "Unhandled server error",
        extra={"correlation_id": correlation_id},
    )
    return JSONResponse(
        status_code=500,
        headers={"X-Correlation-ID": correlation_id},
        content={
            "error": "internal_server_error",
            "correlation_id": correlation_id,
        },
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}
