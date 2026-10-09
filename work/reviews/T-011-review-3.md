# Review T-011 round 3 — changes-requested

Gates: ruff — not run · format — not run · mypy — not run · pytest — not run · Redis integration — not run. This review was performed against branch `implement/T-011-redis-multiworker`. The remote GitHub review environment cannot execute the repository's local `uv` quality gates, so green status is not claimed.

## Spec — findings

### MAJOR M1 — Cross-worker Redis delivery has no committed integration test

**Spec:** T-011 acceptance criterion: “Given publisher and SSE subscriber requests handled by different Uvicorn workers, When an appointment event is committed, Then Redis Pub/Sub delivers the event to the subscriber worker (NFR-5, ADR 0003).” ADR 0003 requires an integration test using distinct publisher/subscriber instances.

**Files:** `backend/src/app/services/event_broadcaster.py:43-55, 109-120`; `backend/tests/services/test_event_broadcaster.py`; `backend/README.md`.

The implementation has a Redis listener and publisher, and the unit tests cover local in-memory fan-out. However, the documented `TEST_REDIS_URL` cross-instance integration test is not present in the branch's test tree (the documented `backend/tests/integration/test_redis_event_broker.py` path returns 404). Thus the core new production guarantee—Redis publication received by a separate broadcaster/worker—is not regression-tested.

**Fix direction:** add and commit a Redis integration test that starts two independent `EventBroadcaster` instances against `TEST_REDIS_URL`, subscribes on instance B, publishes through instance A, asserts the full event reaches B, and reliably stops both instances. Ensure the test skips only when `TEST_REDIS_URL` is unset, and run it with Redis available.

## Standards — findings

No confirmed new architecture or code-smell violation found in the reviewed paths. Positive changes include bounded queues with an explicit resync event, lifespan-managed Redis resources, structured reconnect logging, a dedicated short-lived authentication session for SSE, and callbacks dispatched after a successful commit.

## Tests — findings

### MAJOR T1 — Required validation is unverified

The ticket requires the four repository quality gates and a Redis-backed integration test before marking T-011 done. The ticket's implementation log explicitly says these gates and the Redis integration test have not been run in the remote editing environment. The lockfile now includes Redis, but that alone does not prove the dependency graph and implementation pass the checks.

**Fix direction:** run from the repository root (or the documented backend directory):
- `uv run --directory backend ruff check`
- `uv run --directory backend ruff format --check src/ tests/`
- `uv run --directory backend mypy src`
- `uv run --directory backend pytest -q`
- Run the Redis cross-instance integration test with `TEST_REDIS_URL` configured.
Record exact results in the ticket implementation log.

The direct async-generator tests appropriately avoid HTTPX ASGITransport for an infinite stream and now assert payload fields for booking, rescheduling, cancellation, and status transitions. They do not substitute for the missing cross-instance Redis test.

## Summary

| Severity | Count | Key |
|---|---:|---|
| Blocker | 0 | — |
| Major | 2 | Missing Redis cross-instance integration test; required quality gates/integration run unverified |
| Minor | 0 | — |
| Nit | 0 | — |

**Single worst issue:** the defining multi-worker delivery guarantee is not covered by a committed Redis integration test.

**Verdict: changes-requested.** Do not mark T-011 done until the Redis integration test is added and executed and all quality gates pass.
