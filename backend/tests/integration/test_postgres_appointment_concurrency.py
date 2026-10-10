"""PostgreSQL integration tests for T-014's cross-worker overlap guard."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api import deps
from app.models import Base, DentalService, Patient, Staff, WorkingShift
from app.models.appointment import Appointment
from app.services import appointment_service

BACKEND_DIR = Path(__file__).resolve().parents[2]


class PostgresTestSettings(BaseSettings):
    """Load the optional integration URL from process env or backend/.env."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str | None = Field(
        default=None, validation_alias="TEST_POSTGRES_DATABASE_URL"
    )


def _asyncpg_test_url(raw_url: str) -> URL:
    """Adapt a libpq-style URL to the asyncpg driver supported by this project."""
    url = make_url(raw_url)
    if url.drivername in {"postgresql", "postgresql+psycopg"}:
        url = url.set(drivername="postgresql+asyncpg")

    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    if sslmode is not None:
        query["ssl"] = sslmode
    return url.set(query=query)


TEST_POSTGRES_DATABASE_URL = PostgresTestSettings().database_url
ASYNC_TEST_POSTGRES_URL = (
    _asyncpg_test_url(TEST_POSTGRES_DATABASE_URL)
    if TEST_POSTGRES_DATABASE_URL
    else None
)


@pytest.fixture
async def postgres_sessions(monkeypatch: pytest.MonkeyPatch):
    """Create an isolated schema so the test never touches shared test data."""
    if not TEST_POSTGRES_DATABASE_URL:
        pytest.skip("Set TEST_POSTGRES_DATABASE_URL to an isolated PostgreSQL database")

    schema = f"test_t014_{uuid4().hex}"
    assert ASYNC_TEST_POSTGRES_URL is not None
    admin_engine = create_async_engine(ASYNC_TEST_POSTGRES_URL)
    async with admin_engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    engine = create_async_engine(
        ASYNC_TEST_POSTGRES_URL,
        connect_args={"server_settings": {"search_path": schema}},
    )
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        session_local = async_sessionmaker(engine, expire_on_commit=False)
        monkeypatch.setattr(deps, "SessionLocal", session_local)
        yield session_local
    finally:
        await engine.dispose()
        async with admin_engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin_engine.dispose()


async def _seed_scheduling_data(session_local):
    async with session_local() as session:
        receptionist = Staff(
            email=f"reception-{uuid4().hex}@example.com",
            hashed_password="unused",
            full_name="Receptionist",
            role="RECEPTIONIST",
            is_active=True,
        )
        dentist = Staff(
            email=f"dentist-{uuid4().hex}@example.com",
            hashed_password="unused",
            full_name="Dr. Dentist",
            role="DENTIST",
            is_active=True,
        )
        patient = Patient(
            first_name="Jane",
            last_name="Patient",
            date_of_birth=date(1990, 1, 1),
            phone="+15551234567",
            is_active=True,
        )
        service = DentalService(
            name=f"Cleaning {uuid4().hex}", duration_minutes=45, is_active=True
        )
        session.add_all([receptionist, dentist, patient, service])
        await session.flush()
        session.add(
            WorkingShift(
                dentist_id=dentist.id,
                day_of_week=0,
                start_time=time(9, 0),
                end_time=time(12, 0),
            )
        )
        await session.commit()
        return receptionist, dentist, patient, service


def _request_time(hour: int, minute: int = 0) -> str:
    return datetime(
        2026, 10, 12, hour, minute, tzinfo=ZoneInfo("America/New_York")
    ).isoformat()


