# Concurrency, Middleware, and Operational Patterns

## Structured Concurrency with `asyncio.TaskGroup`

For fan-out async operations (e.g. running multiple independent service tasks simultaneously), use `asyncio.TaskGroup`.
All spawned tasks run concurrently and are guaranteed to either all complete or cancel gracefully if an exception is raised.

```python
import asyncio
from typing import Any


class OrderService:
    async def process_order(self, order_id: int) -> dict[str, Any]:
        async with asyncio.TaskGroup() as tg:
            compliance = tg.create_task(self._check_compliance(order_id))
            risk = tg.create_task(self._score_risk(order_id))
            invoice = tg.create_task(self._generate_invoice(order_id))

        return {
            "order_id": order_id,
            "risk_score": risk.result(),
            "invoice_id": invoice.result(),
        }
```

## Offloading CPU-Bound Work with `run_in_executor`

Heavy CPU calculations (e.g. cryptographic signing, compression, complex numerical calculation) will block the async event loop if run directly.
Offload them to the default thread pool executor:

```python
import asyncio


def _heavy_risk_calculation(order_id: int) -> int:
    total = sum(i % 7 for i in range(2_000_000))
    return total % 100


async def score_risk(order_id: int) -> int:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _heavy_risk_calculation, order_id)
```

## Handling Exception Groups (`except*`)

Tasks running inside a `TaskGroup` raise `ExceptionGroup` upon failure. Catch individual task error types cleanly using Python 3.11+ `except*`:

```python
from fastapi import HTTPException


try:
    result = await order_service.process_order(order_id)
except* ComplianceError as eg:
    raise HTTPException(status_code=409, detail="Order failed compliance check")
```

## Global Middleware: Correlation IDs & Error Handling

Use an HTTP middleware to:
1. Extract or generate an `X-Correlation-ID` header.
2. Catch unhandled errors, log them with structured context, and return a sanitized 500 JSON response.
3. Attach the `X-Correlation-ID` to all outbound responses for distributed tracing.

```python
import logging
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("app")
app = FastAPI()


@app.middleware("http")
async def correlation_and_error_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled server error", extra={"correlation_id": correlation_id})
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "correlation_id": correlation_id},
            headers={"X-Correlation-ID": correlation_id},
        )
    response.headers["X-Correlation-ID"] = correlation_id
    return response


@app.get("/health")
def health():
    return {"status": "ok"}
```

## Thread Safety for Shared State

When keeping in-memory caches, rate limiters, or aggregate counters across async requests, protect shared mutable data with `threading.Lock`.
This ensures safety across multi-threaded workers and Python 3.13+ free-threaded (no-GIL) runtimes:

```python
import threading

_cache: dict[str, int] = {}
_lock = threading.Lock()


def increment_metric(key: str) -> int:
    with _lock:
        val = _cache.get(key, 0) + 1
        _cache[key] = val
        return val
```
