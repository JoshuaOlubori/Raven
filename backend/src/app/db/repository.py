"""Stateless asynchronous data-access functions (Standard §2 / §4).

Repository functions are pure: they accept a session and return domain
objects.  No business logic lives here — queries only.
"""

from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.models.schedule import TimeOffBlock, WorkingShift
from app.models.service import DentalService
from app.models.staff import Staff


async def get_staff_by_id(session: AsyncSession, staff_id: UUID) -> Staff | None:
    """Fetch a single staff member by primary key."""
    return await session.get(Staff, staff_id)


async def get_staff_by_email(session: AsyncSession, email: str) -> Staff | None:
    """Fetch a single staff member by unique email address."""
    result = await session.scalars(select(Staff).where(Staff.email == email))
    return result.one_or_none()


async def create_staff(
    session: AsyncSession,
    *,
    email: str,
    hashed_password: str,
    full_name: str,
    role: str,
) -> Staff:
    """Insert a new staff member and return the persisted object."""
    staff = Staff(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        role=role,
    )
    session.add(staff)
    await session.flush()
    await session.refresh(staff)
    return staff


async def list_staff(
    session: AsyncSession,
    role: str | None = None,
    active_only: bool = True,
) -> list[Staff]:
    """Return staff members, optionally filtered by role and active status."""
    query = select(Staff)
    if role is not None:
        query = query.where(Staff.role == role)
    if active_only:
        query = query.where(Staff.is_active.is_(True))
    result = await session.execute(query)
    return list(result.scalars().all())


async def update_staff(
    session: AsyncSession,
    staff: Staff,
    **kwargs: object,
) -> Staff:
    """Apply keyword field updates to a staff row and return the refreshed object."""
    for key, value in kwargs.items():
        setattr(staff, key, value)
    session.add(staff)
    await session.flush()
    await session.refresh(staff)
    return staff


# ---------------------------------------------------------------------------
# Service repository functions (Spec 03 §3 — Layer 2)
# ---------------------------------------------------------------------------


async def get_service_by_id(
    session: AsyncSession, service_id: UUID
) -> DentalService | None:
    """Fetch a single dental service by primary key."""
    return await session.get(DentalService, service_id)


async def get_service_by_name(session: AsyncSession, name: str) -> DentalService | None:
    """Fetch a single dental service by unique name."""
    result = await session.scalars(
        select(DentalService).where(DentalService.name == name)
    )
    return result.one_or_none()


async def create_service(
    session: AsyncSession,
    *,
    name: str,
    description: str | None,
    duration_minutes: int,
) -> DentalService:
    """Insert a new dental service and return the persisted object."""
    service = DentalService(
        name=name,
        description=description,
        duration_minutes=duration_minutes,
    )
    session.add(service)
    await session.flush()
    await session.refresh(service)
    return service


async def list_services(
    session: AsyncSession,
    active_only: bool = True,
) -> list[DentalService]:
    """Return services, optionally filtered to active only (Spec 03 §4)."""
    query = select(DentalService)
    if active_only:
        query = query.where(DentalService.is_active.is_(True))
    result = await session.execute(query)
    return list(result.scalars().all())


async def update_service(
    session: AsyncSession,
    service: DentalService,
    **kwargs: object,
) -> DentalService:
    """Apply keyword field updates to a service row and return the refreshed object."""
    for key, value in kwargs.items():
        setattr(service, key, value)
    session.add(service)
    await session.flush()
    await session.refresh(service)
    return service


# ---------------------------------------------------------------------------
# Patient repository functions (Spec 02 §3 — Layer 2)
# ---------------------------------------------------------------------------


async def get_patient_by_id(session: AsyncSession, patient_id: UUID) -> Patient | None:
    """Fetch a single patient by primary key."""
    return await session.get(Patient, patient_id)


async def list_patients(
    session: AsyncSession,
    search: str | None = None,
    include_inactive: bool = False,
    page: int = 1,
    size: int = 50,
) -> tuple[list[Patient], int]:
    """Return patients with optional case-insensitive search and pagination.

    Active-only is the default; pass ``include_inactive=True`` to see soft-deleted
    records (Spec 02 §3, §6).
    """
    stmt = select(Patient)
    if not include_inactive:
        stmt = stmt.where(Patient.is_active.is_(True))
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Patient.first_name.ilike(pattern),
                Patient.last_name.ilike(pattern),
                Patient.phone.ilike(pattern),
            )
        )

    # Total count without ORDER BY / LIMIT / OFFSET (Spec 02 §2 — PatientPage).
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = await session.scalar(count_stmt)  # type: ignore[assignment]

    offset = (page - 1) * size
    paged_stmt = (
        stmt.order_by(Patient.last_name, Patient.first_name).offset(offset).limit(size)
    )
    result = await session.execute(paged_stmt)
    patients = list(result.scalars().all())
    return patients, total


