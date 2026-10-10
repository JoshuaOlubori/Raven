"""Stateless asynchronous data-access functions (Standard §2 / §4).

Repository functions are pure: they accept a session and return domain
objects.  No business logic lives here — queries only.
"""

from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.appointment import Appointment
from app.models.audit import AppointmentAuditLog
from app.models.patient import Patient
from app.models.schedule import TimeOffBlock, WorkingShift
from app.models.service import DentalService
from app.models.staff import Staff


async def get_staff_by_id(session: AsyncSession, staff_id: UUID) -> Staff | None:
    """Fetch a single staff member by primary key."""
    return await session.get(Staff, staff_id)


async def get_staff_by_ids(session: AsyncSession, staff_ids: list[UUID]) -> list[Staff]:
    """Fetch multiple staff members by their IDs in a single query.

    Returns a list of Staff objects in the same order as the input IDs.
    Missing IDs are skipped (no error raised).
    """
    if not staff_ids:
        return []
    result = await session.execute(select(Staff).where(Staff.id.in_(staff_ids)))
    staff_list = list(result.scalars().all())
    # Preserve input order
    staff_by_id = {s.id: s for s in staff_list}
    return [staff_by_id[sid] for sid in staff_ids if sid in staff_by_id]


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


# ---------------------------------------------------------------------------
# Appointment repository functions (Spec 05 §3 — Layer 2)
# ---------------------------------------------------------------------------


async def get_appointment(
    session: AsyncSession, appointment_id: UUID
) -> Appointment | None:
    """Fetch a single appointment by primary key."""
    return await session.get(Appointment, appointment_id)


