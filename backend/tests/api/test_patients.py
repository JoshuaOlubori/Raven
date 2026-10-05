"""Patient management API tests (PRD R-3, R-4, R-5, NFR-6; Spec 02 §4).

Each test drives the public HTTP seam (``AsyncClient``) with expected values
drawn from the PRD and spec, never from the implementation under test.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from httpx import AsyncClient

from app.models.staff import Staff

# ---------------------------------------------------------------------------
# AC1 — Patient profile creation (R-3)
# ---------------------------------------------------------------------------


async def test_create_patient_success_201(
    receptionist_staff: Staff,
    auth_headers: Callable[[UUID, str], dict[str, str]],
    client: AsyncClient,
) -> None:
    """R-3: receptionist creates a patient → 201, computed fullName, medicalAlerts."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)

    response = await client.post(
        "/api/v1/patients/",
        headers=headers,
        json={
            "firstName": "Jane",
            "lastName": "Doe",
            "dateOfBirth": "2000-01-15",
            "phone": "555-123-4567",
            "medicalAlerts": "Penicillin allergy",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["fullName"] == "Jane Doe"
    assert body["medicalAlerts"] == "Penicillin allergy"


# ---------------------------------------------------------------------------
# AC2 — DOB / phone validation (422)
# ---------------------------------------------------------------------------


async def test_invalid_phone_rejected_422(
    admin_staff: Staff,
    auth_headers: Callable[[UUID, str], dict[str, str]],
    client: AsyncClient,
) -> None:
    """Spec 02 §2: phone not matching pattern → 422."""
    headers = auth_headers(admin_staff.id, admin_staff.role)

    response = await client.post(
        "/api/v1/patients/",
        headers=headers,
        json={
            "firstName": "Jane",
            "lastName": "Doe",
            "dateOfBirth": "2000-01-15",
            "phone": "not-a-phone-number-with-letters",
        },
    )

    assert response.status_code == 422


async def test_create_patient_missing_phone_422(
    admin_staff: Staff,
    auth_headers: Callable[[UUID, str], dict[str, str]],
    client: AsyncClient,
) -> None:
    """Spec 02 §2 / PRD R-3: missing mandatory phone → 422."""
    headers = auth_headers(admin_staff.id, admin_staff.role)

    response = await client.post(
        "/api/v1/patients/",
        headers=headers,
        json={
            "firstName": "Jane",
            "lastName": "Doe",
            "dateOfBirth": "2000-01-15",
            # phone intentionally omitted
        },
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# AC3 — Patient search (R-4)
# ---------------------------------------------------------------------------


async def test_search_patients_by_name_and_phone(
    admin_staff: Staff,
    auth_headers: Callable[[UUID, str], dict[str, str]],
    client: AsyncClient,
) -> None:
    """R-4: case-insensitive partial name & phone search with pagination metadata."""
    headers = auth_headers(admin_staff.id, admin_staff.role)

    # Create two patients — one matching "smith" by last name, one by phone.
    create_a = await client.post(
        "/api/v1/patients/",
        headers=headers,
        json={
            "firstName": "John",
            "lastName": "Smith",
            "dateOfBirth": "1990-03-10",
            "phone": "555-111-2222",
        },
    )
    assert create_a.status_code == 201

    create_b = await client.post(
        "/api/v1/patients/",
        headers=headers,
        json={
            "firstName": "Jane",
            "lastName": "Doe",
            "dateOfBirth": "1985-07-20",
            "phone": "555-999-0000",
        },
    )
    assert create_b.status_code == 201
    jane_id = create_b.json()["id"]

    # Search by last name substring
    search_name = await client.get(
        "/api/v1/patients/",
        headers=headers,
        params={"search": "smith"},
    )
    assert search_name.status_code == 200
    name_body = search_name.json()
    assert name_body["total"] >= 1
    assert len(name_body["items"]) >= 1
    assert name_body["page"] == 1
    assert name_body["size"] == 50
    assert name_body["pages"] >= 1

    # Search by phone substring — should find Jane Doe
    search_phone = await client.get(
        "/api/v1/patients/",
        headers=headers,
        params={"search": "999"},
    )
    assert search_phone.status_code == 200
    phone_body = search_phone.json()
    assert phone_body["total"] >= 1
    found_ids = [item["id"] for item in phone_body["items"]]
    assert jane_id in found_ids


# ---------------------------------------------------------------------------
# AC4 — Soft deletion (R-5)
# ---------------------------------------------------------------------------


async def test_soft_delete_patient_sets_inactive(
    receptionist_staff: Staff,
    auth_headers: Callable[[UUID, str], dict[str, str]],
    client: AsyncClient,
) -> None:
    """R-5: DELETE marks patient inactive (204); excluded from default search."""
    headers = auth_headers(receptionist_staff.id, receptionist_staff.role)

    # Create a patient
    create_resp = await client.post(
        "/api/v1/patients/",
        headers=headers,
        json={
            "firstName": "Jane",
            "lastName": "Doe",
            "dateOfBirth": "2000-01-15",
            "phone": "555-123-4567",
        },
    )
    assert create_resp.status_code == 201
    patient_id = create_resp.json()["id"]

    # Soft delete
    delete_resp = await client.delete(
        f"/api/v1/patients/{patient_id}",
        headers=headers,
    )
    assert delete_resp.status_code == 204

    # Default search should not include the soft-deleted patient
    search_resp = await client.get(
        "/api/v1/patients/",
        headers=headers,
        params={"search": "Doe"},
    )
    assert search_resp.status_code == 200
    search_body = search_resp.json()
    found_ids = [item["id"] for item in search_body["items"]]
    assert patient_id not in found_ids


# ---------------------------------------------------------------------------
# AC5 — Unauthenticated access (NFR-6)
# ---------------------------------------------------------------------------


async def test_unauthenticated_request_rejected_401(
    client: AsyncClient,
) -> None:
    """NFR-6: unauthenticated request to patients endpoint → 401."""
    response = await client.get("/api/v1/patients/")

    assert response.status_code == 401
