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
                            handler's response is observable (Starlette's
                            ``ServerErrorMiddleware`` sends the response then
                            re-raises by design).

Expected values come from Architecture §4 / §5, never from the code under test.
"""

from __future__ import annotations

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

from app.db.session import init_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


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
    # Validate that init_db runs against the test engine (Base has no models in T-001).
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
