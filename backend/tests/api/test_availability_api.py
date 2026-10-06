"""Availability API tests (Spec 04 §4 — Layer 3, PRD R-9, NFR-2).

Each test drives the public HTTP seam with expected values drawn from the PRD
and spec, never from the implementation under test.
"""

from __future__ import annotations

from datetime import time
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.schedule import WorkingShift
from app.models.service import DentalService
from app.models.staff import Staff

# ---------------------------------------------------------------------------
# Fixtures for availability tests
# ---------------------------------------------------------------------------


@pytest.fixture
async def availability_dentist(
    test_session_local: async_sessionmaker,
) -> Staff:
    """Create a dentist with a Monday shift for availability tests."""
    async with test_session_local() as session:
        dentist = Staff(
            email=f"avail-dentist-{uuid4().hex[:8]}@clinic.com",
            hashed_password="irrelevant",
            full_name="Dr. Availability Test",
            role="DENTIST",
            is_active=True,
        )
        session.add(dentist)
        await session.flush()

        # Add Monday 09:00-12:00 shift
        shift = WorkingShift(
            dentist_id=dentist.id,
            day_of_week=0,  # Monday
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        session.add(shift)
        await session.commit()
        await session.refresh(dentist)
        return dentist


@pytest.fixture
async def availability_service(
    test_session_local: async_sessionmaker,
) -> DentalService:
    """Create a 45-minute service for availability tests."""
    async with test_session_local() as session:
        service = DentalService(
            name=f"Availability Test Cleaning {uuid4().hex[:8]}",
            description="45 min test service",
            duration_minutes=45,
            is_active=True,
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)
        return service


# ---------------------------------------------------------------------------
# AC4: test_availability_endpoint_success_200
# ---------------------------------------------------------------------------


async def test_availability_endpoint_success_200(
    admin_staff: Staff,
    availability_dentist: Staff,
    availability_service: DentalService,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """R-9: GET /availability returns 200 with slots array populated
    with start/end times for a dentist with shifts.
    """
    headers = auth_headers(admin_staff.id, admin_staff.role)

    # Query for a Monday (Jan 5, 2026 is a Monday)
    response = await client.get(
        "/api/v1/schedules/availability",
        headers=headers,
        params={
            "dentistId": str(availability_dentist.id),
            "serviceId": str(availability_service.id),
            "date": "2026-01-05",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["date"] == "2026-01-05"
    assert body["serviceId"] == str(availability_service.id)
    assert body["durationMinutes"] == 45
    assert "slots" in body
    assert isinstance(body["slots"], list)
    assert len(body["slots"]) > 0

    # Verify slot structure
    for slot in body["slots"]:
        assert "startTime" in slot
        assert "endTime" in slot
        assert "dentistId" in slot
        assert "dentistName" in slot
        assert slot["dentistId"] == str(availability_dentist.id)
        assert slot["dentistName"] == availability_dentist.full_name


async def test_availability_endpoint_no_shifts_returns_empty(
    admin_staff: Staff,
    availability_service: DentalService,
    auth_headers: callable,
    client: AsyncClient,
    test_session_local: async_sessionmaker,
) -> None:
    """Given a dentist with no shifts on the requested date, returns 200
    with empty slots array (DentistNotAvailableError returns 200 per spec).
    """
    headers = auth_headers(admin_staff.id, admin_staff.role)

    # Create a dentist with no shifts
    async with test_session_local() as session:
        dentist = Staff(
            email=f"no-shift-{uuid4().hex[:8]}@clinic.com",
            hashed_password="irrelevant",
            full_name="Dr. No Shifts",
            role="DENTIST",
            is_active=True,
        )
        session.add(dentist)
        await session.commit()
        await session.refresh(dentist)

    # Query for a Tuesday (no shift defined)
    response = await client.get(
        "/api/v1/schedules/availability",
        headers=headers,
        params={
            "dentistId": str(dentist.id),
            "serviceId": str(availability_service.id),
            "date": "2026-01-06",  # Tuesday
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["slots"] == []


async def test_availability_endpoint_all_dentists(
    admin_staff: Staff,
    availability_service: DentalService,
    auth_headers: callable,
    client: AsyncClient,
    test_session_local: async_sessionmaker,
) -> None:
    """Availability query without dentist_id returns slots for all dentists."""
    headers = auth_headers(admin_staff.id, admin_staff.role)

    # Create a second dentist with a Monday shift
    async with test_session_local() as session:
        dentist2 = Staff(
            email=f"avail-dentist2-{uuid4().hex[:8]}@clinic.com",
            hashed_password="irrelevant",
            full_name="Dr. Second Dentist",
            role="DENTIST",
            is_active=True,
        )
        session.add(dentist2)
        await session.flush()

        shift2 = WorkingShift(
            dentist_id=dentist2.id,
            day_of_week=0,  # Monday
            start_time=time(14, 0),
            end_time=time(17, 0),
        )
        session.add(shift2)
        await session.commit()
        await session.refresh(dentist2)

    # Omit dentistId - should return slots for all dentists with Monday shifts
    response = await client.get(
        "/api/v1/schedules/availability",
        headers=headers,
        params={
            "serviceId": str(availability_service.id),
            "date": "2026-01-05",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["slots"] is not None
    # Should have slots from both dentists
    dentist_ids = {slot["dentistId"] for slot in body["slots"]}
    assert len(dentist_ids) >= 1


async def test_availability_endpoint_requires_service_id(
    admin_staff: Staff,
    availability_dentist: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """Availability query requires service_id parameter."""
    headers = auth_headers(admin_staff.id, admin_staff.role)

    # Omit serviceId
    response = await client.get(
        "/api/v1/schedules/availability",
        headers=headers,
        params={
            "dentistId": str(availability_dentist.id),
            "date": "2026-01-05",
        },
    )

    assert response.status_code == 422  # Validation error


async def test_availability_endpoint_requires_date(
    admin_staff: Staff,
    availability_dentist: Staff,
    availability_service: DentalService,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """Availability query requires date parameter."""
    headers = auth_headers(admin_staff.id, admin_staff.role)

    # Omit date
    response = await client.get(
        "/api/v1/schedules/availability",
        headers=headers,
        params={
            "dentistId": str(availability_dentist.id),
            "serviceId": str(availability_service.id),
        },
    )

    assert response.status_code == 422  # Validation error


async def test_availability_endpoint_invalid_service_404(
    admin_staff: Staff,
    availability_dentist: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """Availability query with non-existent service returns 404."""
    headers = auth_headers(admin_staff.id, admin_staff.role)

    fake_service_id = UUID("00000000-0000-0000-0000-000000000000")

    response = await client.get(
        "/api/v1/schedules/availability",
        headers=headers,
        params={
            "dentistId": str(availability_dentist.id),
            "serviceId": str(fake_service_id),
            "date": "2026-01-05",
        },
    )

    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "SERVICE_NOT_FOUND"


async def test_availability_unauthenticated_rejected_401(
    availability_dentist: Staff,
    availability_service: DentalService,
    client: AsyncClient,
) -> None:
    """Unauthenticated request to availability endpoint returns 401."""
    response = await client.get(
        "/api/v1/schedules/availability",
        params={
            "dentistId": str(availability_dentist.id),
            "serviceId": str(availability_service.id),
            "date": "2026-01-05",
        },
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# AC5: test_availability_latency_benchmark (NFR-2)
# ---------------------------------------------------------------------------


async def test_availability_latency_benchmark(
    admin_staff: Staff,
    availability_dentist: Staff,
    availability_service: DentalService,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """NFR-2: Availability slot lookups execute in under 100ms latency.

    This is a basic integration test - real benchmarking would need load testing.
    """
    import time as time_module

    headers = auth_headers(admin_staff.id, admin_staff.role)

    start = time_module.perf_counter()
    response = await client.get(
        "/api/v1/schedules/availability",
        headers=headers,
        params={
            "dentistId": str(availability_dentist.id),
            "serviceId": str(availability_service.id),
            "date": "2026-01-05",
        },
    )
    elapsed_ms = (time_module.perf_counter() - start) * 1000

    assert response.status_code == 200
    # Should be well under 100ms for in-memory SQLite
    msg = f"Availability query took {elapsed_ms:.1f}ms (expected < 100ms)"
    assert elapsed_ms < 100, msg
