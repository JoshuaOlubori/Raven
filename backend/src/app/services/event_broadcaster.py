"""Redis-backed live appointment event fan-out (Spec 06, ADR 0003).

Redis Pub/Sub carries events across worker processes. Each worker fans incoming
messages into bounded local queues for its own SSE connections.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from threading import Lock
from typing import TYPE_CHECKING, Any

from redis.asyncio import Redis

if TYPE_CHECKING:
    from app.schemas import AppointmentLiveEvent

logger = logging.getLogger("app.event_broadcaster")

EVENT_CHANNEL = "raven:appointment-events:v1"
SUBSCRIBER_QUEUE_MAXSIZE = 100


class EventBroadcaster:
    """Cross-worker Redis publisher with bounded per-worker subscriber queues."""

    def __init__(self, queue_maxsize: int = SUBSCRIBER_QUEUE_MAXSIZE) -> None:
        if queue_maxsize < 1:
            raise ValueError("queue_maxsize must be greater than zero")
        self._subscribers: set[asyncio.Queue[AppointmentLiveEvent | None]] = set()
        self._lock = asyncio.Lock()
        self._queue_maxsize = queue_maxsize
        self._redis: Redis | None = None
        self._pubsub: Any = None
        self._listener_task: asyncio.Task[None] | None = None

    async def start(self, redis_url: str) -> None:
        """Connect and subscribe before the app begins accepting requests."""
        if self._redis is not None:
            return

        redis = Redis.from_url(redis_url, decode_responses=True)
        try:
            await redis.ping()
            pubsub = redis.pubsub()
            await pubsub.subscribe(EVENT_CHANNEL)
        except Exception:
            await redis.aclose()
            logger.exception("Could not initialize Redis appointment event broker")
            raise

        self._redis = redis
        self._pubsub = pubsub
        self._listener_task = asyncio.create_task(
            self._consume_messages(), name="appointment-event-redis-listener"
        )
        logger.info("Redis appointment event broker started")

    async def stop(self) -> None:
        """Stop the listener and release Redis connections during app shutdown."""
        task = self._listener_task
        self._listener_task = None
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        if self._pubsub is not None:
            await self._pubsub.aclose()
            self._pubsub = None
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
        logger.info("Redis appointment event broker stopped")

    async def _consume_messages(self) -> None:
        """Consume Redis messages and reconnect the subscription after failures."""
        while True:
            try:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if message is None or message.get("type") != "message":
                    continue

                from app.schemas import AppointmentLiveEvent

                raw_data = message["data"]
                event = AppointmentLiveEvent.model_validate_json(raw_data)
                await self._fan_out(event)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "Redis appointment event listener failed; reconnecting"
                )
                await asyncio.sleep(1.0)
                if self._redis is None:
                    return
                try:
                    if self._pubsub is not None:
                        await self._pubsub.aclose()
                    self._pubsub = self._redis.pubsub()
                    await self._pubsub.subscribe(EVENT_CHANNEL)
                    logger.info("Redis appointment event subscription restored")
                except Exception:
                    logger.exception(
                        "Could not restore Redis appointment event subscription"
                    )
                    await asyncio.sleep(2.0)

    async def subscribe(self) -> asyncio.Queue[AppointmentLiveEvent | None]:
        """Register a local SSE client with a bounded queue."""
        queue: asyncio.Queue[AppointmentLiveEvent | None] = asyncio.Queue(
            maxsize=self._queue_maxsize
        )
        async with self._lock:
            self._subscribers.add(queue)
            count = len(self._subscribers)
        logger.info("SSE subscriber added: subscriber_count=%d", count)
        return queue

    async def unsubscribe(
        self, queue: asyncio.Queue[AppointmentLiveEvent | None]
    ) -> None:
        """Remove a local SSE client's queue."""
        async with self._lock:
            self._subscribers.discard(queue)
            count = len(self._subscribers)
        logger.info("SSE subscriber removed: subscriber_count=%d", count)

    async def publish(self, event: AppointmentLiveEvent) -> None:
        """Publish across workers; in-memory fan-out is for isolated unit tests only."""
        if self._redis is None:
            # Explicit local mode is useful for unit tests. Production lifespan
            # always calls start(), which fails startup if Redis is unavailable.
            await self._fan_out(event)
            return

        payload = event.model_dump_json(by_alias=True)
        await self._redis.publish(EVENT_CHANNEL, payload)

    async def _fan_out(self, event: AppointmentLiveEvent) -> None:
        """Fan out an event locally; terminate slow consumers."""
        async with self._lock:
            subscribers = list(self._subscribers)

        for queue in subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Replace the backlog with a sentinel. The SSE route sends a
                # resync-required frame and closes this slow connection.
                while not queue.empty():
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                queue.put_nowait(None)
                logger.warning(
                    "SSE slow consumer disconnected: event_type=%s appointment_id=%s",
                    event.event_type,
                    event.appointment_id,
                )

    @property
    async def subscriber_count(self) -> int:
        """Return the number of active local SSE clients."""
        async with self._lock:
            return len(self._subscribers)


_event_broadcaster: EventBroadcaster | None = None
_broadcaster_lock = Lock()


def get_event_broadcaster() -> EventBroadcaster:
    """Return the process-wide broadcaster, initializing it exactly once."""
    global _event_broadcaster
    with _broadcaster_lock:
        if _event_broadcaster is None:
            _event_broadcaster = EventBroadcaster()
        return _event_broadcaster


async def get_event_broadcaster_async() -> EventBroadcaster:
    """Async dependency-compatible accessor for the process-wide broadcaster."""
    return get_event_broadcaster()


def reset_event_broadcaster() -> None:
    """Reset the singleton for isolated tests."""
    global _event_broadcaster
    with _broadcaster_lock:
        _event_broadcaster = None
