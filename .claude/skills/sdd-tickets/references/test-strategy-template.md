# Test strategy template (work/test-strategy.md)

```markdown
# Test strategy
## 1. Principles
- Test behaviour through public seams, not private functions.
- Expected values come from the PRD/spec, not from re-running the implementation's logic.
- One red test at a time; commit only when the full suite is green.

## 2. Seams
| Seam | Tooling | Used for |
|---|---|---|
| Schema unit | pytest | validators, computed fields, aliases |
| Repository + real DB | pytest-asyncio, test database (transaction rollback per test) | queries, constraints, N+1 guards |
| Service with fakes | pytest | business logic with collaborators injected |
| API via dependency graph | httpx.AsyncClient + app.dependency_overrides | status codes, auth, serialization |
| Streaming | httpx streaming | SSE frames, ids, resume |

## 3. Fixtures and builders
Database session, client, authenticated user per role, factory functions for each entity.

## 4. Cross-cutting suites
| Suite | Purpose | Owner ticket |
|---|---|---|
| Authorization matrix | every endpoint × role → expected 200/401/403 | |
| Query-count guards | list endpoints stay constant-query (no N+1) | |
| OpenAPI snapshot | public contract does not drift unintentionally | |
| Error-shape | every error path returns the standard body | |
| Concurrency/failure | TaskGroup failures surface as intended | |
| Multi-worker state | no module-level mutable state (static check) | |

## 5. CI order
ruff → mypy → unit → integration → API → cross-cutting.

## 6. Coverage expectations
Target and how it is measured. Coverage is a signal, not the goal.
```
