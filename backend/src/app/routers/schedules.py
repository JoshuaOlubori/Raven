"""Schedule management endpoints (Spec 04 §4 — Layer 3, PRD R-7, R-8).

Thin handlers that receive dependencies, delegate to ``ScheduleService``,
and return Pydantic response models.  No business logic lives here — the
handler is the *last* stop before the service layer.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.auth import CurrentUserDep, get_current_user, require_roles
from app.api.deps import ScheduleServiceDep
from app.schemas import (
    TimeOffBlockCreate,
    TimeOffBlockRead,
    WorkingShiftCreate,
    WorkingShiftRead,
)

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
    from datetime import UTC, time

    start_range = datetime.combine(start_date, time.min, tzinfo=UTC)
    end_range = datetime.combine(end_date, time.max, tzinfo=UTC)

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
