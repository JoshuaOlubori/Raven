---
id: T-001
title: Walking skeleton and test infrastructure
status: in-review
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

### What was built
Walking skeleton + test infrastructure for the FastAPI backend (`src/app/`).
- `backend/pyproject.toml`: dependencies per Architecture §2 (fastapi, uvicorn,
  pydantic[settings], sqlalchemy[asyncio]+aiosqlite+asyncpg+alembic,
  argon2-cffi, pyjwt+cryptography). Test/tooling in `dependency-groups.dev`
  (httpx, pytest, pytest-asyncio, ruff, mypy). Project `name = "app"` so the
  uv_build backend packages `app` (matches `src/app/`); `[tool.fastapi]`
  entrypoint set, plus ruff/mypy/pytest config.
- `src/app/config.py`: `Settings` (pydantic-settings) with `DATABASE_URL`,
  `CLINIC_TIMEZONE`, `JWT_SECRET_KEY`, `APP_ENV` (dev defaults; prod-hardening
  deferred to T-002). `get_settings()` accessor.
- `src/app/db/session.py`: app-scoped async engine, `SessionLocal`
  `async_sessionmaker(expire_on_commit=False)` (Standard §4), `Base`
  (DeclarativeBase), and `init_db(engine=None)` creating tables.
- `src/app/api/deps.py`: `get_db_session` async-generator dependency — commit on
  success, rollback + re-raise on error, `close()` in `finally` (Standard §4);
  `DbSessionDep` alias.
- `src/app/main.py`: `lifespan` calling `init_db()`, `X-Correlation-ID`
  middleware (extract/generate on `request.state`, inject on response), global
  `@app.exception_handler(Exception)` → standardized 500 body (Architecture §4;
  header also set in the handler because Starlette's ServerErrorMiddleware
  sends the 500 then re-raises, so the outer middleware can't mutate it),
  and `GET /health` → `{"status": "ok"}`.

### Files touched
- `backend/pyproject.toml` (new deps/config; project renamed backend→app)
- `src/app/{__init__,config,main}.py`, `src/app/db/{__init__,session.py}`,
  `src/app/api/{__init__,deps.py}`, `src/app/db/repository.py` (placeholder)
- `tests/conftest.py` (test engine, tracked session, overrides, client w/
  `raise_app_exceptions=False`, test-only `/_test/exception` route)
- `tests/api/test_health.py`, `tests/api/test_errors.py`,
  `tests/integration/test_db_session_lifecycle.py`

### Notes / Decisions
- **Layout conflict resolved per approved spec §3:** the initial scaffold
  (`src/backend/` stub, `name = "backend"`) contradicted the approved
  Architecture spec which mandates `src/app/`. Followed the spec: package is
  `app`. Project `name` set to `"app"` so `uv_build` selects `src/app`
  (verified: editable install is now `app==0.1.0`, not `backend`).
- `greenlet` added implicitly via `sqlalchemy[asyncio]` (SQLAlchemy async ext
  requires it; the spec's bare `sqlalchemy` dep omits this transitive need).
- `JSONResponse`/`Response` imported from `starlette.responses` (FastAPI 0.142
  no longer re-exports `JSONResponse`).
- `X-Correlation-ID` set in the exception handler as well as the middleware,
  because on the error path `ServerErrorMiddleware` sends the response then
  re-raises, so the outer `BaseHTTPMiddleware` never reaches its header line.
- Tests assert session-close via a `TrackedAsyncSession` subclass recording
  `close()`; SQLAlchemy 2.x sessions are reusable so `is_active` is not a
  reliable "closed" signal.
- `src/backend/` stub remains as a neutralized docstring-only orphan; the
  directory is not auto-deletable in this session — scheduled for removal.

### Commands run
`uv sync`, `uv run ruff check`, `uv run ruff format --check`,
`uv run mypy src`, `uv run pytest -q` — all green. Lifespan boot smoke-tested
against an in-memory DB.

### Verification of acceptance criteria
- [x] AC1 `GET /health` → 200 `{"status":"ok"}` + `X-Correlation-ID` header
  (`test_health_check_returns_200_and_correlation_id`)
- [x] AC2 unhandled exception → 500 `{"error":"internal_server_error",
  "message":..., "correlation_id":...}` with header matching body
  (`test_unhandled_exception_returns_500_error_body`)
- [x] AC3 `get_db_session` commits on success, rolls back on error, closes in
  `finally` (`test_db_session_lifecycle_commits_and_closes`)
- [x] AC4 all four quality gates pass (ruff check / format --check / mypy src / pytest -q)

## Review history
