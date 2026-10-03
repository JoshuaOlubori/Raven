# Production Project Structure and Layering

For production applications, follow a **flat-packages-inside-`app/`** layered architecture. This separates concerns cleanly between routing, business logic, persistence, and external schemas.

## Directory Layout

```text
project-root/
├── pyproject.toml            # Dependencies and entrypoint configuration
└── app/
    ├── __init__.py
    ├── main.py               # Lifespan, FastAPI instantiation, middleware, routers, /health
    ├── schemas.py            # Centralized Pydantic v2 schemas (Create/Read models)
    ├── api/
    │   ├── __init__.py
    │   ├── deps.py           # Dependency injection graph & Annotated *Dep aliases
    │   └── auth.py           # CurrentUser dataclass & auth dependencies
    ├── db/
    │   ├── __init__.py
    │   ├── session.py        # Engine, async_sessionmaker, init_db()
    │   └── repository.py     # Stateless async queries (CRUD, selectinload/joinedload)
    ├── models/
    │   ├── __init__.py
    │   └── <entity>.py       # SQLAlchemy 2.0 ORM models (DeclarativeBase, Mapped)
    ├── routers/
    │   ├── __init__.py
    │   └── <domain>.py       # Thin APIRouter endpoints consuming *Dep aliases
    └── services/
        ├── __init__.py
        └── <domain>_service.py # Business logic classes with constructor injection
```

## Layer Responsibilities

1. **`app/main.py`**:
   - Thin application orchestrator.
   - Manages startup/shutdown via `lifespan(app: FastAPI)` (e.g. `await init_db()`).
   - Registers global middleware (e.g. Correlation ID & error handling).
   - Includes domain routers.
   - Hosts `/health` endpoint.
   - Contains NO business logic.

2. **`app/schemas.py`**:
   - Single source of truth for Pydantic v2 request/response schemas.
   - Clear separation between `XxxCreate` (strict validation) and `XxxRead` (public view).
   - Includes reusable constrained types with `Annotated` + `BeforeValidator`.
   - Uses `ConfigDict(populate_by_name=True)` for camelCase JSON compatibility.

3. **`app/models/`**:
   - SQLAlchemy 2.0 ORM models mapped to database tables.
   - Defines table structures, relationships, cascade rules, and indexes.

4. **`app/db/`**:
   - `session.py`: async engine (defaulting to SQLite `sqlite+aiosqlite:///./app.db`) and `async_sessionmaker(..., expire_on_commit=False)`.
   - `repository.py`: stateless async data-access functions accepting `AsyncSession`. Eliminates raw SQL in routers and services.

5. **`app/services/`**:
   - Domain business logic encapsulated in classes.
   - Receives dependencies (e.g., `AsyncSession`, `AuditService`) via `__init__` constructor injection.
   - Coordinates repository calls, business validations, and domain events.

6. **`app/api/deps.py`**:
   - Dependency injection wiring hub.
   - Implements yield dependencies for transactional session management.
   - Assembles dependency trees.
   - Exports typed `Annotated` aliases (`DbSessionDep`, `CurrentUserDep`, `ItemServiceDep`).

7. **`app/routers/`**:
   - Thin HTTP boundary controllers.
   - Validates incoming parameters via FastAPI and Pydantic schemas.
   - Injects services using `*Dep` aliases.
   - Translates domain results into HTTP responses or raises `HTTPException`.

## Naming Conventions

| Element | Convention | Example |
| :--- | :--- | :--- |
| File / module | `snake_case.py` | `deal_service.py`, `repository.py` |
| Pydantic schemas | `PascalCase` with `Create` / `Read` | `DealCreate`, `DealRead` |
| ORM models | `PascalCase` singular noun | `Deal`, `Customer` |
| Database tables | `snake_case` plural | `deals`, `customers` |
| Dep type aliases | `PascalCase` ending in `Dep` | `DbSessionDep`, `DealServiceDep` |
| Dep factory functions | `get_` prefix | `get_db_session`, `get_deal_service` |
| Service classes | `PascalCase` ending in `Service` | `DealService`, `AuditService` |
| Repository functions | `verb_noun` async functions | `get_deal`, `list_deals_with_items` |
| Schema validators | `_check_` prefix | `_check_dates`, `_check_discount_cap` |
| Constrained types | `PascalCase` descriptive | `NonEmptyStr`, `PositiveQty`, `Email` |
| Frontend JSON aliases | `camelCase` | `"unitPrice"`, `"contactEmail"` |
