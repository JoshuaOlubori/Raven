# Test Strategy: Dental Clinic Appointment Tracker

## 1. Principles
- **Test behaviour through public seams**, not private internal helper functions.
- **Expected values come from the PRD and approved specifications**, never re-calculated using the implementation's own code logic.
- **One test at a time (Red → Green)**: write a failing test, write the minimal code to satisfy it, verify green, run quality gates, commit.
- **Isolate tests with rollbacks**: tests interacting with the database execute inside isolated transactions rolled back after each test case.

---

## 2. Seams

| Seam | Tooling | Used For |
|---|---|---|
| **Schema Unit** | `pytest` | Pydantic v2 input validators, phone/email constraints, `@model_validator` time ranges, camelCase alias serialization |
| **Pure Domain Unit** | `pytest` | Dynamic availability slot calculation algorithm, DST handling, appointment FSM transition logic |
| **Repository + Real DB** | `pytest-asyncio`, SQLite (in-memory) / PostgreSQL | CRUD queries, unique constraints, foreign keys, cascade rules, eager loading (no N+1) |
| **Service with Fakes** | `pytest` | Domain business logic with injected collaborator fakes (e.g. `FakeNotificationService`) |
| **API via Dependency Graph** | `httpx.AsyncClient` + `app.dependency_overrides` | HTTP status codes, error bodies, role-based auth guards (`CurrentUserDep`), pagination |
| **Streaming / SSE** | `httpx` async streaming | SSE event frames, keep-alive pings (`: ping`), event IDs, multi-subscriber broadcasts |
| **Concurrency Seam** | `asyncio.gather` / multi-session DB | Zero double-booking overlap guard (`409 Conflict`), simultaneous reminder claim idempotency |

---

## 3. Fixtures and Builders (`tests/conftest.py`)

- `db_engine`: App-scoped async engine connected to in-memory SQLite (`sqlite+aiosqlite:///:memory:`) configured with table creation.
- `db_session`: AsyncSession yielded for each test, rolled back in `finally` to ensure clean isolation.
- `client`: `httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")`.
- `auth_headers`: Helper function `create_auth_headers(role="ADMIN", staff_id=...)` generating valid signed JWT tokens.
- **Entity Builders**:
  - `build_staff(role="DENTIST", ...)`
  - `build_patient(first_name="Jane", ...)`
  - `build_service(name="Cleaning", duration_minutes=45, ...)`
  - `build_shift(dentist_id, day_of_week=0, start=time(9,0), end=time(17,0))`
  - `build_appointment(patient_id, dentist_id, service_id, start_time, ...)`

---

## 4. Cross-Cutting Test Suites

| Suite | Purpose | Target Ticket |
|---|---|---|
| **Authorization Matrix** | Every endpoint $\times$ role (`ADMIN`, `RECEPTIONIST`, `DENTIST`, `UNAUTHENTICATED`) returns expected `200/201/204` vs `401` vs `403`. | T-003, T-005, T-008 |
| **Query-Count Guards** | List endpoints (`/patients`, `/appointments`, `/staff`) maintain constant query count regardless of row count (`selectinload`/`joinedload`). | T-005, T-008, T-010 |
| **OpenAPI Contract Snapshot** | Verifies exported OpenAPI schema does not introduce unexpected breaking schema changes. | T-001 |
| **Standardized Error Body Shape** | Asserts all error responses conform to `{ "error": "<code_string>", "message": "<str>", "correlation_id": "<str>" }`. | T-001 |
| **Concurrency Overlap Guard** | Two concurrent sessions attempting to book overlapping slots for the same dentist; exactly 1 succeeds (201), 1 fails (409). | T-008 |
| **Multi-Worker Safety** | Static AST / module inspection verifying no module-level mutable dicts/lists without locks. | T-011 |

---

## 5. CI Execution Order

Every pull request and ticket commit must pass:
1. `uv run --directory backend ruff check` (Linting)
2. `uv run --directory backend ruff format --check` (Formatting)
3. `uv run --directory backend mypy src` (Strict type checking)
4. `uv run --directory backend pytest -q` (Unit, integration, API, and cross-cutting suites)

---

## 6. Coverage Expectations

- 100% of PRD functional requirements (`R-1` to `R-17`) and non-functional requirements (`NFR-1` to `NFR-6`) covered by explicit automated tests.
- High test coverage across core domain calculation and FSM logic (target >90% on `services/`).
