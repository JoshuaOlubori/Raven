"""Shared schema and constrained-type unit tests (Architecture §3 / Standard §3).

Verifies that ``ServiceDuration`` rejects invalid values per Spec 03 §2, and
that ``PatientCreate`` rejects future dates of birth per Spec 02 §2.
Verifies that ``WorkingShiftCreate`` and ``TimeOffBlockCreate`` reject
invalid time ranges per Spec 04 §2.
Expected values come from the spec, never from the implementation under test.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas import (
    AppointmentStatusUpdate,
    PatientCreate,
    ServiceCreate,
    TimeOffBlockCreate,
    WorkingShiftCreate,
)


def test_invalid_duration_rejected_422() -> None:
    """Spec 03 §2: duration <= 0 or > 480 is rejected with ValidationError."""
    # duration of 0 is invalid (must be > 0)
    with pytest.raises(ValidationError):
        ServiceCreate(name="Cleaning", duration_minutes=0)

    # negative duration is invalid
    with pytest.raises(ValidationError):
        ServiceCreate(name="Cleaning", duration_minutes=-15)

    # duration above 480 is invalid (max is 480 = 8 hours)
    with pytest.raises(ValidationError):
        ServiceCreate(name="Cleaning", duration_minutes=481)

    # duration of 480 (8 hours) is the valid upper bound
    ServiceCreate(name="Cleaning", duration_minutes=480)


def test_future_dob_rejected_422() -> None:
    """Spec 02 §2: date_of_birth in the future is rejected with ValidationError."""
    future_dob = date.today() + timedelta(days=1)

    with pytest.raises(ValidationError):
        PatientCreate(
            first_name="Jane",
            last_name="Doe",
            date_of_birth=future_dob,
            phone="555-123-4567",
        )


# ---------------------------------------------------------------------------
# Schedule schema tests (Spec 04 §2 — Layer 1)
# ---------------------------------------------------------------------------


def test_shift_start_after_end_rejected() -> None:
    """Spec 04 §2: WorkingShiftCreate rejects
    start_time >= end_time with ValidationError.
    """
    dentist_id = uuid4()

    # start_time == end_time should be rejected
    with pytest.raises(ValidationError):
        WorkingShiftCreate(
            dentist_id=dentist_id,
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(9, 0),
        )

    # start_time > end_time should be rejected
    with pytest.raises(ValidationError):
        WorkingShiftCreate(
            dentist_id=dentist_id,
            day_of_week=0,
            start_time=time(17, 0),
            end_time=time(9, 0),
        )

    # Valid time range should pass
    WorkingShiftCreate(
        dentist_id=dentist_id,
        day_of_week=0,
        start_time=time(9, 0),
        end_time=time(17, 0),
    )


def test_time_off_block_start_after_end_rejected() -> None:
    """Spec 04 §2: TimeOffBlockCreate rejects
    start_time >= end_time with ValidationError.
    """
    dentist_id = uuid4()
    base_time = datetime(2026, 1, 15, 9, 0, 0)

    # start_time == end_time should be rejected
    with pytest.raises(ValidationError):
        TimeOffBlockCreate(
            dentist_id=dentist_id,
            start_time=base_time,
            end_time=base_time,
            reason="Vacation",
        )

    # start_time > end_time should be rejected
    with pytest.raises(ValidationError):
        TimeOffBlockCreate(
            dentist_id=dentist_id,
            start_time=base_time + timedelta(hours=8),
            end_time=base_time,
            reason="Vacation",
        )

    # Valid time range should pass
    TimeOffBlockCreate(
        dentist_id=dentist_id,
        start_time=base_time,
        end_time=base_time + timedelta(hours=1),
        reason="Lunch",
    )


# ---------------------------------------------------------------------------
# Appointment lifecycle schema tests (T-010, Spec 05 §2)
# ---------------------------------------------------------------------------


def test_cancelled_status_requires_dedicated_cancel_endpoint() -> None:
    """T-010: CANCELLED cannot bypass the required cancellation-reason contract."""
    with pytest.raises(
        ValidationError,
        match="CANCELLED requires the dedicated cancel endpoint",
    ):
        AppointmentStatusUpdate.model_validate(
            {"toStatus": "CANCELLED", "note": "cancel"}
        )

    # Non-cancellation lifecycle targets remain valid request payloads.
    request = AppointmentStatusUpdate.model_validate({"toStatus": "CONFIRMED"})
    assert request.to_status == "CONFIRMED"
