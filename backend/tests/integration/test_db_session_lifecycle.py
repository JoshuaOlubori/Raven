"""DB session lifecycle — Standard §4 / Acceptance criterion #3.

The production ``get_db_session`` dependency must:
  * commit on the success path,
  * roll back on the exception path,
  * call ``close()`` in ``finally``.

Expected behaviour comes from the FastAPI production-architecture standard §4
(commit on success, rollback on error, always close), not from this code.
"""

from __future__ import annotations

import contextlib

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.deps import get_db_session


async def test_db_session_lifecycle_commits_and_closes(
    test_session_local: async_sessionmaker,
    override_dbsession: None,  # patches SessionLocal to the test engine
) -> None:
    # --- success path: commit happens, session is closed ---
    gen = get_db_session()
    session = await gen.asend(None)
    assert session.is_active

    await session.execute(
        text("INSERT INTO test_lifecycle (val) VALUES ('committed-row')")
    )
    # Resuming past the yield runs commit() + finally(close()); a generator
    # that finishes cleanly signals completion with StopAsyncIteration.
    with contextlib.suppress(StopAsyncIteration):
        await gen.asend(None)

    # close() was invoked by the dependency's finally block (Standard §4).
    assert session.closed_called
    # The committed row is visible to a fresh session.
    async with test_session_local() as verify:
        rows = (await verify.execute(text("SELECT val FROM test_lifecycle"))).fetchall()
    vals = [r[0] for r in rows]
    assert "committed-row" in vals

    # --- exception path: rollback happens, session is closed ---
    gen2 = get_db_session()
    session2 = await gen2.asend(None)
    assert session2.is_active

    await session2.execute(
        text("INSERT INTO test_lifecycle (val) VALUES ('rolled-back-row')")
    )
    # Throw into the suspended generator: rollback + close run, then the
    # original exception propagates.
    with pytest.raises(RuntimeError):
        await gen2.athrow(RuntimeError("boom"))

    assert session2.closed_called
    # The rolled-back row must NOT be visible.
    async with test_session_local() as verify2:
        rows = (
            await verify2.execute(text("SELECT val FROM test_lifecycle"))
        ).fetchall()
    vals = [r[0] for r in rows]
    assert "rolled-back-row" not in vals
