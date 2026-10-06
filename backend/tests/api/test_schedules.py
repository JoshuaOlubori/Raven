"""Schedule management API tests (Spec 04 §4 — Layer 3, PRD R-7, R-8).

Each test drives the public HTTP seam (``AsyncClient``) with expected values
drawn from the PRD and spec, never from the implementation under test.
"""

from __future__ import annotations

from httpx import AsyncClient

from app.models.staff import Staff

# ---------------------------------------------------------------------------
# AC1 — Working shift creation (R-7)
# ---------------------------------------------------------------------------


async def test_admin_creates_working_shift_201(
    admin_staff: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """R-7: Admin creates a working shift → 201, correct day and times."""
    headers = auth_headers(admin_staff.id, admin_staff.role)

    response = await client.post(
        "/api/v1/schedules/shifts",
        headers=headers,
        json={
            "dentistId": str(admin_staff.id),
            "dayOfWeek": 0,  # Monday
            "startTime": "09:00:00",
            "endTime": "17:00:00",
        },
    )

    if response.status_code != 201:
        print(f"Response: {response.status_code} {response.json()}")
    assert response.status_code == 201
    body = response.json()
    assert body["dayOfWeek"] == 0
    assert body["startTime"] == "09:00:00"
    assert body["endTime"] == "17:00:00"
    assert body["dentistId"] == str(admin_staff.id)
    assert "id" in body


# ---------------------------------------------------------------------------
# AC2 — Shift validation (422) - covered by schema unit tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# AC3 — Overlapping shift rejection (409)
# ---------------------------------------------------------------------------


async def test_duplicate_or_overlapping_shift_returns_409(
    admin_staff: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """Spec 04 §7: Overlapping shift for same dentist on same day
    → 409 SHIFT_OVERLAP.
    """
    headers = auth_headers(admin_staff.id, admin_staff.role)

    # Create first shift
    response1 = await client.post(
        "/api/v1/schedules/shifts",
        headers=headers,
        json={
            "dentistId": str(admin_staff.id),
            "dayOfWeek": 0,  # Monday
            "startTime": "09:00:00",
            "endTime": "13:00:00",
        },
    )
    assert response1.status_code == 201

    # Try to create overlapping shift (09:00-13:00 overlaps with 09:00-13:00)
    response2 = await client.post(
        "/api/v1/schedules/shifts",
        headers=headers,
        json={
            "dentistId": str(admin_staff.id),
            "dayOfWeek": 0,  # Monday
            "startTime": "11:00:00",
            "endTime": "15:00:00",
        },
    )

    assert response2.status_code == 409
    body = response2.json()
    assert body["error"] == "SHIFT_OVERLAP"


async def test_non_overlapping_shift_same_day_allowed(
    admin_staff: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """Non-overlapping shifts on the same day should be allowed."""
    headers = auth_headers(admin_staff.id, admin_staff.role)

    # Create first shift: 09:00-13:00
    response1 = await client.post(
        "/api/v1/schedules/shifts",
        headers=headers,
        json={
            "dentistId": str(admin_staff.id),
            "dayOfWeek": 0,
            "startTime": "09:00:00",
            "endTime": "13:00:00",
        },
    )
    assert response1.status_code == 201

    # Create second shift: 13:00-17:00 (adjacent, not overlapping)
    response2 = await client.post(
        "/api/v1/schedules/shifts",
        headers=headers,
        json={
            "dentistId": str(admin_staff.id),
            "dayOfWeek": 0,
            "startTime": "13:00:00",
            "endTime": "17:00:00",
        },
    )
    assert response2.status_code == 201


# ---------------------------------------------------------------------------
# AC4 — Time-off block creation (R-8)
# ---------------------------------------------------------------------------


async def test_dentist_creates_own_time_off_201(
    dentist_staff: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """R-8: Dentist creates own time-off block → 201, reason saved."""
    headers = auth_headers(dentist_staff.id, dentist_staff.role)

    response = await client.post(
        "/api/v1/schedules/time-off",
        headers=headers,
        json={
            "dentistId": str(dentist_staff.id),
            "startTime": "2026-07-15T09:00:00Z",
            "endTime": "2026-07-15T17:00:00Z",
            "reason": "Vacation",
        },
    )

    if response.status_code != 201:
        print(f"Response: {response.status_code} {response.json()}")
    else:
        print(f"Success Response: {response.json()}")
    assert response.status_code == 201
    body = response.json()
    assert body["reason"] == "Vacation"
    assert body["dentistId"] == str(dentist_staff.id)
    assert "id" in body
    assert "createdAt" in body


# ---------------------------------------------------------------------------
# AC5 — Time-off block authorization (403)
# ---------------------------------------------------------------------------


async def test_dentist_cannot_modify_peer_time_off_403(
    dentist_staff: Staff,
    dentist_staff_2: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """Spec 04 §4: Dentist cannot create time-off for another dentist
    → 403 SCHEDULE_FORBIDDEN.
    """
    headers = auth_headers(dentist_staff.id, dentist_staff.role)

    response = await client.post(
        "/api/v1/schedules/time-off",
        headers=headers,
        json={
            "dentistId": str(dentist_staff_2.id),  # Different dentist!
            "startTime": "2026-07-15T09:00:00Z",
            "endTime": "2026-07-15T17:00:00Z",
            "reason": "Vacation",
        },
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error"] == "SCHEDULE_FORBIDDEN"


async def test_dentist_cannot_delete_peer_time_off_403(
    dentist_staff: Staff,
    dentist_staff_2: Staff,
    admin_staff: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """Spec 04 §4: Dentist cannot delete another dentist's time-off block → 403."""
    admin_headers = auth_headers(admin_staff.id, admin_staff.role)
    dentist_headers = auth_headers(dentist_staff.id, dentist_staff.role)

    # Admin creates time-off for dentist_2
    create_resp = await client.post(
        "/api/v1/schedules/time-off",
        headers=admin_headers,
        json={
            "dentistId": str(dentist_staff_2.id),
            "startTime": "2026-07-15T09:00:00Z",
            "endTime": "2026-07-15T17:00:00Z",
            "reason": "Vacation",
        },
    )
    assert create_resp.status_code == 201
    block_id = create_resp.json()["id"]

    # Dentist tries to delete it
    delete_resp = await client.delete(
        f"/api/v1/schedules/time-off/{block_id}",
        headers=dentist_headers,
    )

    assert delete_resp.status_code == 403
    body = delete_resp.json()
    assert body["error"] == "SCHEDULE_FORBIDDEN"


# ---------------------------------------------------------------------------
# Additional tests for list endpoints
# ---------------------------------------------------------------------------


async def test_list_shifts_returns_all(
    admin_staff: Staff,
    dentist_staff: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """GET /shifts returns all shifts for all dentists."""
    admin_headers = auth_headers(admin_staff.id, admin_staff.role)
    dentist_headers = auth_headers(dentist_staff.id, dentist_staff.role)

    # Create shifts for both dentists
    await client.post(
        "/api/v1/schedules/shifts",
        headers=admin_headers,
        json={
            "dentistId": str(admin_staff.id),
            "dayOfWeek": 0,
            "startTime": "09:00:00",
            "endTime": "17:00:00",
        },
    )
    await client.post(
        "/api/v1/schedules/shifts",
        headers=admin_headers,
        json={
            "dentistId": str(dentist_staff.id),
            "dayOfWeek": 1,
            "startTime": "10:00:00",
            "endTime": "18:00:00",
        },
    )

    # List all shifts
    response = await client.get(
        "/api/v1/schedules/shifts",
        headers=dentist_headers,
    )
    print(f"List shifts response: {response.status_code} {response.json()}")
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 2


async def test_list_time_off_returns_blocks(
    dentist_staff: Staff,
    admin_staff: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """GET /time-off returns time-off blocks for a dentist within a range."""
    admin_headers = auth_headers(admin_staff.id, admin_staff.role)
    dentist_headers = auth_headers(dentist_staff.id, dentist_staff.role)

    # Create time-off block
    await client.post(
        "/api/v1/schedules/time-off",
        headers=admin_headers,
        json={
            "dentistId": str(dentist_staff.id),
            "startTime": "2026-07-15T09:00:00Z",
            "endTime": "2026-07-15T17:00:00Z",
            "reason": "Vacation",
        },
    )

    # List time-off blocks
    response = await client.get(
        "/api/v1/schedules/time-off",
        headers=dentist_headers,
        params={
            "dentistId": str(dentist_staff.id),
            "startDate": "2026-07-14",
            "endDate": "2026-07-16",
        },
    )
    print(f"List time-off response: {response.status_code} {response.json()}")
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert body[0]["reason"] == "Vacation"


async def test_delete_shift_204(
    admin_staff: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """DELETE /shifts/{id} removes shift → 204."""
    headers = auth_headers(admin_staff.id, admin_staff.role)

    # Create shift
    create_resp = await client.post(
        "/api/v1/schedules/shifts",
        headers=headers,
        json={
            "dentistId": str(admin_staff.id),
            "dayOfWeek": 0,
            "startTime": "09:00:00",
            "endTime": "17:00:00",
        },
    )
    assert create_resp.status_code == 201
    shift_id = create_resp.json()["id"]

    # Delete shift
    delete_resp = await client.delete(
        f"/api/v1/schedules/shifts/{shift_id}",
        headers=headers,
    )
    assert delete_resp.status_code == 204

    # Verify it's gone
    list_resp = await client.get(
        "/api/v1/schedules/shifts",
        headers=headers,
        params={"dentistId": str(admin_staff.id)},
    )
    assert list_resp.status_code == 200
    shifts = list_resp.json()
    assert not any(s["id"] == shift_id for s in shifts)


async def test_delete_time_off_204(
    dentist_staff: Staff,
    auth_headers: callable,
    client: AsyncClient,
) -> None:
    """DELETE /time-off/{id} removes block → 204."""
    headers = auth_headers(dentist_staff.id, dentist_staff.role)

    # Create time-off block
    create_resp = await client.post(
        "/api/v1/schedules/time-off",
        headers=headers,
        json={
            "dentistId": str(dentist_staff.id),
            "startTime": "2026-07-15T09:00:00Z",
            "endTime": "2026-07-15T17:00:00Z",
            "reason": "Vacation",
        },
    )
    assert create_resp.status_code == 201
    block_id = create_resp.json()["id"]

    # Delete time-off block
    delete_resp = await client.delete(
        f"/api/v1/schedules/time-off/{block_id}",
        headers=headers,
    )
    assert delete_resp.status_code == 204

    # Verify it's gone
    list_resp = await client.get(
        "/api/v1/schedules/time-off",
        headers=headers,
        params={
            "dentistId": str(dentist_staff.id),
            "startDate": "2026-07-14",
            "endDate": "2026-07-16",
        },
    )
    assert list_resp.status_code == 200
    blocks = list_resp.json()
    assert not any(b["id"] == block_id for b in blocks)


# ---------------------------------------------------------------------------
# Unauthenticated access (NFR-6)
# ---------------------------------------------------------------------------


async def test_unauthenticated_shifts_rejected_401(
    client: AsyncClient,
) -> None:
    """Unauthenticated request to shifts endpoint → 401."""
    response = await client.get("/api/v1/schedules/shifts")
    assert response.status_code == 401


async def test_unauthenticated_time_off_rejected_401(
    client: AsyncClient,
) -> None:
    """Unauthenticated request to time-off endpoint → 401."""
    response = await client.get("/api/v1/schedules/time-off")
    assert response.status_code == 401
