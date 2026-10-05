"""Shared pytest fixtures and test-only application wiring.

Test architecture follows the project's test strategy (Architecture §5):

* ``test_engine``        — session-scoped in-memory SQLite engine (StaticPool)
* ``test_session_local`` — session-scoped async sessionmaker over the test
                            engine, using a ``TrackedAsyncSession`` so tests can
                            prove ``close()`` is invoked; also creates the shared
                            schema + a throwaway lifecycle table.
* ``override_dbsession`` — patches ``app.api.deps.SessionLocal`` to the test
                            maker so the *production* ``get_db_session`` is
                            exercised against the in-memory DB.
* ``client``             — ``httpx.AsyncClient`` over ``ASGITransport`` with
                            ``raise_app_exceptions=False`` so the global 500
                            handler's response is observable.
* ``test_staff``         — persists an active ``Staff`` with known credentials
                            (used by auth API tests).
* ``inactive_test_staff``— persists an inactive ``Staff`` (login rejection).
* ``auth_headers``       — factory generating signed Bearer JWT tokens.

Expected values come from Architecture §4 / §5 and Spec 01, never from the
code under test.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.session import init_db
from app.main import app
from app.models.staff import Staff
from app.services.auth_service import AuthService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_PASSWORD = "SecurePass123!"


# ---------------------------------------------------------------------------
# Test-only endpoint used to exercise the global 500 handler.
# conftest.py is loaded only by pytest, so this does not affect production.
# ---------------------------------------------------------------------------


async def _raise_unhandled() -> None:
    raise RuntimeError("intentional test error")


app.add_api_route("/_test/exception", _raise_unhandled, methods=["GET"])


# ---------------------------------------------------------------------------
# Tracked session: records whether close() was actually invoked, which is the
# observable for "the session is closed" (Standard §4). SQLAlchemy 2.x
# sessions are reusable, so ``is_active`` / post-close execute() do NOT reflect
# close(); an explicit flag is the faithful seam.
# ---------------------------------------------------------------------------


class TrackedAsyncSession(AsyncSession):
    closed_called: bool = False

    async def close(self) -> None:
        self.closed_called = True
        await super().close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_engine() -> AsyncEngine:
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    yield engine


@pytest.fixture(scope="session")
async def test_session_local(test_engine: AsyncEngine) -> async_sessionmaker:
    # Validate that init_db runs against the test engine (creates all model tables).
    await init_db(test_engine)
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS test_lifecycle "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, val TEXT NOT NULL)"
            )
        )
    return async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        class_=TrackedAsyncSession,
    )


@pytest.fixture
def override_dbsession(
    test_session_local: async_sessionmaker, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Point the production ``get_db_session`` at the in-memory test engine."""
    monkeypatch.setattr("app.api.deps.SessionLocal", test_session_local)
    yield


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Staff / auth fixtures (Spec 01 §9 — Test Seams)
# ---------------------------------------------------------------------------


@pytest.fixture
async def test_staff(
    test_session_local: async_sessionmaker,
    override_dbsession: None,
) -> tuple[Staff, str]:
    """Persist an **active** staff member with known credentials.

    Returns ``(staff, plaintext_password)`` so tests can submit the password
    in a login request and assert on the response.
    """
    async with test_session_local() as session:
        auth_service = AuthService(Settings())
        hashed = await auth_service.hash_password(TEST_PASSWORD)
        staff = Staff(
            email=f"active-{uuid.uuid4().hex[:8]}@clinic.com",
            hashed_password=hashed,
            full_name="Dr. Alice Chen",
            role="DENTIST",
            is_active=True,
        )
        session.add(staff)
        await session.commit()
        await session.refresh(staff)
        return staff, TEST_PASSWORD


@pytest.fixture
async def inactive_test_staff(
    test_session_local: async_sessionmaker,
    override_dbsession: None,
) -> tuple[Staff, str]:
    """Persist an **inactive** staff member with known credentials."""
    async with test_session_local() as session:
        auth_service = AuthService(Settings())
        hashed = await auth_service.hash_password(TEST_PASSWORD)
        staff = Staff(
            email=f"inactive-{uuid.uuid4().hex[:8]}@clinic.com",
            hashed_password=hashed,
            full_name="Dr. Inactive Bob",
            role="DENTIST",
            is_active=False,
        )
        session.add(staff)
        await session.commit()
        await session.refresh(staff)
        return staff, TEST_PASSWORD


@pytest.fixture
def auth_headers() -> Callable[[UUID, str], dict[str, str]]:
    """Factory: generate signed Bearer JWT headers for any staff ID / role."""
    settings = Settings()

    def _make(staff_id: UUID, role: str) -> dict[str, str]:
        auth_service = AuthService(settings)
        token = auth_service.create_token(str(staff_id), role)
        return {"Authorization": f"Bearer {token}"}

    return _make


# ---------------------------------------------------------------------------
# RBAC role fixtures — staff records with ADMIN / RECEPTIONIST roles so that
# get_current_user (which resolves the role from the DB) sees the correct value.
# ---------------------------------------------------------------------------


@pytest.fixture
async def admin_staff(
    test_session_local: async_sessionmaker,
    override_dbsession: None,
) -> Staff:
    """Persist an active ADMIN staff member (for RBAC auth headers)."""
    async with test_session_local() as session:
        staff = Staff(
            email=f"admin-{uuid.uuid4().hex[:8]}@clinic.com",
            hashed_password="irrelevant",
            full_name="Admin User",
            role="ADMIN",
            is_active=True,
        )
        session.add(staff)
        await session.commit()
        await session.refresh(staff)
        return staff


@pytest.fixture
async def receptionist_staff(
    test_session_local: async_sessionmaker,
    override_dbsession: None,
) -> Staff:
    """Persist an active RECEPTIONIST staff member (for RBAC auth headers)."""
    async with test_session_local() as session:
        staff = Staff(
            email=f"recep-{uuid.uuid4().hex[:8]}@clinic.com",
            hashed_password="irrelevant",
            full_name="Receptionist User",
            role="RECEPTIONIST",
            is_active=True,
        )
        session.add(staff)
        await session.commit()
        await session.refresh(staff)
        return staff


@pytest.fixture
async def dentist_staff(
    test_session_local: async_sessionmaker,
    override_dbsession: None,
) -> Staff:
    """Persist an active DENTIST staff member (for RBAC auth headers)."""
    async with test_session_local() as session:
        staff = Staff(
            email=f"dentist-{uuid.uuid4().hex[:8]}@clinic.com",
            hashed_password="irrelevant",
            full_name="Dentist User",
            role="DENTIST",
            is_active=True,
        )
        session.add(staff)
        await session.commit()
        await session.refresh(staff)
        return staff
