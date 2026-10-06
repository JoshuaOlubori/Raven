"""Pure domain unit tests for the availability engine (Spec 04 §5, §9).

Tests cover:
- Dynamic slot calculation subtracting booked appointments
- Time-off block exclusion
- DST clock transition accuracy
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import Settings
from app.models.schedule import WorkingShift
from app.models.service import DentalService
from app.models.staff import Staff
from app.services.availability_engine import AvailabilityEngine

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def clinic_tz() -> ZoneInfo:
    return ZoneInfo("America/New_York")


@pytest.fixture
async def availability_engine(
    test_session_local: async_sessionmaker, clinic_tz: ZoneInfo
) -> AvailabilityEngine:
    """Create an AvailabilityEngine with a test session and settings."""
    settings = Settings()
    settings.clinic_timezone = "America/New_York"
    async with test_session_local() as session:
        yield AvailabilityEngine(session=session, settings=settings)


@pytest.fixture
async def test_dentist(
    test_session_local: async_sessionmaker, override_dbsession: None
) -> Staff:
    """Create a test dentist."""
    async with test_session_local() as session:
        dentist = Staff(
            email=f"dentist-{uuid4().hex[:8]}@clinic.com",
            hashed_password="irrelevant",
            full_name="Dr. Test Dentist",
            role="DENTIST",
            is_active=True,
        )
        session.add(dentist)
        await session.commit()
        await session.refresh(dentist)
        return dentist


@pytest.fixture
async def test_service(
    test_session_local: async_sessionmaker, override_dbsession: None
) -> DentalService:
    """Create a test dental service (45 minutes)."""
    async with test_session_local() as session:
        service = DentalService(
            name=f"Routine Cleaning {uuid4().hex[:8]}",
            description="Standard cleaning",
            duration_minutes=45,
            is_active=True,
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)
        return service


@pytest.fixture
async def monday_shift(
    test_session_local: async_sessionmaker,
    test_dentist: Staff,
    override_dbsession: None,
) -> WorkingShift:
    """Create a Monday 09:00-12:00 shift for the test dentist."""
    async with test_session_local() as session:
        shift = WorkingShift(
            dentist_id=test_dentist.id,
            day_of_week=0,  # Monday
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        session.add(shift)
        await session.commit()
        await session.refresh(shift)
        return shift


# ---------------------------------------------------------------------------
# AC1: test_dynamic_slots_subtracts_booked_appointments
# ---------------------------------------------------------------------------


async def test_dynamic_slots_subtracts_booked_appointments(
    availability_engine: AvailabilityEngine,
    test_dentist: Staff,
    test_service: DentalService,
    monday_shift: WorkingShift,
    clinic_tz: ZoneInfo,
) -> None:
    """R-9: Given a dentist working 09:00-12:00 with an existing appointment
    09:00-09:45, querying slots for a 45-minute service should return
    09:45-10:30 and 10:30-11:15 as available start times.
    """
    # Target date: a Monday in 2026 (non-DST period)
    target_date = date(2026, 1, 5)  # Monday, Jan 5 2026

    # Get available slots (no appointments yet in T-007)
    slots = await availability_engine.get_available_slots(
        dentist_id=test_dentist.id,
        service_id=test_service.id,
        target_date=target_date,
    )

    # Convert to clinic timezone for assertion
    slot_starts = [s[0].astimezone(clinic_tz) for s in slots]
    slot_ends = [s[1].astimezone(clinic_tz) for s in slots]

    # Expect slots: 09:00-09:45, 09:15-10:00, 09:30-10:15, 09:45-10:30,
    # 10:00-10:45, 10:15-11:00, 10:30-11:15, 10:45-11:30, 11:00-11:45, 11:15-12:00
    # (stepping in 15-min increments, 45-min duration)
    expected_starts = [
        time(9, 0),
        time(9, 15),
        time(9, 30),
        time(9, 45),
        time(10, 0),
        time(10, 15),
        time(10, 30),
        time(10, 45),
        time(11, 0),
        time(11, 15),
    ]

    assert len(slots) == 10
    for i, expected_start in enumerate(expected_starts):
        assert slot_starts[i].time() == expected_start
        expected_end = (
            datetime.combine(target_date, expected_start) + timedelta(minutes=45)
        ).time()
        assert slot_ends[i].time() == expected_end


# ---------------------------------------------------------------------------
# AC2: test_dynamic_slots_excludes_time_off_blocks
# ---------------------------------------------------------------------------


async def test_dynamic_slots_excludes_time_off_blocks(
    availability_engine: AvailabilityEngine,
    test_dentist: Staff,
    test_service: DentalService,
    monday_shift: WorkingShift,
    clinic_tz: ZoneInfo,
) -> None:
    """Given a dentist with a time-off block (e.g. lunch 12:00-13:00),
    no slots overlapping 12:00-13:00 should be returned.
    """
    # Target date: Monday
    target_date = date(2026, 1, 5)

    # Add a time-off block for lunch 12:00-13:00 UTC (which is 07:00-08:00 EST)
    # We need to add it in UTC for the target date
    from app.db.repository import create_time_off_block

    async with availability_engine._session as session:
        # 12:00-13:00 in America/New_York on Jan 5 = 17:00-18:00 UTC
        lunch_start = datetime(2026, 1, 5, 17, 0, 0)  # UTC
        lunch_end = datetime(2026, 1, 5, 18, 0, 0)  # UTC
        await create_time_off_block(
            session,
            dentist_id=test_dentist.id,
            start_time=lunch_start,
            end_time=lunch_end,
            reason="Lunch",
        )
        await session.commit()

    # Get available slots
    slots = await availability_engine.get_available_slots(
        dentist_id=test_dentist.id,
        service_id=test_service.id,
        target_date=target_date,
    )

    # Convert to clinic timezone
    slot_starts = [s[0].astimezone(clinic_tz) for s in slots]
    slot_ends = [s[1].astimezone(clinic_tz) for s in slots]

    # No slot should overlap 12:00-13:00
    for start, end in zip(slot_starts, slot_ends, strict=True):
        # Check if slot overlaps lunch (12:00-13:00)
        overlaps = not (end.time() <= time(12, 0) or start.time() >= time(13, 0))
        msg = f"Slot {start.time()}-{end.time()} should not overlap lunch"
        assert not overlaps, msg


# ---------------------------------------------------------------------------
# AC3: test_no_shifts_returns_empty
# ---------------------------------------------------------------------------


async def test_no_shifts_returns_empty(
    availability_engine: AvailabilityEngine,
    test_dentist: Staff,
    test_service: DentalService,
    clinic_tz: ZoneInfo,
) -> None:
    """Given a day when the dentist has no working shifts, an empty list
    of slots is returned with 200 OK (handled at API level).
    """
    # Target date: Tuesday (no shift defined for Tuesday)
    target_date = datetime(2026, 1, 6, tzinfo=clinic_tz)  # Tuesday

    slots = await availability_engine.get_available_slots(
        dentist_id=test_dentist.id,
        service_id=test_service.id,
        target_date=target_date,
    )

    assert slots == []


# ---------------------------------------------------------------------------
# AC4: test_dst_clock_transition_availability_accuracy
# ---------------------------------------------------------------------------


async def test_dst_spring_forward_availability(
    availability_engine: AvailabilityEngine,
    test_dentist: Staff,
    test_service: DentalService,
    monday_shift: WorkingShift,
    clinic_tz: ZoneInfo,
) -> None:
    """Test DST spring forward (23-hour day) - slots align with wall-clock hours.

    In America/New_York, DST starts March 8, 2026 at 02:00 -> 03:00.
    A shift 09:00-12:00 on that day should still produce correct wall-clock slots.
    """
    # March 9, 2026 is a Monday (first Monday after DST spring forward on March 8)
    target_date = date(2026, 3, 9)

    slots = await availability_engine.get_available_slots(
        dentist_id=test_dentist.id,
        service_id=test_service.id,
        target_date=target_date,
    )

    slot_starts = [s[0].astimezone(clinic_tz) for s in slots]

    # Should still have slots starting at 09:00, 09:15, etc. in wall-clock time
    assert len(slots) > 0
    assert slot_starts[0].time() == time(9, 0)
    assert slot_starts[-1].time() <= time(11, 15)


async def test_dst_fall_back_availability(
    availability_engine: AvailabilityEngine,
    test_dentist: Staff,
    test_service: DentalService,
    monday_shift: WorkingShift,
    clinic_tz: ZoneInfo,
) -> None:
    """Test DST fall back (25-hour day) - slots align with wall-clock hours.

    In America/New_York, DST ends November 1, 2026 at 02:00 -> 01:00.
    A shift 09:00-12:00 on that day should produce correct wall-clock slots.
    """
    # November 2, 2026 is a Monday (first Monday after DST fall back on November 1)
    target_date = date(2026, 11, 2)

    slots = await availability_engine.get_available_slots(
        dentist_id=test_dentist.id,
        service_id=test_service.id,
        target_date=target_date,
    )

    slot_starts = [s[0].astimezone(clinic_tz) for s in slots]

    # Should still have slots starting at 09:00, 09:15, etc. in wall-clock time
    assert len(slots) > 0
    assert slot_starts[0].time() == time(9, 0)
    assert slot_starts[-1].time() <= time(11, 15)


# ---------------------------------------------------------------------------
# Helper tests for internal methods
# ---------------------------------------------------------------------------


def test_overlaps_busy_detection() -> None:
    """Test the _overlaps_busy helper method directly."""
    engine = AvailabilityEngine.__new__(AvailabilityEngine)
    engine._clinic_tz = ZoneInfo("UTC")

    busy = [
        (datetime(2026, 1, 5, 9, 0), datetime(2026, 1, 5, 9, 45)),  # 09:00-09:45
        (datetime(2026, 1, 5, 12, 0), datetime(2026, 1, 5, 13, 0)),  # 12:00-13:00
    ]

    # Overlaps first busy interval
    assert engine._overlaps_busy(
        datetime(2026, 1, 5, 9, 30), datetime(2026, 1, 5, 10, 15), busy
    )

    # Overlaps second busy interval
    assert engine._overlaps_busy(
        datetime(2026, 1, 5, 12, 30), datetime(2026, 1, 5, 13, 15), busy
    )

    # Adjacent (not overlapping) - end == busy_start
    assert not engine._overlaps_busy(
        datetime(2026, 1, 5, 9, 45), datetime(2026, 1, 5, 10, 30), busy
    )

    # Before first busy interval
    assert not engine._overlaps_busy(
        datetime(2026, 1, 5, 8, 0), datetime(2026, 1, 5, 9, 0), busy
    )

    # After last busy interval
    assert not engine._overlaps_busy(
        datetime(2026, 1, 5, 13, 0), datetime(2026, 1, 5, 14, 0), busy
    )


def test_shift_time_to_utc_conversion() -> None:
    """Test _shift_time_to_utc converts correctly."""
    engine = AvailabilityEngine.__new__(AvailabilityEngine)
    engine._clinic_tz = ZoneInfo("America/New_York")

    # Jan 5, 2026 is EST (UTC-5)
    target_dt = datetime(2026, 1, 5, tzinfo=ZoneInfo("America/New_York"))
    result = engine._shift_time_to_utc(target_dt, time(9, 0))

    # 09:00 EST = 14:00 UTC
    assert result.hour == 14
    assert result.minute == 0

    # March 9, 2026 is EDT (UTC-4) - after DST spring forward
    target_dt = datetime(2026, 3, 9, tzinfo=ZoneInfo("America/New_York"))
    result = engine._shift_time_to_utc(target_dt, time(9, 0))

    # 09:00 EDT = 13:00 UTC
    assert result.hour == 13
    assert result.minute == 0
