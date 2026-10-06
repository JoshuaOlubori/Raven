"""Shared Pydantic schemas and constrained types (Architecture §3 / Standard §3).

Central location for reusable constrained types (``EmailStr``, ``PasswordStr``,
``NonEmptyStr``, ``StaffRole``) and the auth-module request/response models
defined in Spec 01 §2 (Layer 1 — Contracts).
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    computed_field,
    model_validator,
)

# ---------------------------------------------------------------------------
# Shared constrained types (Spec 01 §2 — Layer 1)
# ---------------------------------------------------------------------------

StaffRole = Literal["ADMIN", "RECEPTIONIST", "DENTIST"]


def _normalize_email(value: object) -> object:
    """Strip whitespace and lowercase an email string."""
    if isinstance(value, str):
        return value.strip().lower()
    return value


def _strip(value: object) -> object:
    """Strip leading/trailing whitespace from a string."""
    if isinstance(value, str):
        return value.strip()
    return value


EmailStr = Annotated[
    str, BeforeValidator(_normalize_email), Field(min_length=3, max_length=255)
]
PasswordStr = Annotated[str, Field(min_length=8, max_length=128)]
NonEmptyStr = Annotated[
    str, BeforeValidator(_strip), Field(min_length=1, max_length=100)
]
# Spec 02 §2 — Layer 1: PhoneStr for patient contact fields.
PhoneStr = Annotated[
    str,
    BeforeValidator(_strip),
    Field(min_length=7, max_length=20, pattern=r"^\+?[0-9\s\-()]+$"),
]
ServiceDuration = Annotated[
    int,
    Field(
        gt=0,
        le=480,
        description="Duration in minutes (e.g. 15, 30, 45, 60, 90)",
    ),
]

# ---------------------------------------------------------------------------
# Auth schemas (Spec 01 §2 — Layer 1)
# ---------------------------------------------------------------------------


class TokenRequest(BaseModel):
    """Login input body. Uses ``username`` (email) per OAuth2 convention."""

    username: EmailStr
    password: PasswordStr


class TokenResponse(BaseModel):
    """Access token output with camelCase aliases (Spec 01 §2)."""

    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(alias="accessToken")
    token_type: str = Field(default="bearer", alias="tokenType")
    expires_in: int = Field(alias="expiresIn")
    role: StaffRole


class StaffRead(BaseModel):
    """Public staff representation with camelCase aliases (Spec 01 §2)."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    email: EmailStr
    full_name: NonEmptyStr = Field(alias="fullName")
    role: StaffRole
    is_active: bool = Field(alias="isActive")
    created_at: datetime = Field(alias="createdAt")


class StaffCreate(BaseModel):
    """Staff registration input (Admin only) — Spec 01 §2, Layer 1."""

    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
    password: PasswordStr
    full_name: NonEmptyStr = Field(alias="fullName")
    role: StaffRole


class StaffUpdate(BaseModel):
    """Partial staff update input — Spec 01 §2, Layer 1."""

    model_config = ConfigDict(populate_by_name=True)

    full_name: NonEmptyStr | None = Field(default=None, alias="fullName")
    role: StaffRole | None = None
    is_active: bool | None = Field(default=None, alias="isActive")


# ---------------------------------------------------------------------------
# Service schemas (Spec 03 §2 — Layer 1)
# ---------------------------------------------------------------------------


class ServiceCreate(BaseModel):
    """Dental service (procedure) creation input — Spec 03 §2, Layer 1."""

    model_config = ConfigDict(populate_by_name=True)

    name: NonEmptyStr
    description: str | None = None
    duration_minutes: ServiceDuration = Field(alias="durationMinutes")
    is_active: bool = Field(default=True, alias="isActive")