async def create_patient(
    session: AsyncSession,
    *,
    first_name: str,
    last_name: str,
    date_of_birth: date,
    phone: str,
    email: str | None = None,
    emergency_contact_name: str | None = None,
    emergency_contact_phone: str | None = None,
    medical_alerts: str | None = None,
) -> Patient:
    """Insert a new patient and return the persisted object."""
    patient = Patient(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date_of_birth,
        phone=phone,
        email=email,
        emergency_contact_name=emergency_contact_name,
        emergency_contact_phone=emergency_contact_phone,
        medical_alerts=medical_alerts,
    )
    session.add(patient)
    await session.flush()
    await session.refresh(patient)
    return patient


async def update_patient(
    session: AsyncSession, patient: Patient, **kwargs: object
) -> Patient:
    """Apply keyword field updates to a patient row and return the refreshed object."""
    for key, value in kwargs.items():
        setattr(patient, key, value)
    session.add(patient)
    await session.flush()
    await session.refresh(patient)
    return patient


async def soft_delete_patient(session: AsyncSession, patient: Patient) -> Patient:
    """Mark a patient inactive rather than running a SQL DELETE (R-5, Spec 02 §5)."""
    patient.is_active = False
    session.add(patient)
    await session.flush()
    await session.refresh(patient)
    return patient


# ---------------------------------------------------------------------------
# Schedule repository functions (Spec 04 §3 — Layer 2)
# ---------------------------------------------------------------------------


async def list_shifts_for_dentist(
    session: AsyncSession, dentist_id: UUID | None = None
) -> list[WorkingShift]:
    """Return all working shifts, optionally filtered by dentist."""
    stmt = select(WorkingShift)
    if dentist_id is not None:
        stmt = stmt.where(WorkingShift.dentist_id == dentist_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_shifts_by_day(
    session: AsyncSession, day_of_week: int, dentist_id: UUID | None = None
) -> list[WorkingShift]:
    """Return all working shifts for a specific day, optionally filtered by dentist."""
    stmt = select(WorkingShift).where(WorkingShift.day_of_week == day_of_week)
    if dentist_id is not None:
        stmt = stmt.where(WorkingShift.dentist_id == dentist_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_working_shift(
    session: AsyncSession,
    *,
    dentist_id: UUID,
    day_of_week: int,
    start_time: time,
    end_time: time,
) -> WorkingShift:
    """Insert a new working shift and return the persisted object."""
    shift = WorkingShift(
        dentist_id=dentist_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
    )
    session.add(shift)
    await session.flush()
    await session.refresh(shift)
    return shift


async def delete_working_shift(session: AsyncSession, shift_id: UUID) -> bool:
    """Delete a working shift by ID. Returns True if deleted, False if not found."""
    shift = await session.get(WorkingShift, shift_id)
    if shift is None:
        return False
    await session.delete(shift)
    await session.flush()
    return True


async def list_time_off_blocks(
    session: AsyncSession,
    dentist_id: UUID,
    start_range: datetime,
    end_range: datetime,
) -> list[TimeOffBlock]:
    """Return time-off blocks for a dentist within a date range."""
    result = await session.execute(
        select(TimeOffBlock)
        .where(TimeOffBlock.dentist_id == dentist_id)
        .where(TimeOffBlock.start_time < end_range)
        .where(TimeOffBlock.end_time > start_range)
    )
    return list(result.scalars().all())


async def create_time_off_block(
    session: AsyncSession,
    *,
    dentist_id: UUID,
    start_time: datetime,
    end_time: datetime,
    reason: str | None,
) -> TimeOffBlock:
    """Insert a new time-off block and return the persisted object."""
    block = TimeOffBlock(
        dentist_id=dentist_id,
        start_time=start_time,
        end_time=end_time,
        reason=reason,
    )
    session.add(block)
    await session.flush()
    await session.refresh(block)
    return block


async def delete_time_off_block(session: AsyncSession, block_id: UUID) -> bool:
    """Delete a time-off block by ID. Returns True if deleted, False if not found."""
    block = await session.get(TimeOffBlock, block_id)
    if block is None:
        return False
    await session.delete(block)
    await session.flush()
    return True
