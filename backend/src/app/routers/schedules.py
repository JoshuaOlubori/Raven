"""Schedule management endpoints (Spec 04 §4 — Layer 3, PRD R-7, R-8, R-9).

Thin handlers that receive dependencies, delegate to ``ScheduleService`` and
``AvailabilityEngine``, and return Pydantic response models.  No business
logic lives here — the handler is the *last* stop before the service layer.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.auth import CurrentUserDep, get_current_user, require_roles
from app.api.deps import AvailabilityEngineDep, ScheduleServiceDep
from app.schemas import (
    AvailabilityResponse,
    TimeOffBlockCreate,
    TimeOffBlockRead,
    TimeSlot,
    WorkingShiftCreate,
    WorkingShiftRead,
)
from app.utils.datetime_utils import date_to_midnight_local

if TYPE_CHECKING:
    from app.models.schedule import TimeOffBlock, WorkingShift

router = APIRouter(prefix="/api/v1/schedules", tags=["schedules"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _shift_read(shift: WorkingShift) -> WorkingShiftRead:
    """Project a ``WorkingShift`` ORM object to ``WorkingShiftRead``."""

    # We need to use the model's attributes directly
    return WorkingShiftRead(
        id=shift.id,
        dentistId=shift.dentist_id,
        dayOfWeek=shift.day_of_week,
        startTime=shift.start_time,
        endTime=shift.end_time,
    )


def _time_off_read(block: TimeOffBlock) -> TimeOffBlockRead:
    """Project a ``TimeOffBlock`` ORM object to ``TimeOffBlockRead``."""

    return TimeOffBlockRead(
        id=block.id,
        dentistId=block.dentist_id,
        startTime=block.start_time,
        endTime=block.end_time,
        reason=block.reason,
        createdAt=block.created_at,
    )


# ---------------------------------------------------------------------------
# Working Shifts (Admin only)
# ---------------------------------------------------------------------------


@router.post(
    "/shifts",
    response_model=WorkingShiftRead,
    status_code=201,
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def create_working_shift_endpoint(
    request: WorkingShiftCreate,
    service: ScheduleServiceDep,
) -> WorkingShiftRead:
    """Create a new recurring working shift (Admin only) (R-7, Spec 04 §4)."""
    shift = await service.create_shift(
        dentist_id=request.dentist_id,
        day_of_week=request.day_of_week,
        start_time=request.start_time,
        end_time=request.end_time,
    )
    return _shift_read(shift)


@router.get(
    "/shifts",
    response_model=list[WorkingShiftRead],
    dependencies=[Depends(get_current_user)],
)
async def list_working_shifts_endpoint(
    service: ScheduleServiceDep,
    dentist_id: Annotated[UUID | None, Query()] = None,
) -> list[WorkingShiftRead]:
    """List all working shifts, optionally filtered by dentist
    (All staff) (R-7, Spec 04 §4).
    """
    shifts = await service.list_shifts(dentist_id)
    return [_shift_read(s) for s in shifts]


@router.delete(
    "/shifts/{shift_id}",
    status_code=204,
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def delete_working_shift_endpoint(
    shift_id: UUID,
    service: ScheduleServiceDep,
) -> None:
    """Delete a working shift (Admin only) (R-7, Spec 04 §4)."""
    deleted = await service.delete_shift(shift_id)
    if not deleted:
        from app.exceptions import StaffNotFoundError

        raise StaffNotFoundError()


# ---------------------------------------------------------------------------
# Time-Off Blocks (Admin or own Dentist)
# ---------------------------------------------------------------------------


@router.post(
    "/time-off",
    response_model=TimeOffBlockRead,
    status_code=201,
    dependencies=[Depends(require_roles("ADMIN", "DENTIST"))],
)
async def create_time_off_endpoint(
    request: TimeOffBlockCreate,
    service: ScheduleServiceDep,
    current_user: CurrentUserDep,
) -> TimeOffBlockRead:
    """Create a time-off block (Admin or own Dentist) (R-8, Spec 04 §4)."""
    block = await service.create_time_off(
        dentist_id=request.dentist_id,
        start_time=request.start_time,
        end_time=request.end_time,
        reason=request.reason,
        current_user_id=current_user.id,
        current_user_role=current_user.role,
    )
    return _time_off_read(block)


@router.get(
    "/time-off",
    response_model=list[TimeOffBlockRead],
    dependencies=[Depends(get_current_user)],
)
async def list_time_off_endpoint(
    service: ScheduleServiceDep,
    dentist_id: Annotated[UUID, Query(alias="dentistId")],
    start_date: Annotated[date, Query(alias="startDate")],
    end_date: Annotated[date, Query(alias="endDate")],
) -> list[TimeOffBlockRead]:
    """List time-off blocks for a dentist within a date range
    (All staff) (R-8, Spec 04 §4).
    """
    # Convert date to datetime at start/end of day in UTC
    from datetime import UTC

    start_range = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
    end_range = datetime.combine(end_date, datetime.max.time(), tzinfo=UTC)

    blocks = await service.list_time_off(dentist_id, start_range, end_range)
    return [_time_off_read(b) for b in blocks]


@router.delete(
    "/time-off/{block_id}",
    status_code=204,
    dependencies=[Depends(require_roles("ADMIN", "DENTIST"))],
)
async def delete_time_off_endpoint(
    block_id: UUID,
    service: ScheduleServiceDep,
    current_user: CurrentUserDep,
) -> None:
    """Delete a time-off block (Admin or own Dentist) (R-8, Spec 04 §4)."""
    deleted = await service.delete_time_off(
        block_id, current_user.id, current_user.role
    )
    if not deleted:
        from app.exceptions import StaffNotFoundError

        raise StaffNotFoundError()


# ---------------------------------------------------------------------------
# Dynamic Availability (All staff)
# ---------------------------------------------------------------------------


@router.get(
    "/availability",
    response_model=AvailabilityResponse,
    dependencies=[Depends(get_current_user)],
)
async def get_availability_endpoint(
    engine: AvailabilityEngineDep,
    service_id: Annotated[UUID, Query(alias="serviceId")],
    target_date: Annotated[date, Query(alias="date")],
    dentist_id: Annotated[UUID | None, Query(alias="dentistId")] = None,
) -> AvailabilityResponse:
    """Get dynamically computed available slots for a dentist and service on a date.

    Query params:
    - dentist_id: Optional UUID of the dentist (defaults to all dentists with shifts)
    - service_id: Required UUID of the dental service (provides duration)
    - date: Required target date in CLINIC_TIMEZONE

    Returns AvailabilityResponse with date, service_id, duration_minutes,
    and slots array. (R-9, Spec 04 §4)
    """
    from app.db.repository import (
        get_service_by_id,
        get_staff_by_id,
        list_shifts_by_day,
    )

    # Validate service exists and get duration
    service = await get_service_by_id(engine._session, service_id)
    if service is None:
        from app.exceptions import ServiceNotFoundError

        raise ServiceNotFoundError()

    duration_minutes = service.duration_minutes

    if dentist_id is not None:
        # Single dentist query
        slots_utc = await engine.get_available_slots(
            dentist_id=dentist_id,
            service_id=service_id,
            target_date=target_date,
        )

        dentist = await get_staff_by_id(engine._session, dentist_id)
        dentist_name = dentist.full_name if dentist else "Unknown"

        time_slots = [
            TimeSlot(
                startTime=start,
                endTime=end,
                dentistId=dentist_id,
                dentistName=dentist_name,
            )
            for start, end in slots_utc
        ]
    else:
        # Query all dentists with shifts on the target weekday
        # Get weekday in clinic timezone
        target_dt_tz = date_to_midnight_local(target_date, engine._clinic_tz)
        weekday = target_dt_tz.weekday()

        shifts = await list_shifts_by_day(engine._session, weekday, None)
        if not shifts:
            return AvailabilityResponse(
                date=target_date,
                serviceId=service_id,
                durationMinutes=duration_minutes,
                slots=[],
            )

        # Group shifts by dentist and compute slots for each
        from collections import defaultdict

        shifts_by_dentist: dict[UUID, list] = defaultdict(list)
        for shift in shifts:
            shifts_by_dentist[shift.dentist_id].append(shift)

        all_slots: list[TimeSlot] = []
        for did, _dentist_shifts in shifts_by_dentist.items():
            dentist = await get_staff_by_id(engine._session, did)
            dentist_name = dentist.full_name if dentist else "Unknown"

            # Create a temporary engine call for this dentist
            slots_utc = await engine.get_available_slots(
                dentist_id=did,
                service_id=service_id,
                target_date=target_date,
            )

            time_slots = [
                TimeSlot(
                    startTime=start,
                    endTime=end,
                    dentistId=did,
                    dentistName=dentist_name,
                )
                for start, end in slots_utc
            ]
            all_slots.extend(time_slots)

        # Sort slots by start time
        all_slots.sort(key=lambda s: s.start_time)
        time_slots = all_slots

    return AvailabilityResponse(
        date=target_date,
        serviceId=service_id,
        durationMinutes=duration_minutes,
        slots=time_slots,
    )
