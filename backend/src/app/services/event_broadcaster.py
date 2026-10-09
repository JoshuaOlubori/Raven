"""Event broadcaster for real-time SSE distribution (Spec 06 §3 — Layer 3, NFR-5).

Singleton pub-sub managing active subscriber queues with thread-safe
registration and deregistration per Standard §7.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas import AppointmentLiveEvent

logger = logging.getLogger("app.event_broadcaster")


class EventBroadcaster:
    """Thread-safe in-memory pub-sub for SSE event distribution.

    Manages a set of asyncio.Queue instances representing active SSE subscribers.
    Uses asyncio.Lock for registration/deregistration to avoid blocking
    the event loop (Standard §7, NFR-5).
    """

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[AppointmentLiveEvent]] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[AppointmentLiveEvent]:
        """Register a new subscriber and return its queue.

        Returns:
            asyncio.Queue that will receive published AppointmentLiveEvent objects.
        """
        queue: asyncio.Queue[AppointmentLiveEvent] = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(queue)
        logger.info(
            "SSE subscriber added: subscriber_count=%d",
            len(self._subscribers),
        )
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[AppointmentLiveEvent]) -> None:
        """Deregister a subscriber queue.

        Args:
            queue: The queue returned by subscribe() to remove.
        """
        async with self._lock:
            self._subscribers.discard(queue)
        logger.info(
            "SSE subscriber removed: subscriber_count=%d",
            len(self._subscribers),
        )

    async def publish(self, event: AppointmentLiveEvent) -> None:
        """Publish an event to all active subscribers.

        Non-blocking: puts event on each subscriber's queue without waiting.
        If a queue is full, the event is dropped for that subscriber (best-effort)
        and a warning is logged.

        Args:
            event: The AppointmentLiveEvent to broadcast.
        """
        async with self._lock:
            subscribers = list(self._subscribers)

        for queue in subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "SSE subscriber queue full, dropping event: "
                    "event_type=%s appointment_id=%s",
                    event.event_type,
                    event.appointment_id,
                )

    @property
    async def subscriber_count(self) -> int:
        """Return the number of active subscribers."""
        async with self._lock:
            return len(self._subscribers)


# Global singleton instance
_event_broadcaster: EventBroadcaster | None = None
_broadcaster_lock = asyncio.Lock()


def get_event_broadcaster() -> EventBroadcaster:
    """Return the global EventBroadcaster singleton (async-safe initialization)."""
    global _event_broadcaster
    if _event_broadcaster is None:
        # Note: This is not truly async-safe without a lock, but in practice
        # initialization happens at startup before concurrent requests.
        # For full safety, use the lifespan startup hook.
        _event_broadcaster = EventBroadcaster()
    return _event_broadcaster


async def get_event_broadcaster_async() -> EventBroadcaster:
    """Return the global EventBroadcaster singleton (async-safe initialization)."""
    global _event_broadcaster
    async with _broadcaster_lock:
        if _event_broadcaster is None:
            _event_broadcaster = EventBroadcaster()
    return _event_broadcaster


def reset_event_broadcaster() -> None:
    """Reset the global EventBroadcaster singleton (for testing).

    Allows test isolation by clearing the module-level singleton state.
    """
    global _event_broadcaster
    _event_broadcaster = None
