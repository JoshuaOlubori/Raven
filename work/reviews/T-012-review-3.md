# Review T-012 round 3 — Changes requested
Gates: ruff ✓ · format ✗ (62 files already formatted; generated `work/TRACKER.md` is invalid UTF-8) · mypy ✓ · pytest ✓ (151 passed, 2 skipped)

## Spec — findings

### Blocker — Booking and reschedule confirmations are never scheduled in supported FastAPI versions
`backend/src/app/api/deps.py:60-64` adds `after_response_callbacks` to the injected `BackgroundTasks` object from the exit section of `get_db_session`. `DbSessionDep` uses the default request scope (`:74`), and the project's supported FastAPI range starts at 0.118.0. FastAPI documents that request-scoped `yield` cleanup runs after the response and its background tasks have been sent/run; at that point appending tasks cannot dispatch them. Thus the callbacks registered from `AppointmentService.book_appointment()` and `.reschedule_appointment()` (`backend/src/app/services/appointment_service.py:225-226,391-392`) are too late, so the required confirmations are silently omitted on real HTTP requests. Register the background work while handling the request (for example, pass the shared `BackgroundTasks` into the route/service path), and preserve the post-commit guard before it can run. Add a real ASGI request test that asserts delivery after commit. See [FastAPI's `yield` dependency lifecycle](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/) and [background tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/).

## Standards — findings

- **Layer 3 / lifecycle:** `backend/src/app/api/deps.py:60-64` relies on request-scoped dependency teardown to mutate response background work after FastAPI has already run that work. Move registration to the path-operation/request phase; keep database commit ordering explicit.

## Tests — findings

### Major — Confirmation tests do not cover the real request/response lifecycle
`backend/tests/unit/test_db_session_callbacks.py:58-84` manually invokes the dependency generator and only afterward invokes `background_tasks()`. This models task registration before task execution, not FastAPI's request-scoped cleanup order. The API tests cover reminder endpoints but have no booking/reschedule confirmation request test (`backend/tests/api/test_appointments.py`). Add ASGI tests that submit booking and reschedule requests, verify the notification fake is called, and ensure the callback does not run before a successful commit.

## Summary

| Severity | Count | Key |
|---|---:|---|
| Blocker | 1 | Confirmation callbacks are registered during late request-scoped cleanup and do not execute |
| Major | 1 | Unit-level task test misses the actual FastAPI lifecycle failure |
| Minor | 0 | — |
| Nit | 0 | — |

Worst issue: both booking and reschedule confirmation delivery are absent on the supported FastAPI request lifecycle.

Verdict: **Changes requested**.
