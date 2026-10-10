"""Idempotent reminder dispatch orchestration (Spec 06 §6, ADR 0002)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import (
    claim_pending_reminders,
    complete_reminder_claim,
    release_reminder_claim,
)
from app.schemas import ReminderDispatchResult
from app.services.notification_service import NotificationService

logger = logging.getLogger("app.reminders")


class ReminderDispatcher:
    """Dispatch eligible reminders using one transactional claim workflow."""

    def __init__(
        self, session: AsyncSession, notification_service: NotificationService
    ) -> None:
        self._session = session
        self._notification_service = notification_service

    async def dispatch(self) -> ReminderDispatchResult:
        """Send reminders in the inclusive 23–25 hour window.

        Claims stay uncommitted until delivery finishes. Successful claims are
        stamped with their delivery time; failed deliveries are released before
        the caller commits, allowing a later dispatcher run to retry them.
        """
        claim_time = datetime.now(UTC)
        window_start = claim_time.replace(tzinfo=None) + timedelta(hours=23)
        window_end = claim_time.replace(tzinfo=None) + timedelta(hours=25)
        appointments = await claim_pending_reminders(
            self._session, window_start, window_end, claim_time
        )

        dispatched_count = 0
        for appointment in appointments:
            try:
                await self._notification_service.send_reminder(appointment)
            except Exception:
                await release_reminder_claim(self._session, appointment.id, claim_time)
                logger.exception(
                    "Failed to dispatch reminder for appointment %s", appointment.id
                )
            else:
                await complete_reminder_claim(
                    self._session,
                    appointment.id,
                    claim_time,
                    datetime.now(UTC),
                )
                dispatched_count += 1

        return ReminderDispatchResult(
            dispatchedCount=dispatched_count,
            checkedWindowStart=window_start,
            checkedWindowEnd=window_end,
        )
