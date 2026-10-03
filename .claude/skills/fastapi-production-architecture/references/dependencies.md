# Dependency Injection

Use dependencies when:

* They can't be declared in Pydantic validation and require additional logic
* The logic depends on external resources or could block in any other way
* Other dependencies need their results (it's a sub-dependency)
* The logic can be shared by multiple endpoints to do things like error early, handle authentication, etc.
* They need to handle cleanup (e.g., DB sessions, file handles), using dependencies with `yield`
* Their logic needs input data from the request, like headers, query parameters, etc.

## Dependencies with `yield` and `scope`

When using dependencies with `yield`, they can have a `scope` that defines when the exit code is run.

Use the default scope `"request"` to run the exit code after the response is sent back.

```python
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import SessionLocal

app = FastAPI()


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


Use the scope `"function"` when they should run the exit code after the response data is generated but before the response is sent back to the client.

```python
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


def get_username():
    try:
        yield "Rick"
    finally:
        print("Clean up before response is sent")

UserNameDep = Annotated[str, Depends(get_username, scope="function")]

@app.get("/users/me")
def get_user_me(username: UserNameDep):
    return username
```

## Class Dependencies

Avoid creating class dependencies when possible.

If a class is needed, instead create a regular function dependency that returns a class instance.

Do this:

```python
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


@dataclass
class DatabasePaginator:
    offset: int = 0
    limit: int = 100
    q: str | None = None

    def get_page(self) -> dict:
        # Simulate a page of data
        return {
            "offset": self.offset,
            "limit": self.limit,
            "q": self.q,
            "items": [],
        }


def get_db_paginator(
    offset: int = 0, limit: int = 100, q: str | None = None
) -> DatabasePaginator:
    return DatabasePaginator(offset=offset, limit=limit, q=q)


PaginatorDep = Annotated[DatabasePaginator, Depends(get_db_paginator)]


@app.get("/items/")
async def read_items(paginator: PaginatorDep):
    return paginator.get_page()
```

instead of this:

```python
# DO NOT DO THIS
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


class DatabasePaginator:
    def __init__(self, offset: int = 0, limit: int = 100, q: str | None = None):
        self.offset = offset
        self.limit = limit
        self.q = q

    def get_page(self) -> dict:
        # Simulate a page of data
        return {
            "offset": self.offset,
            "limit": self.limit,
            "q": self.q,
            "items": [],
        }


@app.get("/items/")
async def read_items(paginator: Annotated[DatabasePaginator, Depends()]):
    return paginator.get_page()
```

## Dependency Trees & Centralized `*Dep` Aliases (`app/api/deps.py`)

Centralize all dependency factory definitions and type aliases in `app/api/deps.py`. Routers should **only** import `Annotated` type aliases ending in `Dep`, never raw factory functions.

FastAPI caches dependencies with `yield` per-request by default. If multiple services (e.g. `ItemService` and `ApprovalService`) depend on `get_db_session`, they automatically receive the **same `AsyncSession`** instance within that request, executing within a single shared transaction.

```python
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Annotated
import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import SessionLocal
from app.services.item_service import ItemService
from app.services.audit_service import AuditLogService


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


@dataclass
class RequestContext:
    correlation_id: str
    user_id: int | None = None


async def get_request_context(
    x_correlation_id: Annotated[str | None, Header()] = None,
) -> RequestContext:
    return RequestContext(correlation_id=x_correlation_id or str(uuid.uuid4()))


def get_audit_service(
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> AuditLogService:
    return AuditLogService(ctx.correlation_id, ctx.user_id)


def get_item_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    audit: Annotated[AuditLogService, Depends(get_audit_service)],
) -> ItemService:
    # Service classes receive dependencies via constructor injection
    return ItemService(session, audit)


# Annotated type aliases — routers only import these
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
RequestContextDep = Annotated[RequestContext, Depends(get_request_context)]
AuditServiceDep = Annotated[AuditLogService, Depends(get_audit_service)]
ItemServiceDep = Annotated[ItemService, Depends(get_item_service)]
```

## Role-Based Route Guards

Implement reusable role guards using dependency factories with closures:

```python
@dataclass
class CurrentUser:
    id: int
    roles: list[str]
    region: str | None = None


async def get_current_user(...) -> CurrentUser:
    ...


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_roles(*allowed: str):
    async def _guard(user: CurrentUserDep) -> CurrentUser:
        if not set(allowed) & set(user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role for this operation",
            )
        return user

    return _guard
```

Use the guard at the router or endpoint level:

```python
@router.post(
    "/{item_id}/approve",
    dependencies=[Depends(require_roles("manager", "finance"))],
)
async def approve_item(item_id: int, item_service: ItemServiceDep):
    return await item_service.approve(item_id)
```

