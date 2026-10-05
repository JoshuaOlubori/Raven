"""Dental services catalog API tests (PRD R-6, Spec 03 §4, §7).

Each test drives the public HTTP seam (``AsyncClient``) with expected values
drawn from the PRD and spec, never from the implementation under test.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from httpx import AsyncClient

from app.models.staff import Staff


async def test_admin_creates_dental_service_201(
    admin_staff: Staff,
    auth_headers: Callable[[UUID, str], dict[str, str]],
    client: AsyncClient,
) -> None:
    """R-6: admin creates a dental service → 201, duration 45, is_active True."""
    headers = auth_headers(admin_staff.id, admin_staff.role)

    response = await client.post(
        "/api/v1/services/",
        headers=headers,
        json={
            "name": "Routine Cleaning",
            "durationMinutes": 45,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["durationMinutes"] == 45
    assert body["isActive"] is True


async def test_non_admin_cannot_create_service_403(
    receptionist_staff: Staff,
    auth_headers: Callable[[UUID, str], dict[str, str]],
    client: AsyncClient,
) -> None:
    """Spec 03 §4: non-admin (receptionist) POST /services → 403 Forbidden."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)

    response = await client.post(
        "/api/v1/services/",
        headers=headers,
        json={
            "name": "Cleaning",
            "durationMinutes": 30,
        },
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error"] == "RBAC_FORBIDDEN"
    assert "Insufficient role" in body["message"]


async def test_duplicate_service_name_returns_409(
    admin_staff: Staff,
    auth_headers: Callable[[UUID, str], dict[str, str]],
    client: AsyncClient,
) -> None:
    """Spec 03 §7: duplicate service name → 409 SERVICE_NAME_EXISTS."""
    headers = auth_headers(admin_staff.id, admin_staff.role)
    name = "Deep Cleaning"

    # First creation succeeds (201)
    first = await client.post(
        "/api/v1/services/",
        headers=headers,
        json={"name": name, "durationMinutes": 90},
    )
    assert first.status_code == 201

    # Second creation with same name → 409
    response = await client.post(
        "/api/v1/services/",
        headers=headers,
        json={"name": name, "durationMinutes": 90},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error"] == "SERVICE_NAME_EXISTS"


async def test_list_services_active_filter(
    admin_staff: Staff,
    auth_headers: Callable[[UUID, str], dict[str, str]],
    client: AsyncClient,
) -> None:
    """Spec 03 §4: inactive services excluded when active_only=True."""
    headers = auth_headers(admin_staff.id, admin_staff.role)

    # Create an active service
    create_resp = await client.post(
        "/api/v1/services/",
        headers=headers,
        json={"name": "Active Service", "durationMinutes": 30},
    )
    assert create_resp.status_code == 201
    service_id = create_resp.json()["id"]

    # Deactivate the service via PATCH
    patch_resp = await client.patch(
        f"/api/v1/services/{service_id}",
        headers=headers,
        json={"isActive": False},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["isActive"] is False

    # List with active_only=True — the deactivated service must be excluded
    list_resp = await client.get(
        "/api/v1/services/",
        headers=headers,
        params={"active_only": True},
    )
    assert list_resp.status_code == 200
    body = list_resp.json()
    ids = [item["id"] for item in body]
    assert service_id not in ids
    assert all(item["isActive"] is True for item in body)