class ServiceRead(BaseModel):
    """Public service representation with camelCase aliases (Spec 03 §2)."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    name: NonEmptyStr
    description: str | None
    duration_minutes: int = Field(alias="durationMinutes")
    is_active: bool = Field(alias="isActive")
    created_at: datetime = Field(alias="createdAt")


class ServiceUpdate(BaseModel):
    """Partial service update input — Spec 03 §2, Layer 1."""

    model_config = ConfigDict(populate_by_name=True)

    name: NonEmptyStr | None = None
    description: str | None = None
    duration_minutes: ServiceDuration | None = Field(
        default=None, alias="durationMinutes"
    )
    is_active: bool | None = Field(default=None, alias="isActive")


# ---------------------------------------------------------------------------
# Patient schemas (Spec 02 §2 — Layer 1)
# ---------------------------------------------------------------------------


class PatientCreate(BaseModel):
    """Patient registration input (Receptionist, Admin) — Spec 02 §2, Layer 1."""

    model_config = ConfigDict(populate_by_name=True)

    first_name: NonEmptyStr = Field(alias="firstName")
    last_name: NonEmptyStr = Field(alias="lastName")
    date_of_birth: date = Field(alias="dateOfBirth")
    phone: PhoneStr
    email: EmailStr | None = None
    emergency_contact_name: str | None = Field(
        default=None, alias="emergencyContactName"
    )
    emergency_contact_phone: PhoneStr | None = Field(
        default=None, alias="emergencyContactPhone"
    )
    medical_alerts: str | None = Field(default=None, alias="medicalAlerts")

    @model_validator(mode="after")
    def _dob_not_in_future(self) -> Self:
        """Reject dates of birth in the future (Spec 02 §2)."""
        if self.date_of_birth > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        return self


class PatientUpdate(BaseModel):
    """Partial patient profile update input — Spec 02 §2, Layer 1."""

    model_config = ConfigDict(populate_by_name=True)

    first_name: NonEmptyStr | None = Field(default=None, alias="firstName")
    last_name: NonEmptyStr | None = Field(default=None, alias="lastName")
    date_of_birth: date | None = Field(default=None, alias="dateOfBirth")
    phone: PhoneStr | None = None
    email: EmailStr | None = None
    emergency_contact_name: str | None = Field(
        default=None, alias="emergencyContactName"
    )
    emergency_contact_phone: PhoneStr | None = Field(
        default=None, alias="emergencyContactPhone"
    )
    medical_alerts: str | None = Field(default=None, alias="medicalAlerts")

    @model_validator(mode="after")
    def _dob_not_in_future(self) -> Self:
        """Reject future dates of birth when provided (Spec 02 §2)."""
        if self.date_of_birth is not None and self.date_of_birth > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        return self


class PatientRead(BaseModel):
    """Public patient representation with camelCase aliases (Spec 02 §2)."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    first_name: NonEmptyStr = Field(alias="firstName")
    last_name: NonEmptyStr = Field(alias="lastName")
    date_of_birth: date = Field(alias="dateOfBirth")
    phone: PhoneStr
    email: EmailStr | None = None
    emergency_contact_name: str | None = Field(
        default=None, alias="emergencyContactName"
    )
    emergency_contact_phone: PhoneStr | None = Field(
        default=None, alias="emergencyContactPhone"
    )
    medical_alerts: str | None = Field(default=None, alias="medicalAlerts")
    is_active: bool = Field(alias="isActive")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    @computed_field(alias="fullName")  # type: ignore[prop-decorator]
    @property
    def full_name(self) -> str:
        """Computed full name from first and last name (Spec 02 §2)."""
        return f"{self.first_name} {self.last_name}"


class PatientPage(BaseModel):
    """Paginated patient search output — Spec 02 §2, Layer 1."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[PatientRead]
    total: int
    page: int
    size: int
    pages: int


# ---------------------------------------------------------------------------
# Schedule schemas (Spec 04 §2 — Layer 1)
# ---------------------------------------------------------------------------


DayOfWeek = Annotated[
    int, Field(ge=0, le=6, description="0=Monday, 1=Tuesday, ..., 6=Sunday")
]


class WorkingShiftCreate(BaseModel):
    """Register weekly recurring shift — Spec 04 §2, Layer 1."""

    model_config = ConfigDict(populate_by_name=True)

    dentist_id: UUID = Field(alias="dentistId")
    day_of_week: DayOfWeek = Field(alias="dayOfWeek")
    start_time: time = Field(alias="startTime")
    end_time: time = Field(alias="endTime")

    @model_validator(mode="after")
    def _validate_time_range(self) -> Self:
        """Enforce start_time < end_time (Spec 04 §2, §7)."""
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class WorkingShiftRead(BaseModel):
    """Public shift view with camelCase aliases — Spec 04 §2, Layer 1."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    dentist_id: UUID = Field(alias="dentistId")
    day_of_week: int = Field(alias="dayOfWeek")
    start_time: time = Field(alias="startTime")
    end_time: time = Field(alias="endTime")


class TimeOffBlockCreate(BaseModel):
    """Ad-hoc blocked period input — Spec 04 §2, Layer 1."""

    model_config = ConfigDict(populate_by_name=True)

    dentist_id: UUID = Field(alias="dentistId")
    start_time: datetime = Field(alias="startTime")
    end_time: datetime = Field(alias="endTime")
    reason: str | None = None

    @model_validator(mode="after")
    def _validate_time_range(self) -> Self:
        """Enforce start_time < end_time (Spec 04 §2, §7)."""
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class TimeOffBlockRead(BaseModel):
    """Public time-off view with camelCase aliases — Spec 04 §2, Layer 1."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    dentist_id: UUID = Field(alias="dentistId")
    start_time: datetime = Field(alias="startTime")
    end_time: datetime = Field(alias="endTime")
    reason: str | None
    created_at: datetime = Field(alias="createdAt")


# ---------------------------------------------------------------------------
# Availability schemas (Spec 04 §2 — Layer 1)
# ---------------------------------------------------------------------------


class AvailabilityQuery(BaseModel):
    """Query parameters for slot search — Spec 04 §2, Layer 1."""

    model_config = ConfigDict(populate_by_name=True)

    dentist_id: UUID | None = Field(default=None, alias="dentistId")
    service_id: UUID = Field(alias="serviceId")
    date: date


class TimeSlot(BaseModel):
    """Single open bookable window — Spec 04 §2, Layer 1."""

    model_config = ConfigDict(populate_by_name=True)

    start_time: datetime = Field(alias="startTime")
    end_time: datetime = Field(alias="endTime")
    dentist_id: UUID = Field(alias="dentistId")
    dentist_name: str = Field(alias="dentistName")


class AvailabilityResponse(BaseModel):
    """Collection of available slots — Spec 04 §2, Layer 1."""

    model_config = ConfigDict(populate_by_name=True)

    date: date
    service_id: UUID = Field(alias="serviceId")
    duration_minutes: int = Field(alias="durationMinutes")
    slots: list[TimeSlot]
