"""Authentication endpoint tests (PRD R-1, Spec 01 §7).

Each test drives the public HTTP seam (``AsyncClient``) with expected values
drawn from the PRD and spec, never from the implementation under test.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from httpx import AsyncClient

from app.models.staff import Staff


async def test_login_success_returns_jwt_token(
    test_staff: tuple[Staff, str],
    client: AsyncClient,
) -> None:
    """R-1: valid credentials → 200 with a bearer JWT and role."""
    staff, password = test_staff

    response = await client.post(
        "/api/v1/auth/token",
        json={"username": staff.email, "password": password},
    )

    assert response.status_code == 200
    body = response.json()
    assert "accessToken" in body
    assert body["tokenType"] == "bearer"
    assert body["role"] == "DENTIST"


async def test_login_invalid_password_returns_401(
    test_staff: tuple[Staff, str],
    client: AsyncClient,
) -> None:
    """R-1: wrong password → 401 AUTH_INVALID_CREDENTIALS."""
    staff, _ = test_staff

    response = await client.post(
        "/api/v1/auth/token",
        json={"username": staff.email, "password": "WrongPassword123"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"] == "AUTH_INVALID_CREDENTIALS"


async def test_login_inactive_user_returns_401(
    inactive_test_staff: tuple[Staff, str],
    client: AsyncClient,
) -> None:
    """R-1: inactive account → 401 AUTH_INACTIVE_ACCOUNT."""
    staff, password = inactive_test_staff

    response = await client.post(
        "/api/v1/auth/token",
        json={"username": staff.email, "password": password},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"] == "AUTH_INACTIVE_ACCOUNT"


async def test_auth_me_returns_current_user_profile(
    test_staff: tuple[Staff, str],
    auth_headers: Callable[[UUID, str], dict[str, str]],
    client: AsyncClient,
) -> None:
    """R-1: valid Bearer token → 200 with the authenticated staff profile."""
    staff, _ = test_staff
    headers = auth_headers(staff.id, staff.role)

    response = await client.get("/api/v1/auth/me", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == staff.email
    assert body["role"] == staff.role
