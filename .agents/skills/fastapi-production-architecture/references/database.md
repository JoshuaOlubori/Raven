# Database with SQLAlchemy 2.0 (Async)

## SQLite Default

Always default to a **SQLite** database unless a specific database is explicitly requested.

- Use the async driver `aiosqlite` with the connection string `sqlite+aiosqlite:///./app.db`.
- To swap to PostgreSQL in production environments, change the URL to `postgresql+asyncpg://...` and add `asyncpg`.

## Engine and Session Setup (`app/db/session.py`)

Always configure `expire_on_commit=False` on `async_sessionmaker` to prevent async lazy-loading attribute errors (`MissingGreenlet`) after a transaction commits.

```python
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.models.base import Base

DATABASE_URL = "sqlite+aiosqlite:///./app.db"

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

## ORM Models with SQLAlchemy 2.0 (`app/models/`)

Use class-based `DeclarativeBase` (never the legacy `declarative_base()` factory).
Declare all fields using `Mapped[T]` and `mapped_column()`.
Declare relationships using `Mapped[list[Child]] = relationship(back_populates="...", cascade="all, delete-orphan")`.

```python
from datetime import date
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """2.0 declarative base."""
    pass


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)

    items: Mapped[list["Item"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    price: Mapped[float] = mapped_column(default=0.0)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))

    customer: Mapped["Customer"] = relationship(back_populates="items")
```

## Repository Pattern (`app/db/repository.py`)

Keep data access clean, centralized, and stateless. Repository functions are async functions that take `session: AsyncSession` as their first parameter.

```python
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from app.models.item import Customer, Item


async def get_item(session: AsyncSession, item_id: int) -> Item | None:
    return await session.get(Item, item_id)


async def list_items(session: AsyncSession) -> list[Item]:
    result = await session.scalars(select(Item))
    return list(result.all())


async def create_item(
    session: AsyncSession,
    *,
    title: str,
    price: float,
    customer_id: int,
) -> Item:
    item = Item(title=title, price=price, customer_id=customer_id)
    session.add(item)
    await session.flush()
    return item
```

## Eliminating N+1 Queries: Eager Loading

In async SQLAlchemy, accessing an un-loaded relationship outside of the initial query raises an asyncio/greenlet error instead of quietly issuing a background query.

Always specify eager loading in query functions:

1. **`selectinload`** for one-to-many collections (uses a fast secondary `SELECT ... WHERE id IN (...)`):
   ```python
   async def list_customers_with_items(session: AsyncSession) -> list[Customer]:
       stmt = select(Customer).options(selectinload(Customer.items))
       result = await session.scalars(stmt)
       return list(result.all())
   ```

2. **`joinedload`** for many-to-one or one-to-one scalars (uses a single SQL `JOIN`):
   ```python
   async def get_item_with_customer(session: AsyncSession, item_id: int) -> Item | None:
       stmt = (
           select(Item)
           .where(Item.id == item_id)
           .options(joinedload(Item.customer))
       )
       return await session.scalar(stmt)
   ```

## Database Session Lifecycle Dependency (`app/api/deps.py`)

Manage transaction safety per-request with an async generator yield dependency:
- Injects `AsyncSession` into route handlers or service constructors
- Commits transaction on clean exit
- Rolls back on any exception
- Closes the session in a `finally` block to release connection resources

```python
from collections.abc import AsyncGenerator
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import SessionLocal


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


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
```
