"""Real-time live appointment SSE stream endpoints (Spec 06 §4 — Layer 3,
PRD R-15, NFR-5).

Provides Server-Sent Events stream for front-desk and operatory screens to
receive instant appointment updates with 15-second keep-alive heartbeats.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterable

from fastapi import APIRouter, Depends, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.api.auth import CurrentUserDep, get_current_user
from app.api.deps import EventBroadcasterDep

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])

logger = logging.getLogger("app.live")


@router.get(
    "/live",
    response_class=EventSourceResponse,
    dependencies=[Depends(get_current_user)],
)
async def stream_live_appointments(
    request: Request,
    current_user: CurrentUserDep,
    broadcaster: EventBroadcasterDep,
) -> AsyncIterable[ServerSentEvent]:
    """Stream live appointment updates via Server-Sent Events (R-15, Spec 06 §5).

    Yields:
        ServerSentEvent with event_type as event name, appointment_id as event ID,
        and full AppointmentLiveEvent as JSON data payload.

    Keep-alive:
        Emits a `: ping` comment every 15 seconds of inactivity to prevent
        client/proxy connection timeouts.

    Cleanup:
        Subscriber queue is unsubscribed and garbage collected on disconnect.
    """
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    user_id = getattr(current_user, "id", "unknown")
    queue = await broadcaster.subscribe()
    try:
        logger.info(
            "SSE connection opened: correlation_id=%s user_id=%s subscriber_count=%d",
            correlation_id,
            user_id,
            await broadcaster.subscriber_count,
        )
        while True:
            try:
                # Wait for next event with a 15-second timeout for keep-alive
                event_data = await asyncio.wait_for(queue.get(), timeout=15.0)
                logger.debug("SSE sending event: %s", event_data.event_type)
                yield ServerSentEvent(
                    data=event_data.model_dump(by_alias=True, mode="json"),
                    event=event_data.event_type,
                    id=str(event_data.appointment_id),
                )
            except TimeoutError:
                # Periodic keep-alive ping comment to prevent client/proxy timeouts
                logger.info("SSE sending keep-alive ping")
                yield ServerSentEvent(comment="ping")
    finally:
        await broadcaster.unsubscribe(queue)
        logger.info(
            "SSE connection closed: correlation_id=%s user_id=%s subscriber_count=%d",
            correlation_id,
            user_id,
            await broadcaster.subscriber_count,
        )
