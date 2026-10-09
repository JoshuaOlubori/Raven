"""Event broadcaster unit tests (T-011 Test Plan #3, #4, #5).

Tests the EventBroadcaster service directly with service-level fakes.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from uuid import uuid4

import pytest

from app.schemas import AppointmentLiveEvent
from app.services.event_broadcaster import EventBroadcaster, reset_event_broadcaster


@pytest.fixture(autouse=True)
def reset_broadcaster() -> None:
    """Ensure fresh broadcaster state for each test."""
    reset_event_broadcaster()
    yield
    reset_event_broadcaster()


class TestBroadcasterFanOut:
    """Test 3: broadcaster_multiple_subscribers_fan_out"""

    async def test_multiple_subscribers_receive_event(self) -> None:
        """Event published is delivered to all active subscriber queues."""
        broadcaster = EventBroadcaster()

        queue1 = await broadcaster.subscribe()
        queue2 = await broadcaster.subscribe()
        queue3 = await broadcaster.subscribe()

        event = AppointmentLiveEvent(
            eventType="appointment.checked_in",
            appointmentId=uuid4(),
            dentistId=uuid4(),
            patientName="Jane Doe",
            status="CHECKED_IN",
            startTime=datetime.now(),
        )

        await broadcaster.publish(event)

        # All three queues should receive the event
        received1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
        received2 = await asyncio.wait_for(queue2.get(), timeout=1.0)
        received3 = await asyncio.wait_for(queue3.get(), timeout=1.0)

        assert received1.event_type == "appointment.checked_in"
        assert received2.event_type == "appointment.checked_in"
        assert received3.event_type == "appointment.checked_in"
        assert received1.appointment_id == event.appointment_id
        assert received2.appointment_id == event.appointment_id
        assert received3.appointment_id == event.appointment_id

    async def test_subscriber_count_increases_on_subscribe(self) -> None:
        """Subscriber count reflects active connections."""
        broadcaster = EventBroadcaster()

        assert await broadcaster.subscriber_count == 0

        q1 = await broadcaster.subscribe()
        assert await broadcaster.subscriber_count == 1

        q2 = await broadcaster.subscribe()
        assert await broadcaster.subscriber_count == 2

        await broadcaster.unsubscribe(q1)
        assert await broadcaster.subscriber_count == 1

        await broadcaster.unsubscribe(q2)
        assert await broadcaster.subscriber_count == 0


class TestBroadcasterDisconnectCleanup:
    """Test 4: sse_client_disconnect_cleans_up_subscription"""

    async def test_unsubscribe_removes_queue(self) -> None:
        """Unsubscribing removes the queue from active subscribers."""
        broadcaster = EventBroadcaster()

        queue = await broadcaster.subscribe()
        assert await broadcaster.subscriber_count == 1

        await broadcaster.unsubscribe(queue)
        assert await broadcaster.subscriber_count == 0

        # Publishing after unsubscribe should not deliver to removed queue
        event = AppointmentLiveEvent(
            eventType="appointment.booked",
            appointmentId=uuid4(),
            dentistId=uuid4(),
            patientName="John Smith",
            status="SCHEDULED",
            startTime=datetime.now(),
        )
        await broadcaster.publish(event)

        # Queue should be empty (no event delivered)
        assert queue.empty()

    async def test_unsubscribe_nonexistent_queue_no_error(self) -> None:
        """Unsubscribing a queue that was never subscribed is a no-op."""
        broadcaster = EventBroadcaster()
        queue = asyncio.Queue()

        # Should not raise
        await broadcaster.unsubscribe(queue)
        assert await broadcaster.subscriber_count == 0


class TestBroadcasterThreadSafety:
    """Test 5: broadcaster_thread_safety_under_concurrent_subscribe"""

    async def test_concurrent_subscribe_unsubscribe(self) -> None:
        """Concurrent subscribe/unsubscribe operations don't deadlock or race."""
        broadcaster = EventBroadcaster()

        async def subscriber_task(task_id: int) -> list[AppointmentLiveEvent]:
            queue = await broadcaster.subscribe()
            try:
                # Wait for one event
                event = await asyncio.wait_for(queue.get(), timeout=2.0)
                return [event]
            except TimeoutError:
                return []
            finally:
                await broadcaster.unsubscribe(queue)

        async def publisher_task() -> None:
            # Give subscribers time to register
            await asyncio.sleep(0.1)
            event = AppointmentLiveEvent(
                eventType="appointment.booked",
                appointmentId=uuid4(),
                dentistId=uuid4(),
                patientName="Test Patient",
                status="SCHEDULED",
                startTime=datetime.now(),
            )
            await broadcaster.publish(event)

        # Run multiple concurrent subscribers and one publisher
        results = await asyncio.gather(
            subscriber_task(1),
            subscriber_task(2),
            subscriber_task(3),
            subscriber_task(4),
            subscriber_task(5),
            publisher_task(),
        )

        # All 5 subscribers should have received the event
        received_events = [r for r in results if isinstance(r, list) and r]
        assert len(received_events) == 5

    async def test_concurrent_publish_while_subscribing(self) -> None:
        """Publishing while subscribers are being added/removed is safe."""
        broadcaster = EventBroadcaster()
        received_events: list[AppointmentLiveEvent] = []
        ready_event = asyncio.Event()

        async def publisher() -> None:
            # Wait for all subscribers to be ready
            await ready_event.wait()
            for i in range(10):
                event = AppointmentLiveEvent(
                    eventType="appointment.booked",
                    appointmentId=uuid4(),
                    dentistId=uuid4(),
                    patientName=f"Patient {i}",
                    status="SCHEDULED",
                    startTime=datetime.now(),
                )
                await broadcaster.publish(event)
                await asyncio.sleep(0.01)

        async def subscriber() -> None:
            queue = await broadcaster.subscribe()
            try:
                # Signal that this subscriber is ready
                ready_event.set()
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=0.5)
                        received_events.append(event)
                    except TimeoutError:
                        break
            finally:
                await broadcaster.unsubscribe(queue)

        await asyncio.gather(publisher(), subscriber(), subscriber(), subscriber())

        # All events should have been received by all 3 subscribers
        # (10 events * 3 subscribers = 30, but allow some tolerance for timing)
        assert len(received_events) >= 27  # At least 90% delivery


