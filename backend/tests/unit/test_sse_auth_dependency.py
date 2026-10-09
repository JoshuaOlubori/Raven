"""Tests that SSE authentication closes its DB session before streaming."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.api import auth


class FakeSession:
    def __init__(self) -> None:
        self.closed = False

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        self.closed = True


class FakeAuthService:
    def __init__(self, session: FakeSession, settings: object) -> None:
        self.session = session
        self.settings = settings

    def decode_token(self, token: str) -> SimpleNamespace:
        assert token == "valid-token"
        return SimpleNamespace(staff_id=str(staff_id))


staff_id = uuid4()


async def test_sse_authentication_session_closes_before_dependency_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()
    staff = SimpleNamespace(
        id=staff_id,
        email="receptionist@example.com",
        full_name="SSE Receptionist",
        role="RECEPTIONIST",
        is_active=True,
        created_at=datetime.now(UTC),
    )

    async def get_staff(_session: FakeSession, _staff_id) -> SimpleNamespace:
        assert _staff_id == staff_id
        return staff

    monkeypatch.setattr(auth, "SessionLocal", lambda: session)
    monkeypatch.setattr(auth, "AuthService", FakeAuthService)
    monkeypatch.setattr(auth, "get_staff_by_id", get_staff)

    user = await auth.get_current_user_for_stream(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token")
    )

    assert user.id == staff_id
    assert session.closed is True
