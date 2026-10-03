"""Health endpoint — Architecture §4 (cross-cutting) / §5 (test seams).

Expected value: ``{"status": "ok"}`` with a ``X-Correlation-ID`` response header.
"""

from __future__ import annotations

from httpx import AsyncClient


async def test_health_check_returns_200_and_correlation_id(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Correlation-ID" in response.headers
