# Final Review — 2026-10-10

## Gate results

| Gate | Result | Evidence |
|---|---|---|
| Ruff | Pass | `uv run --directory backend ruff check` — all checks passed |
| Format | Pass | `uv run --directory backend ruff format --check` — 62 files already formatted |
| mypy | Pass | `uv run --directory backend mypy src` — 39 source files, no issues |
| pytest | Pass | `uv run --directory backend pytest -q` — 152 passed, 2 skipped in 10.05s |
| Coverage | Not measured | pytest-cov is not installed; adding `--cov` fails with unrecognized arguments |
| Alembic migration smoke test | Not runnable | `backend/alembic.ini`, migration environment and revisions are absent; application instead invokes `Base.metadata.create_all()` at startup |
| Production-like boot / OpenAPI comparison | Not verified | No production deployment configuration or API schema contract check was available; Redis service not provisioned in this environment |
| Bandit / dependency audit / secret scan | Not run | Bandit, pip-audit, Trufflehog and Gitleaks executables are unavailable |

The working tree had existing user changes before this review. They were preserved.

## PRD coverage matrix

| Requirement | Ticket(s) | Tests/evidence | Status |
|---|---|---|---|
| R-1 Authentication | T-002 | Auth API tests; invalid/expired token paths | Covered |
| R-2 RBAC | T-003 | Staff and module API role tests | Covered; review not an exhaustive route × role proof |
| R-3 Patient profile | T-005 | Patient API tests | Covered |
| R-4 Patient search/retrieval | T-005 | Search, pagination and detail API tests | Covered |
| R-5 Patient soft-delete | T-005 | Delete and inactive-record behavior tests | Covered |
| R-6 Service catalog | T-004 | Services API tests | Covered |
| R-7 Shifts | T-006 | Schedule API tests | Covered |
| R-8 Time off | T-006 | Schedule API tests incl. ownership authorization | Covered |
| R-9 Availability | T-007 | API and unit tests incl. DST and timing | Covered |
| R-10 Booking | T-008 | Appointment service/API tests | Gap: production concurrency guarantee is not proven (F-002) |
| R-11 Reschedule | T-009 | Appointment service/API tests | Covered |
| R-12 State transitions | T-010 | FSM and API tests | Covered |
| R-13 Cancellation | T-009/T-010 | Reason and lifecycle tests | Covered |
| R-14 Audit log | T-010 | Audit persistence/API tests | Covered at application level; database immutability enforcement not established |
| R-15 Live SSE | T-011 | SSE API and Redis integration tests | Covered; Redis integration test skipped without configured test Redis |
| R-16 Confirmations | T-012 | Service/API tests | Covered |
| R-17 Reminders | T-012 | Dispatcher/repository/API tests | Covered; cross-worker claim/delivery behavior deserves deployment validation |
| NFR-1 Zero double booking | T-008 | Sequential two-session test only | Gap (F-002) |
| NFR-2 p95 latency | T-007/T-008 | Availability engine timing test | Partial: engine-only test, not end-to-end database/API load |
| NFR-3 UTC/timezone/DST | T-006/T-007 | DST and timezone unit tests | Covered in tested cases |
| NFR-4 Audit immutability | T-010 | Application audit tests | Partial: no database permissions/trigger enforcement |
| NFR-5 Stateless workers | T-011/T-012 | Redis cross-instance test; reminder tests | Partial: event fan-out has cross-instance coverage, reminder claims lack atomic claim/lease proof |
| NFR-6 Security | T-002/T-003/T-005 | Auth, password and authorization tests | Gap: default known JWT secret remains accepted in non-development configuration (F-003) |

No PRD out-of-scope functionality was identified in the reviewed routes and services.

## Findings

### Authorization completeness

The implemented API routes are protected by authentication or explicit role guards, and tests exercise role denials across several modules. The review did not establish a complete generated OpenAPI route × role test matrix; this remains a minor assurance gap.

### Architecture conformance

- **[Major F-001] Production schema lifecycle has no migrations.** The architecture requires Alembic revisions and reversible upgrades, but there is no Alembic configuration or migration directory. `init_db()` calls `Base.metadata.create_all()` from lifespan. This cannot safely evolve an existing production schema or satisfy the required empty-database/downgrade/upgrade smoke test.
- Layered `src/app` layout, async request sessions, centralized domain error handling and router separation are present. Several persistence flows use eager loading; list endpoints are bounded where paginated.
- The architecture specifies JSON structured logging and a `/health` route; logs are standard-library text logs and there is no readiness check. These are minor operational gaps.

### Performance and persistence

- **[Blocker F-002] Appointment overlap protection does not serialize empty-range checks.** PostgreSQL `SELECT ... FOR UPDATE NOWAIT` only locks rows returned by the query. When no appointment currently overlaps, concurrent transactions both obtain an empty result and can both insert overlapping appointments. There is no exclusion constraint or per-dentist lock. The test named concurrent booking runs the two sessions sequentially with a commit between them, so it does not expose this race. This violates NFR-1, a release-critical guarantee.
- Existing query patterns include pagination for patients; a full query-plan/index and endpoint load audit was not established. NFR-2 is only measured for the availability engine calculation, not end-to-end API/database latency.

### Shared state and workers

Redis backs cross-worker live event delivery and the integration test exists. Reminder delivery uses a read-then-send-then-mark flow; no atomic claim or lease was demonstrated to prevent two workers from concurrently sending the same reminder. Treat multi-worker reminder idempotency as a minor follow-up unless deployment requires multiple reminder workers.

### Security

- **[Major F-003] Known JWT signing key is accepted as a runtime default.** `Settings.jwt_secret_key` defaults to `dev-insecure-secret-change-in-production`, and `app_env` does not reject that value outside development. A deployment missing `JWT_SECRET_KEY` would sign and accept tokens with a publicly known key. Require an explicitly supplied strong secret for non-development environments and test the startup failure.
- Standard HTTP error bodies avoid returning exception text; passwords use Argon2; RBAC and active-account checks exist. Automated static security, dependency and secret scans were unavailable in this environment.

### Cross-ticket consistency and operability

No urgent duplicated-helper or abandoned-flag issue was confirmed. README documents Redis setup and the event integration test, but does not provide full run/migrate/deploy guidance; `.env.example`, readiness semantics and structured JSON logging are absent or not documented.

## Verdict

**Do not ship.** F-002 violates the product's zero-double-booking guarantee. F-001 and F-003 also need resolution before production deployment.

## Backlog

- **Minor:** Install/configure pytest-cov and record measured coverage, including service coverage against the >90% target.
- **Minor:** Add end-to-end API/database latency and query-plan checks for NFR-2.
- **Minor:** Complete generated OpenAPI route × role authorization coverage.
- **Minor:** Enforce immutable audit records at the database boundary and document production DB permissions.
- **Minor:** Make reminder dispatch atomically claim work before sending to prevent duplicate delivery across workers.
- **Minor:** Add readiness endpoint, JSON structured logs with correlation IDs, `.env.example`, and full run/test/migrate/deploy instructions.
- **Minor:** Run Bandit/equivalent, dependency audit and secret scan in CI.

## Follow-up tickets

- T-013: Add reversible Alembic migrations and remove production startup `create_all`.
- T-014: Enforce atomic cross-worker appointment overlap prevention and prove it with true concurrent PostgreSQL sessions.
- T-015: Reject missing/default JWT signing secrets outside development.
