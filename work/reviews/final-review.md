# Final Review — 2026-10-10

## Gate results

| Gate | Result | Evidence |
|---|---|---|
| Ruff | Pass | `uv run --directory backend ruff check` — all checks passed |
| Format | Pass | `uv run --directory backend ruff format --check` — 68 files already formatted |
| mypy | Pass | `uv run --directory backend mypy src` — 39 source files, no issues |
| pytest | Pass with skips | `uv run --directory backend pytest -q` — 173 passed, 2 skipped in 69.71s |
| Coverage | Not measured | pytest-cov is not configured/installed |
| Alembic | Pass | Integration tests apply an empty-database migration, check metadata drift, downgrade to base, and upgrade again |
| Production-like boot / OpenAPI comparison | Not verified | Direct boot/OpenAPI inspection could not launch the project interpreter in this environment; no schema-to-spec comparison is automated |
| PostgreSQL booking race | Not exercised here | PostgreSQL concurrency tests skip unless `TEST_POSTGRES_DATABASE_URL` is configured; independent-session race cases are present |
| Redis cross-worker event test | Not exercised here | Redis integration test skips unless `TEST_REDIS_URL` is configured |
| Static security / dependency / secret scans | Not run | Bandit, dependency audit, and secret scanner are not configured as project gates |

Existing user changes in the working tree were preserved. `backend/.env` is ignored by Git and was not read.

## PRD coverage matrix

| Requirement | Ticket(s) | Tests/evidence | Status |
|---|---|---|---|
| R-1 Authentication | T-002 | Auth API, token, invalid/expired-token tests | Covered |
| R-2 RBAC | T-003 | API role tests across staff, patient, service, schedule, and appointment routers | Covered; exhaustive route × role matrix is not generated |
| R-3 Patient profile | T-005 | Patient API validation and creation tests | Covered |
| R-4 Patient search/retrieval | T-005 | Search, pagination, detail tests | Covered |
| R-5 Patient soft-delete | T-005 | Deactivation and inactive-record behavior tests | Covered |
| R-6 Service catalog | T-004 | Services API tests | Covered |
| R-7 Shifts | T-006 | Schedule API tests | Covered |
| R-8 Time off | T-006 | Schedule API, ownership and overlap tests | Covered |
| R-9 Availability | T-007 | Unit/API tests including DST and slot calculation | Covered; end-to-end performance target not measured |
| R-10 Booking | T-008, T-014 | Booking tests and PostgreSQL concurrent-session integration tests | Code path has stable dentist-row lock; PostgreSQL tests not run here |
| R-11 Reschedule | T-009, T-014 | Reschedule service/API tests and PostgreSQL concurrency case | Covered; PostgreSQL test not run here |
| R-12 State transitions | T-010 | FSM and API tests | Covered |
| R-13 Cancellation | T-009, T-010 | Reason validation and lifecycle tests | Covered |
| R-14 Immutable audit log | T-010 | Audit API/persistence tests | Partial: append-only behavior is not enforced against direct database UPDATE/DELETE |
| R-15 Live SSE | T-011 | SSE tests; Redis integration test | Covered locally; cross-worker test skipped here |
| R-16 Confirmations | T-012 | Notification adapter and dispatch tests | Covered |
| R-17 Reminders | T-012 | Dispatcher and API tests | Covered; concurrent-worker idempotency remains unproven |
| NFR-1 Zero double-booking | T-014 | Stable dentist-row `FOR UPDATE` serialization; PostgreSQL race tests | Implementation addressed; release environment must run PostgreSQL race tests |
| NFR-2 p95 latency | T-007, T-008 | Availability engine timing test | Partial: no endpoint/database load result |
| NFR-3 Timezone consistency | T-006, T-007 | DST/timezone unit cases | Covered for tested cases |
| NFR-4 Audit immutability | T-010 | Application behavior tests | Partial: database permissions/triggers do not prevent edits/deletes |
| NFR-5 Stateless workers | T-011, T-012, T-014 | Redis transport, per-dentist DB locks, reminder tests | Partial: Redis and multi-worker reminder behavior need deployment-level verification |
| NFR-6 Security | T-002, T-003, T-005, T-015 | Auth, RBAC, input, and JWT configuration tests | Major gap F-001: JWT strength checks admit guessable repeated values |

No out-of-scope feature was identified in the reviewed routes and services.

## Findings

### Security

- **[Major F-001] JWT secret validation accepts guessable repeated strings.** Non-development settings require a 32-character string with upper/lowercase, a digit, and a special character, but this is only a character-class test. Values such as `Aa1!` repeated to the minimum length satisfy the validator and remain trivial to guess, allowing token forgery. Require a cryptographically generated high-entropy secret (or a defensible entropy/known-pattern check) and test repeated/patterned values. Follow-up: T-016.
- Password hashing uses Argon2; JWT signature and expiration validation, active-account checks, and role guards are present. Error responses sanitize internal exception details.

### Architecture and persistence

- The flat `src/app` layers, async request-scoped sessions, centralized domain errors, provider wiring, and Alembic migration lifecycle conform to the architecture in reviewed areas.
- T-014 now takes a lock on the stable dentist row before checking overlaps, including the empty-result case. Two genuine concurrent PostgreSQL API tests are present, but were skipped without the configured database. Require them in CI/release verification before relying on NFR-1 operationally.
- **[Minor F-002] Audit immutability is application-level only.** The model and migration do not prevent a database principal from updating/deleting audit rows, and cascading foreign keys can remove history with parent records. NFR-4 explicitly includes database users. Add database enforcement and align retention/deletion constraints.

### Authorization completeness

Protected routers use authentication or role guards, and tests cover representative role denials. A generated OpenAPI route × role matrix proving a test for every route and role is absent. **Minor F-003.**

### Performance, shared state, and operations

- Patient listing is paginated and relevant appointment indexes exist. A full query-plan/N+1 audit and end-to-end latency benchmark were not established; NFR-2 remains only partially evidenced.
- Redis backs cross-worker SSE. Local broadcaster queues are bounded. Reminder dispatch uses a read/send/mark flow without a demonstrated atomic claim/lease, so concurrent workers may duplicate delivery. **Minor F-004.**
- `/health`, correlation-ID propagation, logging, and migration instructions exist. Readiness semantics, JSON structured log formatting, `.env.example`, and complete deploy/runbook guidance remain incomplete. **Minor F-005.**
- Automated security/dependency/secret scans are not part of the verified gates. **Minor F-006.**

## Verdict

**Ship after fixes.** Resolve F-001 before production because a guessable JWT key permits token forgery. The production release pipeline should also run the PostgreSQL concurrency suite against a real PostgreSQL service.

## Backlog

- F-002: Enforce audit-log immutability at the database boundary and prevent cascades from erasing history.
- F-003: Generate authorization tests for every OpenAPI route × role combination.
- F-004: Atomically claim reminder work or use a lease/idempotency key for multi-worker dispatch.
- F-005: Add readiness semantics, JSON structured logs, `.env.example`, and deployment/runbook instructions.
- F-006: Add security, dependency, and secret scanning to CI.
- Measure coverage and API/database p95 latency under the PRD's stated operational load.
- Ensure PostgreSQL concurrency integration tests run in CI/release verification.

## Follow-up tickets

- T-016: Reject guessable JWT signing secrets in non-development environments.