def _synchronize_slot_locks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Let both independent requests reach the database lock together."""
    original = appointment_service.lock_dentist_appointment_schedule
    both_arrived = asyncio.Event()
    arrivals = 0
    arrivals_lock = asyncio.Lock()

    async def synchronized_lock(*args, **kwargs):
        nonlocal arrivals
        async with arrivals_lock:
            arrivals += 1
            if arrivals == 2:
                both_arrived.set()
        await asyncio.wait_for(both_arrived.wait(), timeout=10)
        return await original(*args, **kwargs)

    monkeypatch.setattr(
        appointment_service, "lock_dentist_appointment_schedule", synchronized_lock
    )


async def _book(
    client: AsyncClient,
    auth: dict[str, str],
    patient: Patient,
    dentist: Staff,
    service: DentalService,
    start_time: str,
):
    return await client.post(
        "/api/v1/appointments",
        headers=auth,
        json={
            "patientId": str(patient.id),
            "dentistId": str(dentist.id),
            "serviceId": str(service.id),
            "startTime": start_time,
        },
    )


@pytest.mark.skipif(
    not TEST_POSTGRES_DATABASE_URL,
    reason="Set TEST_POSTGRES_DATABASE_URL to run PostgreSQL concurrency tests",
)
async def test_concurrent_postgres_bookings_allow_only_one(
    postgres_sessions, client: AsyncClient, auth_headers, monkeypatch
) -> None:
    receptionist, dentist, patient, service = await _seed_scheduling_data(
        postgres_sessions
    )
    _synchronize_slot_locks(monkeypatch)
    auth = auth_headers(receptionist.id, receptionist.role)

    responses = await asyncio.gather(
        _book(client, auth, patient, dentist, service, _request_time(9)),
        _book(client, auth, patient, dentist, service, _request_time(9)),
    )

    assert sorted(response.status_code for response in responses) == [201, 409]
    conflict = next(response for response in responses if response.status_code == 409)
    assert conflict.json()["error"] == "APPOINTMENT_OVERLAP_CONFLICT"


@pytest.mark.skipif(
    not TEST_POSTGRES_DATABASE_URL,
    reason="Set TEST_POSTGRES_DATABASE_URL to run PostgreSQL concurrency tests",
)
async def test_concurrent_postgres_reschedules_allow_only_one(
    postgres_sessions, client: AsyncClient, auth_headers, monkeypatch
) -> None:
    receptionist, dentist, patient, service = await _seed_scheduling_data(
        postgres_sessions
    )
    async with postgres_sessions() as session:
        start = datetime(2026, 10, 12, 13, 0, tzinfo=ZoneInfo("UTC"))
        appointments = [
            Appointment(
                patient_id=patient.id,
                dentist_id=dentist.id,
                service_id=service.id,
                start_time=start + timedelta(hours=offset),
                end_time=start + timedelta(hours=offset, minutes=45),
                status="SCHEDULED",
            )
            for offset in (0, 2)
        ]
        session.add_all(appointments)
        await session.commit()

    _synchronize_slot_locks(monkeypatch)
    auth = auth_headers(receptionist.id, receptionist.role)
    target = {"startTime": _request_time(10)}
    responses = await asyncio.gather(
        *(
            client.post(
                f"/api/v1/appointments/{appointment.id}/reschedule",
                headers=auth,
                json=target,
            )
            for appointment in appointments
        )
    )

    assert sorted(response.status_code for response in responses) == [200, 409]
    async with postgres_sessions() as session:
        rows = list(
            (
                await session.scalars(
                    select(Appointment).where(Appointment.dentist_id == dentist.id)
                )
            ).all()
        )
    assert len(rows) == 2
    rows.sort(key=lambda row: row.start_time)
    assert rows[0].end_time <= rows[1].start_time


@pytest.mark.skipif(
    not TEST_POSTGRES_DATABASE_URL,
    reason="Set TEST_POSTGRES_DATABASE_URL to run PostgreSQL concurrency tests",
)
async def test_adjacent_appointments_can_both_commit(
    postgres_sessions, client: AsyncClient, auth_headers, monkeypatch
) -> None:
    receptionist, dentist, patient, service = await _seed_scheduling_data(
        postgres_sessions
    )
    _synchronize_slot_locks(monkeypatch)
    auth = auth_headers(receptionist.id, receptionist.role)

    responses = await asyncio.gather(
        _book(client, auth, patient, dentist, service, _request_time(9)),
        _book(client, auth, patient, dentist, service, _request_time(9, 45)),
    )

    assert [response.status_code for response in responses] == [201, 201]
