---
name: fastapi-production-architecture
description: FastAPI best practices and conventions. Use when working with FastAPI APIs, Pydantic models, dependencies, streaming responses including Server-Sent Events (SSE), and serving frontend apps. Keeps FastAPI code clean and up to date with the latest features and patterns.
---

# FastAPI

Official FastAPI skill to write code with best practices, keeping up to date with new versions and features.

## Quick Reference

* Project Architecture: use a flat-packages-inside-`app/` layered structure (`main.py`, `schemas.py`, `models/`, `db/`, `services/`, `api/`, `routers/`); see [Project Architecture](#project-architecture) and [the project structure reference](references/project-structure.md).
* Database & ORM: default to **SQLite** (`sqlite+aiosqlite:///./app.db`) unless another database is specified; prefer **SQLAlchemy** (SQLAlchemy 2.0 async with `Mapped` and `mapped_column`) over SQLModel; see [Database & ORM](#database-and-orm) and [the database reference](references/database.md).
* Serve frontend apps: use `app.frontend()` or `router.frontend()` for built frontend assets; see [Serve Frontend Apps](#serve-frontend-apps).
* Server-Sent Events (SSE): use `response_class=EventSourceResponse` and `yield`; see [Streaming](#streaming-json-lines-sse-bytes) and [the streaming reference](references/streaming.md).
* JSON Lines and byte streaming: see [the streaming reference](references/streaming.md).
* Dependencies: use `Annotated[..., Depends(...)]`; see [Dependency Injection](#dependency-injection) and [the dependency injection reference](references/dependencies.md) for `yield`, scopes, dependency trees, and role guards.
* Response models: prefer return types; use `response_model` when the public response schema differs from the internal return value; see [the response reference](references/responses.md).
* Pydantic models: do not use ellipsis or `RootModel`; use reusable constrained types, `ConfigDict(populate_by_name=True)`, and `@computed_field`; see [the Pydantic reference](references/pydantic.md).
* Routing: declare router-level prefix, tags, and shared dependencies on the `APIRouter`; see [the path operation reference](references/path-operations.md).
* Concurrency & Ops: use `asyncio.TaskGroup`, `run_in_executor`, correlation ID middleware, and `threading.Lock`; see [the concurrency reference](references/concurrency-and-ops.md).
* Tooling and related libraries: use uv, Ruff, ty, Asyncer, SQLAlchemy, and HTTPX when applicable; see [the other tools reference](references/other-tools.md).


## Use the `fastapi` CLI

Run the development server on localhost with reload:

```bash
fastapi dev
```

Run the production server:

```bash
fastapi run
```

Prefer declaring the entrypoint in `pyproject.toml`:

```toml
[tool.fastapi]
entrypoint = "my_app.main:app"
```

When adding the entrypoint is not possible, or the user explicitly asks not to, pass the app file path:

```bash
fastapi dev my_app/main.py
```

## Use `Annotated`

Always prefer the `Annotated` style for parameter and dependency declarations. It keeps function signatures working in other contexts, respects the types, and allows reusability.

Use `Annotated` for parameter declarations, including `Path`, `Query`, `Header`, etc.:

```python
from typing import Annotated

from fastapi import FastAPI, Path, Query

app = FastAPI()


@app.get("/items/{item_id}")
async def read_item(
    item_id: Annotated[int, Path(ge=1, description="The item ID")],
    q: Annotated[str | None, Query(max_length=50)] = None,
):
    return {"message": "Hello World"}
```

Use `Annotated` for dependencies with `Depends()`. Unless asked not to, create a new type alias for the dependency to allow reusing it:

```python
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


def get_current_user():
    return {"username": "johndoe"}


CurrentUserDep = Annotated[dict, Depends(get_current_user)]


@app.get("/items/")
async def read_item(current_user: CurrentUserDep):
    return {"message": "Hello World"}
```

## Do not use Ellipsis for *path operations* or Pydantic models

Do not use `...` as a default value for required parameters or model fields. It's not needed and not recommended.

```python
from typing import Annotated

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

app = FastAPI()


class Item(BaseModel):
    name: str
    description: str | None = None
    price: float = Field(gt=0)


@app.post("/items/")
async def create_item(item: Item, project_id: Annotated[int, Query()]):
    return item
```

See [the Pydantic reference](references/pydantic.md) for more details.

## Return Type or Response Model

When possible, include a return type. It will be used to validate, filter, document, and serialize the response.

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str
    description: str | None = None


@app.get("/items/me")
async def get_item() -> Item:
    return Item(name="Plumbus", description="All-purpose home device")
```

Return types or response models filter data to avoid exposing sensitive information, and they let Pydantic serialize the data on the Rust side for performance.

Use `response_model` when the type you return is not the same as the public schema you want to validate, filter, document, and serialize. See [the response reference](references/responses.md).

## Performance

Do not use `ORJSONResponse` or `UJSONResponse`, they are deprecated.

Instead, declare a return type or response model. Pydantic will handle the data serialization on the Rust side.

## Including Routers

When declaring routers, prefer to add router-level parameters like prefix, tags, and shared dependencies to the router itself instead of in `include_router()`.

```python
from fastapi import APIRouter, Depends, FastAPI

app = FastAPI()


def get_current_user():
    return {"username": "johndoe"}


router = APIRouter(
    prefix="/items",
    tags=["items"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/")
async def list_items():
    return []


app.include_router(router)
```

See [the path operation reference](references/path-operations.md) for more routing patterns.

## Serve Frontend Apps

Use `app.frontend()` to serve a built static frontend app, for example a directory generated by Vite, Astro, Angular, Svelte, Vue, or a similar tool.

```python
from fastapi import FastAPI

app = FastAPI()

app.frontend("/", directory="dist")
```

Use `router.frontend()` when the frontend belongs to an `APIRouter`; normal router prefix behavior applies when the router is included.

```python
from fastapi import APIRouter, FastAPI

app = FastAPI()
router = APIRouter(prefix="/admin")

router.frontend("/", directory="admin-dist")
app.include_router(router)
```

`app.frontend()` and `router.frontend()` are low-priority routes: regular API routes are matched first, then frontend files and client-side routing fallbacks. Use this for single-page apps and built frontend assets instead of mounting `StaticFiles` manually.

## Dependency Injection

Use dependencies when the logic can't be declared in Pydantic validation, depends on external resources, needs cleanup with `yield`, or is shared across endpoints.

Apply shared dependencies at the router level via `dependencies=[Depends(...)]`.

See [the dependency injection reference](references/dependencies.md) for detailed patterns including `yield` with `scope`, and class dependencies.

## Async vs Sync *path operations*

Use `async` *path operations* only when fully certain that the logic called inside is compatible with async and await, and that it doesn't block.

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/async-items/")
async def read_async_items():
    data = await some_async_library.fetch_items()
    return data


@app.get("/items/")
def read_items():
    data = some_blocking_library.fetch_items()
    return data
```

In case of doubt, or by default, use regular `def` functions. They will be run in a threadpool so they don't block the event loop. The same rules apply to dependencies.

Make sure blocking code is not run inside of `async` functions. The logic will work, but will damage performance heavily.

When needing to mix blocking and async code, see Asyncer in [the other tools reference](references/other-tools.md).

## Streaming (JSON Lines, SSE, bytes)

To stream Server-Sent Events, use `response_class=EventSourceResponse` and `yield` items from the endpoint.

```python
from collections.abc import AsyncIterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent

app = FastAPI()


@app.get("/events", response_class=EventSourceResponse)
async def stream_events() -> AsyncIterable[ServerSentEvent]:
    yield ServerSentEvent(data={"status": "started"}, event="status", id="1")
```

Plain objects are automatically JSON-serialized as `data:` fields. Use `ServerSentEvent` for full control over SSE fields (`event`, `id`, `retry`, `comment`) and `raw_data` for pre-formatted strings.

See [the streaming reference](references/streaming.md) for JSON Lines, Server-Sent Events (`EventSourceResponse`, `ServerSentEvent`), and byte streaming (`StreamingResponse`) patterns.

## Tooling

See [the other tools reference](references/other-tools.md) for details on uv, Ruff, ty for package management, linting, type checking, formatting, etc.

## Other Libraries

See [the other tools reference](references/other-tools.md) for details on other libraries:

* Asyncer for handling async and await, concurrency, mixing async and blocking code, prefer it over AnyIO or asyncio.
* SQLAlchemy (2.0 async) for working with SQL databases, defaulting to SQLite unless another database is specified; prefer it over SQLModel.
* HTTPX for interacting with HTTP (other APIs), prefer it over Requests.

## Project Architecture

For production applications, follow a flat-packages-inside-`app/` layered architecture:

* `app/main.py`: Thin bootstrap, lifespan context manager, middleware, and router registration. No business logic.
* `app/schemas.py`: Single source of truth for all Pydantic v2 schemas (strict `XxxCreate` models, rich `XxxRead` models with `@computed_field`).
* `app/models/`: SQLAlchemy 2.0 declarative ORM models (`Mapped[T] = mapped_column(...)`).
* `app/db/session.py`: Async engine defaulting to SQLite (`sqlite+aiosqlite:///./app.db`) and `async_sessionmaker(engine, expire_on_commit=False)`.
* `app/db/repository.py`: Stateless async data-access functions (CRUD queries, eager loading with `selectinload`/`joinedload`).
* `app/services/`: Domain business logic classes constructed via `__init__` dependency injection.
* `app/api/deps.py`: Dependency injection graph, async session yield dependency with commit/rollback/close, and exported `*Dep` type aliases.
* `app/routers/`: Thin HTTP endpoint handlers consuming `*Dep` aliases.

See [the project structure reference](references/project-structure.md).

## Database and ORM

Default to a **SQLite** database unless another database is specified:

```python
DATABASE_URL = "sqlite+aiosqlite:///./app.db"
```

Use SQLAlchemy 2.0 async engine and sessionmaker:

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
```

Manage transactions per-request with an async generator yield dependency:

```python
from collections.abc import AsyncGenerator


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    session = SessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
```

Prevent N+1 query bugs in async with explicit eager loading:
* Use `selectinload` for 1-to-many collections.
* Use `joinedload` for many-to-one scalars.

See [the database reference](references/database.md).

## Concurrency and Production Middleware

* Use `asyncio.TaskGroup` for fan-out concurrent operations and handle failures with `except*`.
* Offload CPU-bound calculations using `loop.run_in_executor(None, sync_fn)`.
* Register global HTTP middleware for correlation ID propagation (`X-Correlation-ID`) and centralized unhandled exception logging.
* Protect shared in-memory mutable state across requests with `threading.Lock`.

See [the concurrency reference](references/concurrency-and-ops.md).


## Do not use Pydantic RootModels

Do not use Pydantic `RootModel`; instead use regular type annotations with `Annotated` and Pydantic validation utilities.

```python
from typing import Annotated

from fastapi import Body, FastAPI
from pydantic import Field

app = FastAPI()


@app.post("/items/")
async def create_items(items: Annotated[list[int], Field(min_length=1), Body()]):
    return items
```

FastAPI supports these type annotations and will create a Pydantic `TypeAdapter` for them, so types work normally without custom wrapper models. See [the Pydantic reference](references/pydantic.md).

## Use one HTTP operation per function

Don't mix HTTP operations in a single function. Having one function per HTTP operation helps separate concerns and organize the code.

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str


@app.get("/items/")
async def list_items():
    return []


@app.post("/items/")
async def create_item(item: Item):
    return item
```

See [the path operation reference](references/path-operations.md) for more examples.
