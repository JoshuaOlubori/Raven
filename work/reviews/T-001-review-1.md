# Review T-001 round 1 — Approve

Gates: ruff ✓ · ruff format ✓ · mypy ✓ · pytest ✓ (3 passed)

## Spec — findings

All four acceptance criteria are met by code and verified by tests.

| AC | Spec requirement (quoted) | Code | Test | Verdict |
|---|---|---|---|---|
| AC1 | *"Given a running application, When `GET /health` is requested, Then it returns `200 OK` with `{"status": "ok"}` and response header `X-Correlation-ID`."* | `main.py:60-63` (`/health` route); `main.py:30-40` (middleware injects `X-Correlation-ID` on every response) | `test_health.py:11` — asserts 200, `{"status": "ok"}`, header present | ✅ |
| AC2 | *"Given any unhandled exception raised in an endpoint, When invoked, Then the global middleware returns `500 Internal Server Error` with JSON body `{"error": "internal_server_error", "correlation_id": "...", "message": "..."}`."* | `main.py:43-57` — `@app.exception_handler(Exception)` returns `JSONResponse` with `error`, `message`, `correlation_id` fields + `X-Correlation-ID` header | `test_errors.py:13` — asserts 500, `error == "internal_server_error"`, both `message` and `correlation_id` present, body correlation ID matches response header | ✅ |
| AC3 | *"Given an active database session dependency, When an endpoint finishes successfully, Then the session commits automatically; When an exception occurs, Then it rolls back."* | `deps.py:23-32` — `get_db_session`: `yield` → `commit()` on success, `rollback()` + `raise` on exception, `close()` in `finally` | `test_db_session_lifecycle.py:23` — success path asserts commit + `close()`; exception path asserts rollback + `close()` via `athrow(RuntimeError)` | ✅ |
| AC4 | *"All four quality gates (`ruff check`, `ruff format --check`, `mypy src`, `pytest -q`) execute and pass cleanly."* | pyproject.toml configures ruff, mypy, pytest | Reviewer ran all four gates | ✅ |

**Spec sources verified against:**
- Architecture §2 (stack & versions): all 5 dependency groups present in `pyproject.toml` — fastapi, uvicorn[standard], pydantic[settings], sqlalchemy[asyncio]+aiosqlite+asyncpg+alembic, argon2-cffi, pyjwt+cryptography. Test dependencies in `dependency-groups.dev`. ✅
- Architecture §4 (cross-cutting): config via pydantic-settings; `X-Correlation-ID` middleware; standardized 500 error body; async engine + `expire_on_commit=False` session. ✅
- Architecture §3 (layout): flat `src/app/` package structure with `main.py`, `config.py`, `db/session.py`, `db/repository.py`, `api/deps.py`. ✅
- Architecture §5 (test seams): `test_engine` (in-memory SQLite + StaticPool), `test_session_local` (TrackedAsyncSession), `override_dbsession` (monkeypatches `SessionLocal`), `client` (ASGITransport + AsyncClient with `raise_app_exceptions=False`). ✅

**Scope:** No out-of-scope features were implemented. The `repository.py` stub, test-only `/_test/exception` route, and `TrackedAsyncSession` are all explicitly documented as test/structural scaffolding, consistent with the spec §3 layout and Architecture §5 fixture patterns.

## Standards — findings

- **minor**: Missing structured exception logging. The `fastapi-production-architecture` Concurrency & Ops reference (ref: `concurrency-and-ops.md:60-96`) specifies that the correlation-ID/error-handling middleware must "Catch unhandled errors, **log them with structured context**, and return a sanitized 500 JSON response." Architecture §4 likewise states the correlation ID must be "Included in all log records (JSON format)." The `internal_server_error_handler` at `main.py:43-57` returns the 500 response but never calls `logger.exception(...)` or otherwise logs the unhandled exception. In production, unhandled 500s produce no log trace, making incident diagnosis impossible. **Fix**: add a module-level `logging.getLogger("app")` and call `logger.exception("Unhandled server error", extra={"correlation_id": correlation_id})` before returning the JSONResponse.

- **nit**: Error-body field ordering. AC2's spec lists the body as `{"error": "internal_server_error", "correlation_id": "...", "message": "..."}` but the code at `main.py:49-56` returns `error`, `message`, `correlation_id`. JSON object key ordering is semantically neutral, so this is cosmetic — **fix**: reorder to `error`, `correlation_id`, `message` to match the spec's listing for readability.

- **nit**: Error-handling pattern deviates from the standard's middleware template. The `fastapi-production-architecture` reference (ref: `concurrency-and-ops.md:60-96`) shows error catching inside the `try/except` of the correlation-ID middleware. The implementation uses `@app.exception_handler(Exception)` instead, which is a valid but different FastAPI pattern. The implementation log (T-001:93-94) documents the rationale: "Starlette's `ServerErrorMiddleware` sends the response then re-raises, so the outer `BaseHTTPMiddleware` can't mutate it." This is a sound architectural decision — **no action needed**, but worth flagging for consistency in documentation. The `X-Correlation-ID` header is correctly set in both the middleware and the handler.

- **nit**: Leftover `src/backend/` orphan directory. `backend/src/backend/__init__.py:1-7` was gutted to a docstring-only stub. The implementation log (T-001:93-94) explicitly notes it as "scheduled for removal" and "no automated deletion is supported in this session." **Fix**: delete the `src/backend/` directory.

## Tests — findings

- Every acceptance criterion has a test at the named seam: AC1 → API (`test_health.py`), AC2 → API (`test_errors.py`), AC3 → Repository+DB (`test_db_session_lifecycle.py`), AC4 → manually verified by reviewer. ✅

- Expected values are independent of the implementation:
  - `test_health.py:15` — `response.json() == {"status": "ok"}` is a literal constant from Architecture §4, not recomputed. ✅
  - `test_errors.py:18` — `body["error"] == "internal_server_error"` is a literal from the spec. ✅
  - `test_db_session_lifecycle.py` — asserts observable side-effects (committed row visible, rolled-back row invisible, `close()` invoked) verified through a fresh session, not by inspecting internal generator state. ✅

- Tests assert behaviour, not private structure: The `test_db_session_lifecycle` test drives the `get_db_session` generator via `.asend()` / `.athrow()` and observes commit/rollback/close through external queries. This survives a refactor that changes the generator's internal structure but preserves the transactional contract. ✅

- Failure paths: `test_errors.py` exercises the 500 path. No 401/403/404/409/422 paths yet — correct, as those domain endpoints are explicitly out of scope ("Domain entity models, authentication, patient, service, or appointment endpoints (handled in subsequent tickets)"). ✅

- No sleeps, no order dependence across tests, no shared mutable fixtures beyond the session-scoped in-memory DB (which is isolated per test session). ✅

- **nit**: Shared `test_lifecycle` table (session-scoped, created in `conftest.py:91-96`). Currently only one test writes to it, but assertions like `"rolled-back-row" not in vals` (`test_db_session_lifecycle.py:67`) would become fragile if future tests insert rows into the same table without cleanup. **Mitigation**: future domain tests should use their own table or unique values per test.

## Summary

| Severity | Count |
|---|---|
| blocker | 0 |
| major | 0 |
| minor | 1 |
| nit | 4 |

**Single worst issue:** missing structured exception logging (minor) — unhandled 500s produce no log trace, contrary to Architecture §4's requirement that correlation IDs appear in all log records. Non-blocking for the walking skeleton but should be addressed before domain endpoints are added.
