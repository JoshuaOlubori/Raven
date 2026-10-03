"""Global error handler — Architecture §4 (error model).

Every unhandled exception must yield a ``500`` with a standardized body whose
``correlation_id`` matches the ``X-Correlation-ID`` response header. Expected
field names come from Architecture §4.
"""

from __future__ import annotations

from httpx import AsyncClient


async def test_unhandled_exception_returns_500_error_body(client: AsyncClient) -> None:
    response = await client.get("/_test/exception")

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "internal_server_error"
    assert "message" in body and body["message"]
    assert "correlation_id" in body and body["correlation_id"]

    header_cid = response.headers.get("X-Correlation-ID")
    assert header_cid is not None
    assert body["correlation_id"] == header_cid
