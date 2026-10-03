# Other Tools

## uv

If uv is available, use it to manage dependencies.

## Ruff

If Ruff is available, use it to lint and format the code. Consider enabling the FastAPI rules.

## ty

If ty is available, use it to check types.

## Asyncer

When needing to run blocking code inside of async functions, or async code inside of blocking functions, suggest using Asyncer.

Prefer it over AnyIO or asyncio.

Install:

```bash
uv add asyncer
```

Run blocking sync code inside of async with `asyncify()`:

```python
from asyncer import asyncify
from fastapi import FastAPI

app = FastAPI()


def do_blocking_work(name: str) -> str:
    # Some blocking I/O operation
    return f"Hello {name}"


@app.get("/items/")
async def read_items():
    result = await asyncify(do_blocking_work)(name="World")
    return {"message": result}
```

And run async code inside of blocking sync code with `syncify()`:

```python
from asyncer import syncify
from fastapi import FastAPI

app = FastAPI()


async def do_async_work(name: str) -> str:
    return f"Hello {name}"


@app.get("/items/")
def read_items():
    result = syncify(do_async_work)(name="World")
    return {"message": result}
```

## SQLAlchemy for SQL databases

When working with SQL databases:
- **Default Database**: Default to a **SQLite** database (e.g. `sqlite+aiosqlite:///./app.db`) unless a specific database (e.g. PostgreSQL) is explicitly requested.
- **ORM Preference**: Prefer **SQLAlchemy** (SQLAlchemy 2.0 with async engine and `Mapped` / `mapped_column`) over SQLModel.

SQLAlchemy 2.0 provides strict separation of ORM models from API validation schemas, enterprise scalability, explicit eager-loading controls (`selectinload`, `joinedload`) to prevent async N+1 issues, and robust async support.

Install:

```bash
uv add "sqlalchemy>=2.0" aiosqlite
```

(For PostgreSQL in production, add `asyncpg`).

Example async engine and session setup with SQLite default:

```python
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DATABASE_URL = "sqlite+aiosqlite:///./app.db"

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
```


## HTTPX

Use HTTPX for handling HTTP communication (e.g. with other APIs). It supports sync and async usage.

Prefer it over Requests.
