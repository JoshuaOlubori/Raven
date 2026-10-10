# Architecture Spec: Dental Clinic Appointment Tracker

_Status: approved · Date: 2026-10-03_

## 1. Context
The Dental Clinic Appointment Tracker is an internal-only backend service enabling clinic staff (Admins, Receptionists, Dentists) to manage patients, dentist shift availability, dynamic service-duration slot calculation, appointment scheduling with strict conflict avoidance, finite state machine (FSM) transitions, immutable audit logging, and real-time Server-Sent Events (SSE). 

See [work/prd.md](file:///c:/Users/seyi/Documents/Development/Raven/work/prd.md) for full product requirements.

### Key NFR Drivers
- **NFR-1 (Zero Double-Booking):** Atomic transaction-level overlap detection with 409 Conflict.
- **NFR-2 (Latency):** Availability slot queries and booking endpoints with p95 < 100ms.
- **NFR-3 (Timezone Consistency):** Database storage in UTC (`TIMESTAMPTZ`), business availability and slot generation in `CLINIC_TIMEZONE` (America/New_York or configured IANA zone).
- **NFR-4 (Audit Immutability):** Append-only audit records, updates/deletions forbidden.
- **NFR-5 (Stateless Multi-Worker Operation):** No process-local shared mutable state for business logic; multi-worker friendly.
- **NFR-6 (Security):** Password hashing with Argon2, scoped JWT Bearer auth, RBAC guards.

---

## 2. Stack and Versions

| Component | Technology | Version | Purpose |
|---|---|---|---|
| Runtime | Python | >= 3.13 | High-performance modern Python runtime |
| Web Framework | FastAPI | >= 0.121.0 | Web API, DI graph, OpenAPI documentation; function-scoped yield dependencies commit before response background tasks |
| ASGI Server | Uvicorn (standard) | >= 0.30.0 | Production ASGI HTTP/SSE server |
| Validation / Schemas | Pydantic v2 | >= 2.10.0 | Request/response validation, computed fields |
| Settings Management | Pydantic Settings | >= 2.6.0 | 12-factor environment configuration |
| Database ORM | SQLAlchemy 2.0 (async) | >= 2.0.35 | Async declarative models, type-safe queries |
| DB Drivers | asyncpg / aiosqlite | >= 0.29.0 / >= 0.20.0 | PostgreSQL for production; SQLite for local/tests |
| Database Migrations | Alembic | >= 1.13.0 | Schema versioning and migration runner |
| Password Hashing | Argon2-cffi | >= 23.1.0 | RFC-recommended memory-hard credential hashing |
| JWT Tokens | PyJWT + cryptography | >= 2.9.0 | Compact, cryptographically signed Bearer tokens |
| HTTP Client (Tests) | HTTPX | >= 0.27.0 | Async test client for endpoint verification |
| Testing Suite | pytest + pytest-asyncio | >= 8.3.0 | Automated unit, integration, and API tests |
| Linter & Formatter | Ruff | >= 0.6.0 | Fast static analysis and formatting |
| Type Checker | mypy | >= 1.11.0 | Strict static type checking |

---

## 3. Layout (Standard §2)

Following the standard's §2 recommended **flat-packages-inside-`src/app/`** layout with domain segregation inside layers. This structure scales cleanly across our 6 domain modules while keeping persistence, business logic, and API wiring strictly decoupled.

```text
backend/
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── src/
│   └── app/
│       ├── __init__.py
│       ├── main.py               # Lifespan, middleware, router mounting, /health
│       ├── config.py             # Pydantic Settings class & app settings dependency
│       ├── schemas.py            # Central base types & shared constrained Pydantic types
│       ├── api/
│       │   ├── __init__.py
│       │   ├── deps.py           # Single source of truth for DI graph and *Dep aliases
│       │   └── auth.py           # CurrentUser model, get_current_user, require_roles
│       ├── db/
│       │   ├── __init__.py
│       │   ├── session.py        # Async engine, SessionLocal(expire_on_commit=False), init_db
│       │   └── repository.py     # Stateless async data access functions
│       ├── models/
│       │   ├── __init__.py
│       │   ├── base.py           # DeclarativeBase, TimestampMixin, UUIDMixin
│       │   ├── staff.py          # Staff account model
│       │   ├── patient.py        # Patient profile model
│       │   ├── service.py        # DentalService catalog model
│       │   ├── schedule.py       # WorkingShift, TimeOffBlock models
│       │   ├── appointment.py    # Appointment model
│       │   └── audit.py          # AppointmentAuditLog model
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── auth.py           # POST /api/v1/auth/token, GET /api/v1/auth/me
│       │   ├── staff.py          # /api/v1/staff (CRUD, activation)
│       │   ├── patients.py       # /api/v1/patients (CRUD, search, soft-delete)
│       │   ├── services.py       # /api/v1/services (CRUD, activate/deactivate)
│       │   ├── schedules.py      # /api/v1/schedules (shifts, time-off, availability slots)
│       │   ├── appointments.py   # /api/v1/appointments (book, reschedule, transition, cancel, audit)
│       │   └── live.py           # /api/v1/appointments/live (SSE stream)
│       └── services/
│           ├── __init__.py
│           ├── auth_service.py         # Password verification, JWT token issuance
│           ├── patient_service.py      # Profile management, validation, search
│           ├── service_catalog.py      # Procedure duration management
│           ├── availability_engine.py  # Dynamic slot subtraction algorithm (ADR 0001)
│           ├── appointment_service.py  # FSM transitions, booking overlap lock, audit logger
│           ├── event_broadcaster.py    # Async in-memory pub-sub for SSE distribution
│           └── notification_service.py # Abstract notification port + logging/test adapter
└── tests/
    ├── conftest.py               # DB engine fixture, AsyncSession, client with overrides
    ├── unit/                     # Domain & schema unit tests (availability engine, FSM)
    ├── integration/              # Repository queries & concurrent booking overlap tests
    └── api/                      # End-to-end API tests with dependency_overrides
```

---

## 4. Cross-Cutting Design

| Concern | Decision | Standard § | ADR |
|---|---|---|---|
| **Config & Secrets** | `pydantic-settings` `BaseSettings` reading from `.env` / environment variables. Exposes `Settings` object; validated at startup. | §8 | — |
| **Logging & Correlation ID** | `X-Correlation-ID` header extracted or generated via ASGI middleware. Included in all log records (JSON format) and injected into response headers. | §8, §11 | — |
| **Global Error Model** | Central exception handler returning standardized RFC-compliant error body `{ "error": "<code_string>", "message": "<str>", "correlation_id": "<str>", "details": ... }`. Maps domain exceptions to HTTP 400, 401, 403, 404, 409, 422, 500. | §8 | — |
| **Authentication (AuthN)** | Scoped Bearer JWT tokens signed with HMAC-SHA256 (`HS256`). Encodes `sub` (staff UUID), `role`, and `exp`. Injected via `OAuth2PasswordBearer` / `HTTPBearer` in `app/api/auth.py`. | §5, §8 | — |
| **Authorization (AuthZ)** | RBAC via `require_roles("ADMIN", "RECEPTIONIST", ...)` closure guard factories (Standard §8.2). Row-level checks (e.g. dentist viewing only their schedule) enforced in service layer. | §5, §8 | — |
| **DB Engine & Sessions** | Single app-scoped async engine (`create_async_engine`), request-scoped `AsyncSession` yielded via `get_db_session` with `expire_on_commit=False`. Auto-commit on success, rollback on error, always closed in `finally`. | §4, §5 | — |
| **Migrations** | Alembic async migrations configured with `env.py` reading app declarative models. Auto-generate revisions against models. | §4 | — |
| **Worker / Concurrency Model** | Stateless FastAPI instances running across multiple Uvicorn workers. Slot overlap enforced in database transaction. Real-time events broadcast through Redis Pub/Sub across all workers; process-local queues are only per-worker fan-out buffers. | §6, §7 | [ADR 0001](file:///c:/Users/seyi/Documents/Development/Raven/docs/adr/0001-dynamic-slot-computation-and-conflict-prevention.md), [ADR 0003](../../docs/adr/0003-multi-worker-live-event-broker.md) |
| **Background Jobs** | Dual pattern: optional in-process lifespan asyncio task for single worker / dev; protected HTTP maintenance endpoint for external crons in multi-worker. | §6, §7 | [ADR 0002](file:///c:/Users/seyi/Documents/Development/Raven/docs/adr/0002-reminder-execution-strategy.md) |
| **API Versioning & Docs** | All endpoints prefixed with `/api/v1`. Interactive Swagger UI available at `/docs`, ReDoc at `/redoc`. Internal OpenAPI schema filters sensitive internals. | §8 | — |

---

## 5. Test Architecture

### 5.1 Test Seams
1. **Schema Unit Tests (`tests/unit/test_schemas.py`)**:
   - Pydantic v2 validators, constrained types (`NonEmptyStr`, `PositiveQty`, `Email`), camelCase alias serialization, `@model_validator` date/time order checks.
2. **Pure Domain Unit Tests (`tests/unit/test_availability.py`, `test_fsm.py`)**:
   - Dynamic availability slot calculation algorithm tested across edge cases: zero shifts, shifts with breaks, overlapping appointments, adjacent appointments, DST clock jumps.
   - Appointment state machine transitions (valid transitions succeed, invalid transitions raise `InvalidStateTransitionError`).
3. **Repository & Transaction Tests (`tests/integration/test_repository.py`)**:
   - Database operations executed against real database (SQLite in-memory or PostgreSQL test container).
   - Eager-loading verification (`selectinload` for 1-to-many, `joinedload` for many-to-one) verifying query counts.
   - Concurrent overlap guard test: two concurrent sessions attempting to book the same dentist slot simultaneously; exactly one commits, other raises `409 Conflict`.
4. **API Integration Tests (`tests/api/`)**:
   - End-to-end HTTP requests executed via `httpx.AsyncClient(transport=ASGITransport(app=app))`.
   - Dependency graph overrides via `app.dependency_overrides[get_current_user]` to test permissions across roles (`ADMIN`, `RECEPTIONIST`, `DENTIST`).
   - Mocking external services (e.g. `NotificationService` replaced with `FakeNotificationService`).

### 5.2 Fixtures & Builders
- `db_engine`: Async engine pointing to `sqlite+aiosqlite:///:memory:` (or test postgres).
- `db_session`: AsyncSession rolled back or isolated per test case.
- `client`: `AsyncClient` with base URL `http://test`.
- `auth_headers_factory`: Helper to generate Bearer JWT tokens for any role.
- Model builders: Factory functions `create_test_staff()`, `create_test_patient()`, `create_test_service()`, `create_test_shift()`.

---

## 6. Quality Gates

All pull requests and commits must cleanly pass the following four quality gates:

```bash
# 1. Static code linting
uv run --directory backend ruff check

# 2. Code formatting verification
uv run --directory backend ruff format --check

# 3. Strict type checking
uv run --directory backend mypy src

# 4. Automated test suite execution
uv run --directory backend pytest -q
```

---

## 7. Risks and ADR Index

- [ADR 0001: Dynamic Slot Computation and Database Overlap Guard](file:///c:/Users/seyi/Documents/Development/Raven/docs/adr/0001-dynamic-slot-computation-and-conflict-prevention.md) — Overlap detection in DB transaction; dynamic slot generation.
- [ADR 0002: Dual-Mode 24-Hour Pre-Appointment Reminder Execution](file:///c:/Users/seyi/Documents/Development/Raven/docs/adr/0002-reminder-execution-strategy.md) — Protected maintenance endpoint + optional lifespan asyncio task.
