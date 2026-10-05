"""Shared schema and constrained-type unit tests (Architecture §3 / Standard §3).

Verifies that ``ServiceDuration`` rejects invalid values per Spec 03 §2.
Expected values come from the spec, never from the implementation under test.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import ServiceCreate


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
