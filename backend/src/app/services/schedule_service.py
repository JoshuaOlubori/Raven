"""Schedule domain service (Spec 04 §3 — Layer 2, PRD R-7, R-8).

Encapsulates business rules for dentist schedule management:
* Validates shift time ranges (start < end)
* Enforces non-overlapping shifts for the same dentist on the same day
* Validates time-off block time ranges
* Enforces ABAC: dentists can only manage their own time-off blocks

The service is stateless with respect to application state (NFR-5): it holds
only a reference to the request-scoped ``AsyncSession``.
"""

from __future__ import annotations

from datetime import datetime, time
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import (
    create_time_off_block,
    create_working_shift,
    delete_time_off_block,
    delete_working_shift,
    list_shifts_by_day,
    list_shifts_for_dentist,
    list_time_off_blocks,
)
from app.exceptions import (
    InvalidTimeRangeError,
    ShiftOverlapError,
    UnauthorizedScheduleModificationError,
)
from app.models.schedule import TimeOffBlock, WorkingShift


class ScheduleService:
    """Domain service for schedule operations (Spec 04 §3)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------------------------------------------------------------------
    # Working Shifts (Admin only)
    # -------------------------------------------------------------------------

    async def list_shifts(self, dentist_id: UUID | None = None) -> list[WorkingShift]:
        """List all working shifts, optionally filtered by dentist."""
        return await list_shifts_for_dentist(self._session, dentist_id)

    async def create_shift(
        self,
        *,
        dentist_id: UUID,
        day_of_week: int,
        start_time: time,
        end_time: time,
    ) -> WorkingShift:
        """Create a new working shift for a dentist (R-7).

        Validates:
        - start_time < end_time
        - No overlapping shifts for the same dentist on the same day
        """
        # Validate time range
        if start_time >= end_time:
            raise InvalidTimeRangeError()

        # Check for overlapping shifts
        existing_shifts = await list_shifts_by_day(
            self._session, day_of_week, dentist_id
        )
        for shift in existing_shifts:
            if self._shifts_overlap(
                shift.start_time, shift.end_time, start_time, end_time
            ):
                raise ShiftOverlapError()

        return await create_working_shift(
            self._session,
            dentist_id=dentist_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
        )

    async def delete_shift(self, shift_id: UUID) -> bool:
        """Delete a working shift by ID (Admin only)."""
        return await delete_working_shift(self._session, shift_id)

    # -------------------------------------------------------------------------
    # Time-Off Blocks (Admin or own Dentist)
    # -------------------------------------------------------------------------

    async def list_time_off(
        self, dentist_id: UUID, start_range: datetime, end_range: datetime
    ) -> list[TimeOffBlock]:
        """List time-off blocks for a dentist within a date range."""
        return await list_time_off_blocks(
            self._session, dentist_id, start_range, end_range
        )

    async def create_time_off(
        self,
        *,
        dentist_id: UUID,
        start_time: datetime,
        end_time: datetime,
        reason: str | None,
        current_user_id: UUID,
        current_user_role: str,
    ) -> TimeOffBlock:
        """Create a time-off block (R-8).

        Validates:
        - start_time < end_time
        - Dentists can only create time-off for themselves
        """
        # Validate time range
        if start_time >= end_time:
            raise InvalidTimeRangeError()

        # ABAC: Dentists can only create time-off for themselves
        if current_user_role == "DENTIST" and current_user_id != dentist_id:
            raise UnauthorizedScheduleModificationError()

        return await create_time_off_block(
            self._session,
            dentist_id=dentist_id,
            start_time=start_time,
            end_time=end_time,
            reason=reason,
        )

    async def delete_time_off(
        self,
        block_id: UUID,
        current_user_id: UUID,
        current_user_role: str,
    ) -> bool:
        """Delete a time-off block.

        Validates:
        - Dentists can only delete their own time-off blocks
        """
        # Get the block to check ownership
        block = await self._session.get(TimeOffBlock, block_id)
        if block is None:
            return False

        # ABAC: Dentists can only delete their own time-off blocks
        if current_user_role == "DENTIST" and current_user_id != block.dentist_id:
            raise UnauthorizedScheduleModificationError()

        return await delete_time_off_block(self._session, block_id)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _shifts_overlap(start1: time, end1: time, start2: time, end2: time) -> bool:
        """Check if two time ranges overlap on the same day."""
        return max(start1, start2) < min(end1, end2)
