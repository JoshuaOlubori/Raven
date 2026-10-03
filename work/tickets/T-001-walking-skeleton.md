---
id: T-001
title: Walking skeleton and test infrastructure
status: todo
mode: AFK
blocked_by: -
spec_refs: specs/00-architecture.md#2-stack-and-versions, specs/00-architecture.md#4-cross-cutting-design, specs/00-architecture.md#5-test-architecture
covers: Architecture §2-§6, CI Gates
updated: 2026-10-03
---

## Outcome
A running FastAPI application bootstrap with configuration management, correlation ID middleware, centralized error handling, async database session lifecycle dependency (`get_db_session`), `/health` endpoint, test fixtures, and passing CI quality gates.

## What to build
- `backend/pyproject.toml`: Add dependencies (`fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `sqlalchemy`, `aiosqlite`, `asyncpg`, `alembic`, `argon2-cffi`, `pyjwt`, `cryptography`, `httpx`, `pytest`, `pytest-asyncio`, `ruff`, `mypy`).
- `src/app/config.py`: Pydantic Settings class with `DATABASE_URL`, `CLINIC_TIMEZONE`, `JWT_SECRET_KEY`, `APP_ENV`.
- `src/app/db/session.py`: Async engine, `SessionLocal(expire_on_commit=False)`, and `init_db()`.
- `src/app/api/deps.py`: `get_db_session` async generator yield dependency and `DbSessionDep` alias.
- `src/app/main.py`: Lifespan context manager (`init_db`), correlation ID & global error handler middleware (`X-Correlation-ID`), `/health` route returning `{"status": "ok"}`.
- `tests/conftest.py`: Async engine, db session fixture with transaction rollback, and `httpx.AsyncClient` test fixture.

## Acceptance criteria
- [ ] Given a running application, When `GET /health` is requested, Then it returns `200 OK` with `{"status": "ok"}` and response header `X-Correlation-ID`.
- [ ] Given any unhandled exception raised in an endpoint, When invoked, Then the global middleware returns `500 Internal Server Error` with JSON body `{"error": "internal_server_error", "correlation_id": "...", "message": "..."}`.
- [ ] Given an active database session dependency, When an endpoint finishes successfully, Then the session commits automatically; When an exception occurs, Then it rolls back.
- [ ] All four quality gates (`ruff check`, `ruff format --check`, `mypy src`, `pytest -q`) execute and pass cleanly.

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | `test_health_check_returns_200_and_correlation_id` | API | status 200, `body["status"] == "ok"`, `X-Correlation-ID` header present | Architecture §4 |
| 2 | `test_unhandled_exception_returns_500_error_body` | API | status 500, `body["error"] == "internal_server_error"`, correlation ID matches header | Architecture §4 |
| 3 | `test_db_session_lifecycle_commits_and_closes` | Repository + DB | transaction commit on exit, closed session | Standard §4 |

## Out of scope
Domain entity models, authentication, patient, service, or appointment endpoints (handled in subsequent tickets).

## Notes for the implementer
Ensure `expire_on_commit=False` on `async_sessionmaker` per FastAPI production architecture guidelines. Use `ASGITransport` with `httpx.AsyncClient`.

## Implementation log

## Review history
