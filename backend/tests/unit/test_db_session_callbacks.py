"""Tests for the transaction callback seam used by T-011 live events."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from app.api import deps


class FakeSession:
    """Small async-session fake exposing only the dependency's contract."""

    def __init__(self, fail_commit: bool = False) -> None:
        self.info: dict[str, Any] = {}
        self.fail_commit = fail_commit
        self.rolled_back = False
        self.closed = False

    async def commit(self) -> None:
        if self.fail_commit:
            raise RuntimeError("commit failed")

    async def rollback(self) -> None:
        self.rolled_back = True

    async def close(self) -> None:
        self.closed = True


async def test_post_commit_callbacks_run_after_successful_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()
    monkeypatch.setattr(deps, "SessionLocal", lambda: session)
    published: list[bool] = []

    async def publish() -> None:
        published.append(True)

    generator = deps.get_db_session()
    yielded_session = await anext(generator)
    assert yielded_session is session
    callbacks: list[Callable[[], Awaitable[None]]] = yielded_session.info.setdefault(
        "after_commit_callbacks", []
    )
    callbacks.append(publish)

    with pytest.raises(StopAsyncIteration):
        await anext(generator)

    assert published == [True]
    assert session.closed is True
    assert session.rolled_back is False


async def test_post_commit_callbacks_do_not_run_when_commit_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession(fail_commit=True)
    monkeypatch.setattr(deps, "SessionLocal", lambda: session)
    published: list[bool] = []

    async def publish() -> None:
        published.append(True)

    generator = deps.get_db_session()
    yielded_session = await anext(generator)
    callbacks: list[Callable[[], Awaitable[None]]] = yielded_session.info.setdefault(
        "after_commit_callbacks", []
    )
    callbacks.append(publish)

    with pytest.raises(RuntimeError, match="commit failed"):
        await anext(generator)

    assert published == []
    assert session.rolled_back is True
    assert session.closed is True