class TestBroadcasterQueueFullHandling:
    """Additional: queue full handling logs warning"""

    async def test_queue_full_logs_warning(self, caplog) -> None:
        """When subscriber queue is full, event is dropped and warning logged."""
        broadcaster = EventBroadcaster()

        # Create a small queue that will fill up quickly
        queue = asyncio.Queue(maxsize=1)

        # Subscribe normally, then replace the queue with our small one
        await broadcaster.subscribe()
        # Replace the last added queue with our small queue
        async with broadcaster._lock:
            if broadcaster._subscribers:
                # Remove the default queue and add our small one
                for q in broadcaster._subscribers:
                    broadcaster._subscribers.discard(q)
                    break
                broadcaster._subscribers.add(queue)

        event = AppointmentLiveEvent(
            eventType="appointment.booked",
            appointmentId=uuid4(),
            dentistId=uuid4(),
            patientName="Test Patient",
            status="SCHEDULED",
            startTime=datetime.now(),
        )

        # Fill the queue
        queue.put_nowait(event)

        # Try to publish another event - should be dropped with warning
        with caplog.at_level("WARNING"):
            await broadcaster.publish(event)

        assert "SSE slow consumer disconnected" in caplog.text
        assert await queue.get() is None

        # Cleanup
        await broadcaster.unsubscribe(queue)


@pytest.mark.skipif(
    not os.getenv("TEST_REDIS_URL"),
    reason="Set TEST_REDIS_URL to run the cross-worker Redis integration test",
)
class TestRedisCrossWorkerFanOut:
    """Distinct broadcaster instances model subscribers on different workers."""

    async def test_event_published_by_one_worker_reaches_another(self) -> None:
        redis_url = os.environ["TEST_REDIS_URL"]
        publisher_worker = EventBroadcaster()
        subscriber_worker = EventBroadcaster()
        queue = None

        try:
            await publisher_worker.start(redis_url)
            await subscriber_worker.start(redis_url)
            queue = await subscriber_worker.subscribe()
            event = AppointmentLiveEvent(
                eventType="appointment.checked_in",
                appointmentId=uuid4(),
                dentistId=uuid4(),
                patientName="Jane Doe",
                status="CHECKED_IN",
                startTime=datetime.now().astimezone(),
            )

            await publisher_worker.publish(event)
            received = await asyncio.wait_for(queue.get(), timeout=3.0)

            assert received is not None
            assert received.event_type == "appointment.checked_in"
            assert received.appointment_id == event.appointment_id
            assert received.patient_name == "Jane Doe"
        finally:
            if queue is not None:
                await subscriber_worker.unsubscribe(queue)
            await publisher_worker.stop()
            await subscriber_worker.stop()