async def get_appointment_detail(
    session: AsyncSession, appointment_id: UUID
) -> Appointment | None:
    """Fetch an appointment with eager-loaded patient, dentist, and service."""
    from sqlalchemy.orm import joinedload

    stmt = (
        select(Appointment)
        .options(
            joinedload(Appointment.patient),
            joinedload(Appointment.dentist),
            joinedload(Appointment.service),
        )
        .where(Appointment.id == appointment_id)
    )
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def list_appointments(
    session: AsyncSession,
    dentist_id: UUID | None = None,
    patient_id: UUID | None = None,
    status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[Appointment]:
    """Query appointments with optional filters."""
    stmt = select(Appointment).options(
        joinedload(Appointment.patient),
        joinedload(Appointment.dentist),
        joinedload(Appointment.service),
    )
    if dentist_id is not None:
        stmt = stmt.where(Appointment.dentist_id == dentist_id)
    if patient_id is not None:
        stmt = stmt.where(Appointment.patient_id == patient_id)
    if status is not None:
        stmt = stmt.where(Appointment.status == status)
    if start_date is not None:
        stmt = stmt.where(Appointment.start_time >= start_date)
    if end_date is not None:
        stmt = stmt.where(Appointment.end_time <= end_date)
    result = await session.execute(stmt)
    return list(result.unique().scalars().all())


async def lock_dentist_appointment_schedule(
    session: AsyncSession, dentist_id: UUID
) -> None:
    """Hold a stable dentist-row lock while checking and writing a slot.

    The dentist row exists even when there are no appointments to overlap, so
    PostgreSQL can serialize booking and rescheduling against this row.
    """
    await session.execute(
        select(Staff.id).where(Staff.id == dentist_id).with_for_update()
    )


async def check_appointment_overlap(
    session: AsyncSession,
    dentist_id: UUID,
    start_time: datetime,
    end_time: datetime,
    exclude_id: UUID | None = None,
) -> bool:
    """Check for non-cancelled overlapping appointments for a dentist.

    Two intervals [a, b) and [c, d) overlap iff max(a, c) < min(b, d).
    Equivalent to: start_time < existing.end_time AND end_time > existing.start_time

    The caller must first hold ``lock_dentist_appointment_schedule`` until the
    transaction commits; locking appointment rows cannot cover an empty result.
    """
    stmt = select(Appointment.id).where(
        Appointment.dentist_id == dentist_id,
        Appointment.status != "CANCELLED",
        Appointment.start_time < end_time,
        Appointment.end_time > start_time,
    )
    if exclude_id is not None:
        stmt = stmt.where(Appointment.id != exclude_id)
    existing = await session.scalar(stmt)
    return existing is not None


async def create_appointment(
    session: AsyncSession,
    *,
    patient_id: UUID,
    dentist_id: UUID,
    service_id: UUID,
    start_time: datetime,
    end_time: datetime,
    status: str = "SCHEDULED",
) -> Appointment:
    """Insert a new appointment and return the persisted object."""
    appointment = Appointment(
        patient_id=patient_id,
        dentist_id=dentist_id,
        service_id=service_id,
        start_time=start_time,
        end_time=end_time,
        status=status,
    )
    session.add(appointment)
    await session.flush()
    await session.refresh(appointment)
    return appointment


async def update_appointment(
    session: AsyncSession,
    appointment: Appointment,
    **kwargs: object,
) -> Appointment:
    """Apply keyword field updates to an appointment and return the refreshed object."""
    for key, value in kwargs.items():
        setattr(appointment, key, value)
    session.add(appointment)
    await session.flush()
    await session.refresh(appointment)
    return appointment


# ---------------------------------------------------------------------------
# Reminder repository functions (Spec 06 §3 — Layer 2)
# ---------------------------------------------------------------------------


async def list_pending_reminders(
    session: AsyncSession,
    window_start: datetime,
    window_end: datetime,
) -> list[Appointment]:
    """Fetch appointments in SCHEDULED/CONFIRMED state starting in window
    with reminder_sent_at IS NULL.

    Args:
        session: Database session.
        window_start: Start of the 23-25 hour window (inclusive).
        window_end: End of the 23-25 hour window (inclusive).

    Returns:
        List of appointments with patient, dentist, and service eager-loaded.
    """
    stmt = (
        select(Appointment)
        .where(
            Appointment.status.in_(["SCHEDULED", "CONFIRMED"]),
            Appointment.reminder_sent_at.is_(None),
            Appointment.start_time >= window_start,
            Appointment.start_time <= window_end,
        )
        .options(
            joinedload(Appointment.patient),
            joinedload(Appointment.dentist),
            joinedload(Appointment.service),
        )
    )
    result = await session.scalars(stmt)
    return list(result.unique().all())


async def mark_reminder_sent(
    session: AsyncSession, appointment_id: UUID, sent_at: datetime
) -> int:
    """Atomically set reminder_sent_at = sent_at for an appointment.

    Uses WHERE reminder_sent_at IS NULL to ensure idempotency: if the
    reminder was already sent, the update affects zero rows.

    Args:
        session: Database session.
        appointment_id: UUID of the appointment to update.
        sent_at: Timestamp to set as reminder_sent_at (should be timezone-aware UTC).

    Returns:
        Number of rows affected (1 if reminder was claimed, 0 if already sent).
    """
    stmt = (
        update(Appointment)
        .where(Appointment.id == appointment_id, Appointment.reminder_sent_at.is_(None))
        .values(reminder_sent_at=sent_at)
    )
    result = await session.execute(stmt)
    return int(result.rowcount)  # type: ignore[no-any-return,attr-defined]


async def complete_reminder_claim(
    session: AsyncSession,
    appointment_id: UUID,
    claim_time: datetime,
    sent_at: datetime,
) -> int:
    """Replace a claim timestamp with the actual successful delivery time."""
    stmt = (
        update(Appointment)
        .where(
            Appointment.id == appointment_id,
            Appointment.reminder_sent_at == claim_time,
        )
        .values(reminder_sent_at=sent_at)
    )
    result = await session.execute(stmt)
    return int(result.rowcount)  # type: ignore[no-any-return,attr-defined]


async def release_reminder_claim(
    session: AsyncSession, appointment_id: UUID, claim_time: datetime
) -> int:
    """Clear a failed reminder claim so a later dispatcher can retry it."""
    stmt = (
        update(Appointment)
        .where(
            Appointment.id == appointment_id,
            Appointment.reminder_sent_at == claim_time,
        )
        .values(reminder_sent_at=None)
    )
    result = await session.execute(stmt)
    return int(result.rowcount)  # type: ignore[no-any-return,attr-defined]


async def claim_pending_reminders(
    session: AsyncSession,
    window_start: datetime,
    window_end: datetime,
    claim_time: datetime,
) -> list[Appointment]:
    """Atomically claim appointments in the 23-25h window for reminder dispatch.

    Uses a single UPDATE ... WHERE reminder_sent_at IS NULL RETURNING to
    atomically claim rows before any notification is sent. This prevents
    duplicate dispatches when multiple workers trigger simultaneously.

    Args:
        session: Database session.
        window_start: Start of the 23-25 hour window (inclusive).
        window_end: End of the 23-25 hour window (inclusive).
        claim_time: Timestamp to set as reminder_sent_at (timezone-aware UTC).

    Returns:
        List of claimed appointments with patient, dentist, and service eager-loaded.
    """
    # Atomic claim: UPDATE with WHERE reminder_sent_at IS NULL and RETURNING
    # This ensures only one worker can claim each appointment
    # First, claim the appointments by setting reminder_sent_at
    update_stmt = (
        update(Appointment)
        .where(
            Appointment.status.in_(["SCHEDULED", "CONFIRMED"]),
            Appointment.reminder_sent_at.is_(None),
            Appointment.start_time >= window_start,
            Appointment.start_time <= window_end,
        )
        .values(reminder_sent_at=claim_time)
        .returning(Appointment.id)
    )
    update_result = await session.execute(update_stmt)
    claimed_ids: list[UUID] = [row[0] for row in update_result.fetchall()]

    if not claimed_ids:
        return []

    # Fetch the claimed appointments with eager-loaded relations
    select_stmt = (
        select(Appointment)
        .where(Appointment.id.in_(claimed_ids))
        .options(
            joinedload(Appointment.patient),
            joinedload(Appointment.dentist),
            joinedload(Appointment.service),
        )
    )
    select_result = await session.scalars(select_stmt)
    return list(select_result.unique().all())


# ---------------------------------------------------------------------------
# Audit log repository functions (Spec 05 §3 — Layer 2)
# ---------------------------------------------------------------------------


async def create_audit_log(
    session: AsyncSession,
    *,
    appointment_id: UUID,
    actor_id: UUID,
    from_status: str | None,
    to_status: str | None,
    old_start_time: datetime | None,
    new_start_time: datetime | None,
    note: str | None,
) -> AppointmentAuditLog:
    """Insert a new audit log record and return the persisted object.

    This function is append-only — no update or delete operations are provided
    to maintain audit log immutability (NFR-4).
    """
    audit_log = AppointmentAuditLog(
        appointment_id=appointment_id,
        actor_id=actor_id,
        from_status=from_status,
        to_status=to_status,
        old_start_time=old_start_time,
        new_start_time=new_start_time,
        note=note,
    )
    session.add(audit_log)
    await session.flush()
    await session.refresh(audit_log)
    return audit_log


async def list_audit_logs_for_appointment(
    session: AsyncSession, appointment_id: UUID
) -> list[AppointmentAuditLog]:
    """List all audit log entries for an appointment, ordered chronologically.

    Uses joinedload to eager-load the actor (staff) relationship to avoid N+1
    query overhead (Spec 05 §3 — Eager-Loading Strategy).
    """
    stmt = (
        select(AppointmentAuditLog)
        .options(joinedload(AppointmentAuditLog.actor))
        .where(AppointmentAuditLog.appointment_id == appointment_id)
        .order_by(AppointmentAuditLog.created_at)
    )
    result = await session.execute(stmt)
    return list(result.unique().scalars().all())
