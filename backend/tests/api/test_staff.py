"""Staff management API tests (PRD R-2, Spec 01 §4, §7).

Each test drives the public HTTP seam (``AsyncClient``) with expected values
drawn from the PRD and spec, never from the implementation under test.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from httpx import AsyncClient

from app.models.staff import Staff


async def test_admin_creates_staff_success_201(
    admin_staff: Staff,
    auth_headers: Callable[[UUID, str], dict[str, str]],
    client: AsyncClient,
) -> None:
    """R-2: admin creates a new DENTIST staff → 201, password hash excluded."""
    headers = auth_headers(admin_staff.id, admin_staff.role)

    response = await client.post(
        "/api/v1/staff/",
        headers=headers,
        json={
            "email": "newdentist@clinic.com",
            "password": "SecurePass123!",
            "fullName": "Dr. New Dentist",
            "role": "DENTIST",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "DENTIST"
    assert "hashed_password" not in body


async def test_receptionist_creating_staff_returns_403(
    receptionist_staff: Staff,
    auth_headers: Callable[[UUID, str], dict[str, str]],
    client: AsyncClient,
) -> None:
    """R-2: receptionist attempts staff creation → 403 Forbidden."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)

    response = await client.post(
        "/api/v1/staff/",
        headers=headers,
        json={
            "email": "newreceptionist@clinic.com",
            "password": "SecurePass123!",
            "fullName": "New Receptionist",
            "role": "RECEPTIONIST",
        },
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error"] == "RBAC_FORBIDDEN"
    assert "Insufficient role" in body["message"]


async def test_create_duplicate_email_returns_409(
    admin_staff: Staff,
    auth_headers: Callable[[UUID, str], dict[str, str]],
    client: AsyncClient,
) -> None:
    """Spec 01 §7: duplicate email → 409 STAFF_EMAIL_EXISTS."""
    headers = auth_headers(admin_staff.id, admin_staff.role)
    email = "duplicate@clinic.com"

    # First creation succeeds (201)
    first = await client.post(
        "/api/v1/staff/",
        headers=headers,
        json={
            "email": email,
            "password": "SecurePass123!",
            "fullName": "First User",
            "role": "DENTIST",
        },
    )
    assert first.status_code == 201

    # Second creation with same email → 409
    response = await client.post(
        "/api/v1/staff/",
        headers=headers,
        json={
            "email": email,
            "password": "SecurePass123!",
            "fullName": "Second User",
            "role": "DENTIST",
        },
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error"] == "STAFF_EMAIL_EXISTS"


async def test_list_staff_filters_by_role(
    admin_staff: Staff,
    test_staff: tuple[Staff, str],
    receptionist_staff: Staff,
    auth_headers: Callable[[UUID, str], dict[str, str]],
    client: AsyncClient,
) -> None:
    """Spec 01 §4: GET /api/v1/staff?role=DENTIST returns only DENTIST staff."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)

    response = await client.get(
        "/api/v1/staff/",
        headers=headers,
        params={"role": "DENTIST"},
    )

    assert response.status_code == 200
    body = response.json()
    # Every returned staff must have the requested role.
    for item in body:
        assert item["role"] == "DENTIST"


async def test_admin_deactivates_staff_member(
    admin_staff: Staff,
    test_staff: tuple[Staff, str],
    auth_headers: Callable[[UUID, str], dict[str, str]],
    client: AsyncClient,
) -> None:
    """Spec 01 §4: admin deactivates a staff member → 200, isActive=False."""
    staff, _ = test_staff
    headers = auth_headers(admin_staff.id, admin_staff.role)

    response = await client.patch(
        f"/api/v1/staff/{staff.id}",
        headers=headers,
        json={"isActive": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["isActive"] is False
