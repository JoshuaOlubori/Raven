"""Redis-backed cross-instance event delivery tests for T-011 (ADR 0003)."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.schemas import AppointmentLiveEvent
from app.services.event_broadcaster import EventBroadcaster


@pytest.mark.skipif(
    not os.getenv("TEST_REDIS_URL"),
    reason="TEST_REDIS_URL must point to an isolated test Redis instance",
)
async def test_redis_pubsub_delivers_event_between_broadcaster_instances() -> None:
    """A publisher instance delivers the full event to a separate worker instance."""
    redis_url = os.environ["TEST_REDIS_URL"]
    publisher_worker = EventBroadcaster()
    subscriber_worker = EventBroadcaster()
    queue = None

    try:
        # start() pings Redis and awaits SUBSCRIBE before returning.
        await subscriber_worker.start(redis_url)
        await publisher_worker.start(redis_url)
        queue = await subscriber_worker.subscribe()

        event = AppointmentLiveEvent(
            eventType="appointment.checked_in",
            appointmentId=uuid4(),
            dentistId=uuid4(),
            patientName="Jane Doe",
            status="CHECKED_IN",
            startTime=datetime.now(UTC),
        )

        await publisher_worker.publish(event)
        received = await asyncio.wait_for(queue.get(), timeout=5.0)

        assert received is not None
        assert received.event_type == event.event_type
        assert received.appointment_id == event.appointment_id
        assert received.dentist_id == event.dentist_id
        assert received.patient_name == event.patient_name
        assert received.status == event.status
        assert received.start_time == event.start_time
        assert received.timestamp == event.timestamp
    finally:
        if queue is not None:
            await subscriber_worker.unsubscribe(queue)
        await publisher_worker.stop()
        await subscriber_worker.stop()
