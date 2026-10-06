"""Datetime utilities for timezone-aware date/datetime conversions.

Provides shared helpers to avoid repeated patterns and ensure consistent
DST handling across the availability engine and schedule endpoints.
"""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo


def date_to_midnight_utc(target_date: date, clinic_tz: ZoneInfo) -> datetime:
    """Convert a clinic-local date to midnight UTC datetime.

    Args:
        target_date: Date in the clinic's timezone.
        clinic_tz: Clinic timezone (e.g., ZoneInfo("America/New_York")).

    Returns:
        Timezone-aware datetime at 00:00:00 in clinic_tz, converted to UTC.
    """
    local_midnight = datetime.combine(target_date, time.min, tzinfo=clinic_tz)
    return local_midnight.astimezone(ZoneInfo("UTC"))


def date_to_midnight_local(target_date: date, clinic_tz: ZoneInfo) -> datetime:
    """Convert a clinic-local date to timezone-aware midnight datetime.

    Args:
        target_date: Date in the clinic's timezone.
        clinic_tz: Clinic timezone.

    Returns:
        Timezone-aware datetime at 00:00:00 in clinic_tz.
    """
    return datetime.combine(target_date, time.min, tzinfo=clinic_tz)
