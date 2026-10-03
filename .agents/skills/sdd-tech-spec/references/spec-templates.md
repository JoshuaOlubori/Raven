# Spec templates

## Architecture (`work/specs/00-architecture.md`)

```markdown
# Architecture spec
_Status: draft | approved · Date_

## 1. Context
One paragraph + link to PRD. List NFRs that shape architecture (NFR-ids).

## 2. Stack and versions
Python, FastAPI, Pydantic v2, SQLAlchemy 2.0 async + driver, Alembic, pytest(+pytest-asyncio, httpx), Ruff, mypy, Redis/other (only if justified).

## 3. Layout (standard §2)
Chosen layout (a or b) and why. Folder tree down to module level.

## 4. Cross-cutting design
| Concern | Decision | Standard § | ADR |
|---|---|---|---|
| Config & secrets | | §8 | |
| Logging & correlation id | JSON logs, X-CORRELATION-ID via dependency | §8 | |
| Error model | global exception handler, error body shape, status mapping | §8 | |
| AuthN | | §5 | |
| AuthZ model | RBAC gate + ABAC refine; guard factories | §5 | |
| DB sessions | app-scoped engine, request-scoped session | §4 | |
| Migrations | | §4 | |
| Worker model | processes, shared state externalised | §7 | |
| API versioning & docs | | §8 | |

## 5. Test architecture
Seams, fixtures (db, client, auth override), data builders, what runs in CI, coverage expectations.

## 6. Quality gates
Exact commands (ruff, mypy, pytest) and pre-commit hooks (§8).

## 7. Risks and ADR index
```

## Module (`work/specs/<domain>.md`)

```markdown
# <Domain> module spec
_Status: draft | approved · Covers: R-1, R-2, NFR-3_

## 1. Responsibility
What this module owns and what it explicitly does not.

## 2. Layer 1 — Contracts (standard §3)
| Schema | Purpose | Fields (name: type, optional?) | Validators / computed fields (business rules) |
|---|---|---|---|
| DealCreate | input | … | positive qty; discount ≤ cap (R-4) |
| DealRead | output | … | computed total |
Public aliases that must stay stable. Input/output split.

## 3. Layer 2 — Persistence (standard §4)
| Model | Columns | Relationships | Indexes / constraints |
Eager-loading plan per read path (avoid N+1). Repository functions: `get_`, `list_`, `create_`, `update_`, `delete_` signatures. Migration notes.

## 4. Layer 3 — Wiring (standard §5)
Providers (`get_<thing>`), `<Thing>Dep` aliases, service constructors (injected collaborators), guards (`require_roles`, `require_permission`), router-level guards.

### Endpoints
| Method | Path | Request | Response | Success | Errors (401/403/404/409/422) | Guard | Covers |
|---|---|---|---|---|---|---|---|

### Authorization matrix
| Action | Role/permission | Row-level (ABAC) rule |

## 5. Layer 4 — Concurrency and real-time (standard §6)
Which calls run concurrently (`TaskGroup`, `except*` handling), what is offloaded (`run_in_executor`), SSE/WebSocket design (event names, ids, retry, keep-alive, resume via Last-Event-ID, session closed before streaming). "N/A — …" if none.

## 6. Layer 5 — State and hardening (standard §7)
Any shared mutable state and where it lives (external store), middleware, rate limits, caching, thread-safety notes. "No module-level mutable state" is a valid, checkable statement.

## 7. Errors
| Exception | Raised when | HTTP status | Error code |

## 8. State machine (if the entity has a lifecycle)
| From | Event | To | Guard | Side effects |

## 9. Test seams
| Behaviour | Seam | Notes |
|---|---|---|
| schema rejects discount > cap | schema unit | |
| list_deals avoids N+1 | repository + real DB, query count | |
| approver-only approve | API + dependency_overrides | 403 for others |

## 10. Traceability
| Requirement | Spec section | Endpoint(s) |

## 11. Open questions / ADRs
```
