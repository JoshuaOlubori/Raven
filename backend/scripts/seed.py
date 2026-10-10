#!/usr/bin/env python
"""Database seed script for Dental Clinic Appointment Tracker.

Creates:
- 2 admin users
- 3 dentists
- 2 receptionists
- 6 dental services
- 12 patients
- Working shifts for all dentists (Mon-Fri, 9am-5pm)
- 20 appointments across various statuses
- Time-off blocks for testing availability
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.config import Settings
from app.db.session import SessionLocal
from app.models import (
    Appointment,
    DentalService,
    Patient,
    Staff,
    TimeOffBlock,
    WorkingShift,
)
from app.services.auth_service import AuthService


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CLINIC_TZ = ZoneInfo("America/New_York")
DEFAULT_PASSWORD = "SecurePass123!"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def hash_password(password: str) -> str:
    auth = AuthService(Settings())
    return await auth.hash_password(password)


async def get_or_create_staff(
    session,
    email: str,
    full_name: str,
    role: str,
    is_active: bool = True,
) -> Staff:
    """Create staff if not exists, return existing otherwise."""
    from app.db.repository import get_staff_by_email

    existing = await get_staff_by_email(session, email)
    if existing:
        print(f"  Staff exists: {email}")
        return existing

    hashed = await hash_password(DEFAULT_PASSWORD)
    staff = Staff(
        email=email,
        hashed_password=hashed,
        full_name=full_name,
        role=role,
        is_active=is_active,
    )
    session.add(staff)
    await session.flush()
    print(f"  Created staff: {email} ({role})")
    return staff


# ---------------------------------------------------------------------------
# Seed Functions
# ---------------------------------------------------------------------------
async def seed_staff(session) -> dict[str, Staff]:
    """Create admin, dentist, and receptionist users."""
    print("\n=== Seeding Staff ===")

    # Admins
    admin1 = await get_or_create_staff(session, "admin@clinic.com", "Dr. Admin One", "ADMIN")
    admin2 = await get_or_create_staff(session, "admin2@clinic.com", "Dr. Admin Two", "ADMIN")

    # Dentists
    dentist1 = await get_or_create_staff(session, "dr.smith@clinic.com", "Dr. Sarah Smith", "DENTIST")
    dentist2 = await get_or_create_staff(session, "dr.jones@clinic.com", "Dr. Michael Jones", "DENTIST")
    dentist3 = await get_or_create_staff(session, "dr.lee@clinic.com", "Dr. Emily Lee", "DENTIST")

    # Receptionists
    recep1 = await get_or_create_staff(session, "recep@clinic.com", "Jane Reception", "RECEPTIONIST")
    recep2 = await get_or_create_staff(session, "recep2@clinic.com", "John Reception", "RECEPTIONIST")

    await session.commit()
    return {
        "admin1": admin1,
        "admin2": admin2,
        "dentist1": dentist1,
        "dentist2": dentist2,
        "dentist3": dentist3,
        "recep1": recep1,
        "recep2": recep2,
    }


async def seed_services(session) -> list[DentalService]:
    """Create dental services catalog."""
    print("\n=== Seeding Services ===")

    services_data = [
        ("Comprehensive Exam", 45, "Full oral examination with X-rays"),
        ("Cleaning (Prophylaxis)", 30, "Routine dental cleaning"),
        ("Deep Cleaning (Scaling & Root Planing)", 60, "Periodontal therapy per quadrant"),
        ("Composite Filling", 45, "Tooth-colored filling (1 surface)"),
        ("Crown (Porcelain)", 90, "Single-visit CEREC crown"),
        ("Root Canal (Molar)", 90, "Endodontic therapy"),
        ("Extraction (Simple)", 30, "Simple tooth removal"),
        ("Extraction (Surgical)", 60, "Surgical extraction"),
        ("Teeth Whitening (In-Office)", 60, "Professional bleaching"),
        ("Night Guard", 30, "Custom occlusal guard impressions"),
    ]

    services = []
    for name, duration, desc in services_data:
        from app.db.repository import get_service_by_name
        existing = await get_service_by_name(session, name)
        if existing:
            print(f"  Service exists: {name}")
            services.append(existing)
            continue

        service = DentalService(
            name=name,
            description=desc,
            duration_minutes=duration,
            is_active=True,
        )
        session.add(service)
        services.append(service)
        print(f"  Created service: {name} ({duration} min)")

    await session.commit()
    return services


async def seed_patients(session) -> list[Patient]:
    """Create sample patients."""
    print("\n=== Seeding Patients ===")

    patients_data = [
        ("John", "Doe", "1985-03-15", "+1-555-0101", "john.doe@email.com", "Jane Doe", "+1-555-0102", "Penicillin allergy"),
        ("Mary", "Johnson", "1992-07-22", "+1-555-0201", "mary.j@email.com", "Robert Johnson", "+1-555-0202", None),
        ("Robert", "Williams", "1978-11-05", "+1-555-0301", "rob.williams@email.com", "Lisa Williams", "+1-555-0302", "High blood pressure"),
        ("Jennifer", "Brown", "1995-01-30", "+1-555-0401", "jen.brown@email.com", "Mark Brown", "+1-555-0402", None),
        ("Michael", "Davis", "1980-09-12", "+1-555-0501", "mike.davis@email.com", "Sarah Davis", "+1-555-0502", "Diabetes Type 2"),
        ("Elizabeth", "Miller", "2000-04-18", "+1-555-0601", "liz.miller@email.com", "James Miller", "+1-555-0602", None),
        ("David", "Wilson", "1972-12-03", "+1-555-0701", "david.wilson@email.com", "Patricia Wilson", "+1-555-0702", "Latex allergy"),
        ("Susan", "Moore", "1988-06-25", "+1-555-0801", "susan.moore@email.com", "Thomas Moore", "+1-555-0802", None),
        ("James", "Taylor", "1993-08-14", "+1-555-0901", "james.taylor@email.com", "Emily Taylor", "+1-555-0902", "Asthma"),
        ("Karen", "Anderson", "1983-02-28", "+1-555-1001", "karen.anderson@email.com", "John Anderson", "+1-555-1002", None),
        ("Christopher", "Thomas", "1975-10-11", "+1-555-1101", "chris.thomas@email.com", "Maria Thomas", "+1-555-1102", "Heart condition"),
        ("Lisa", "Jackson", "1990-05-07", "+1-555-1201", "lisa.jackson@email.com", "David Jackson", "+1-555-1202", None),
    ]

    patients = []
    for first, last, dob, phone, email, ec_name, ec_phone, alerts in patients_data:
        patient = Patient(
            first_name=first,
            last_name=last,
            date_of_birth=date.fromisoformat(dob),
            phone=phone,
            email=email,
            emergency_contact_name=ec_name,
            emergency_contact_phone=ec_phone,
            medical_alerts=alerts,
            is_active=True,
        )
        session.add(patient)
        patients.append(patient)
        print(f"  Created patient: {first} {last}")

    await session.commit()
    return patients


async def seed_shifts(session, staff: dict) -> list[WorkingShift]:
    """Create weekly working shifts for all dentists (Mon-Fri 9am-5pm)."""
    print("\n=== Seeding Working Shifts ===")

    dentists = [staff["dentist1"], staff["dentist2"], staff["dentist3"]]
    shifts = []

    for dentist in dentists:
        for day in range(5):  # Mon-Fri (0-4)
            # Check if shift already exists
            from sqlalchemy import select
            existing = await session.execute(
                select(WorkingShift).where(
                    WorkingShift.dentist_id == dentist.id,
                    WorkingShift.day_of_week == day,
                )
            )
            if existing.scalar_one_or_none():
                print(f"  Shift exists: {dentist.full_name} - Day {day}")
                continue

            shift = WorkingShift(
                dentist_id=dentist.id,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(17, 0),
            )
            session.add(shift)
            shifts.append(shift)
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri"]
            print(f"  Created shift: {dentist.full_name} - {day_names[day]} 9:00-17:00")

    await session.commit()
    return shifts


async def seed_time_off(session, staff: dict) -> list[TimeOffBlock]:
    """Create time-off blocks for testing availability."""
    print("\n=== Seeding Time-Off Blocks ===")

    time_off_data = [
        (staff["dentist1"], date.today() + timedelta(days=7), date.today() + timedelta(days=9), "Conference"),
        (staff["dentist2"], date.today() + timedelta(days=14), date.today() + timedelta(days=14), "Personal day"),
        (staff["dentist3"], date.today() + timedelta(days=3), date.today() + timedelta(days=5), "Vacation"),
    ]

    blocks = []
    for dentist, start, end, reason in time_off_data:
        block = TimeOffBlock(
            dentist_id=dentist.id,
            start_time=datetime.combine(start, time(0, 0), tzinfo=CLINIC_TZ),
            end_time=datetime.combine(end, time(23, 59), tzinfo=CLINIC_TZ),
            reason=reason,
        )
        session.add(block)
        blocks.append(block)
        print(f"  Created time-off: {dentist.full_name} - {start} to {end} ({reason})")

    await session.commit()
    return blocks


async def seed_appointments(session, staff: dict, patients: list[Patient], services: list[DentalService]) -> list[Appointment]:
    """Create sample appointments across various statuses."""
    print("\n=== Seeding Appointments ===")

    dentists = [staff["dentist1"], staff["dentist2"], staff["dentist3"]]
    service_map = {s.name: s for s in services}

    # Build appointments for the next 2 weeks
    base_date = date.today() + timedelta(days=1)  # Start tomorrow

    appointments_data = [
        # Completed appointments (past)
        (patients[0], dentists[0], service_map["Cleaning (Prophylaxis)"], base_date - timedelta(days=10), time(9, 0), "COMPLETED"),
        (patients[1], dentists[1], service_map["Comprehensive Exam"], base_date - timedelta(days=8), time(10, 30), "COMPLETED"),
        (patients[2], dentists[2], service_map["Composite Filling"], base_date - timedelta(days=5), time(14, 0), "COMPLETED"),

        # No-shows
        (patients[3], dentists[0], service_map["Cleaning (Prophylaxis)"], base_date - timedelta(days=3), time(11, 0), "NO_SHOW"),

        # Cancelled
        (patients[4], dentists[1], service_map["Teeth Whitening (In-Office)"], base_date - timedelta(days=1), time(15, 0), "CANCELLED", "Patient requested"),

        # Today's appointments
        (patients[5], dentists[0], service_map["Comprehensive Exam"], base_date, time(9, 0), "SCHEDULED"),
        (patients[6], dentists[1], service_map["Cleaning (Prophylaxis)"], base_date, time(10, 0), "CONFIRMED"),
        (patients[7], dentists[2], service_map["Composite Filling"], base_date, time(13, 30), "SCHEDULED"),

        # Tomorrow
        (patients[8], dentists[0], service_map["Crown (Porcelain)"], base_date + timedelta(days=1), time(9, 0), "SCHEDULED"),
        (patients[9], dentists[1], service_map["Root Canal (Molar)"], base_date + timedelta(days=1), time(11, 0), "SCHEDULED"),
        (patients[10], dentists[2], service_map["Extraction (Simple)"], base_date + timedelta(days=1), time(14, 0), "SCHEDULED"),

        # Next week
        (patients[11], dentists[0], service_map["Night Guard"], base_date + timedelta(days=3), time(10, 0), "SCHEDULED"),
        (patients[0], dentists[1], service_map["Cleaning (Prophylaxis)"], base_date + timedelta(days=4), time(9, 30), "SCHEDULED"),
        (patients[1], dentists[2], service_map["Deep Cleaning (Scaling & Root Planing)"], base_date + timedelta(days=5), time(13, 0), "SCHEDULED"),
        (patients[2], dentists[0], service_map["Composite Filling"], base_date + timedelta(days=6), time(11, 0), "SCHEDULED"),
        (patients[3], dentists[1], service_map["Crown (Porcelain)"], base_date + timedelta(days=7), time(9, 0), "SCHEDULED"),
        (patients[4], dentists[2], service_map["Extraction (Surgical)"], base_date + timedelta(days=8), time(10, 0), "SCHEDULED"),
        (patients[5], dentists[0], service_map["Teeth Whitening (In-Office)"], base_date + timedelta(days=9), time(14, 0), "SCHEDULED"),
        (patients[6], dentists[1], service_map["Night Guard"], base_date + timedelta(days=10), time(15, 0), "SCHEDULED"),
        (patients[7], dentists[2], service_map["Cleaning (Prophylaxis)"], base_date + timedelta(days=11), time(9, 0), "SCHEDULED"),
    ]

    appointments = []
    for i, appt_data in enumerate(appointments_data):
        patient, dentist, service, appt_date, start_time, status = appt_data[:6]
        cancellation_reason = appt_data[6] if len(appt_data) > 6 else None

        start_dt = datetime.combine(appt_date, start_time, tzinfo=CLINIC_TZ)
        end_dt = start_dt + timedelta(minutes=service.duration_minutes)

        appointment = Appointment(
            patient_id=patient.id,
            dentist_id=dentist.id,
            service_id=service.id,
            start_time=start_dt,
            end_time=end_dt,
            status=status,
            cancellation_reason=cancellation_reason,
        )
        session.add(appointment)
        appointments.append(appointment)
        print(f"  Created appointment: {patient.first_name} {patient.last_name} with {dentist.full_name} on {appt_date} at {start_time} [{status}]")

    await session.commit()
    return appointments


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    print("=" * 60)
    print("Dental Clinic Database Seed")
    print("=" * 60)

    async with SessionLocal() as session:
        # Seed in dependency order
        staff = await seed_staff(session)
        services = await seed_services(session)
        patients = await seed_patients(session)
        await seed_shifts(session, staff)
        await seed_time_off(session, staff)
        await seed_appointments(session, staff, patients, services)

    print("\n" + "=" * 60)
    print("Seed complete!")
    print("=" * 60)
    print("\nLogin credentials (all use password: SecurePass123!)")
    print("  Admins:      admin@clinic.com, admin2@clinic.com")
    print("  Dentists:    dr.smith@clinic.com, dr.jones@clinic.com, dr.lee@clinic.com")
    print("  Receptionists: recep@clinic.com, recep2@clinic.com")
    print("\nTo run: uv run python scripts/seed.py")


if __name__ == "__main__":
    asyncio.run(main())