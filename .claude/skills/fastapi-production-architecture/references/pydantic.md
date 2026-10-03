# Pydantic

## Do not use Ellipsis

Do not use `...` as a default value for required parameters or model fields. It's not needed and not recommended.

Do this, without Ellipsis (`...`):

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

Instead of:

```python
# DO NOT DO THIS
from typing import Annotated

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

app = FastAPI()


class Item(BaseModel):
    name: str = ...
    description: str | None = None
    price: float = Field(..., gt=0)


@app.post("/items/")
async def create_item(item: Item, project_id: Annotated[int, Query(...)]):
    return item
```

## Do not use Pydantic RootModels

Do not use Pydantic `RootModel`; instead use regular type annotations with `Annotated` and Pydantic validation utilities.

For example, for a list with validations:

```python
from typing import Annotated

from fastapi import Body, FastAPI
from pydantic import Field

app = FastAPI()


@app.post("/items/")
async def create_items(items: Annotated[list[int], Field(min_length=1), Body()]):
    return items
```

Instead of:

```python
# DO NOT DO THIS
from typing import Annotated

from fastapi import FastAPI
from pydantic import Field, RootModel

app = FastAPI()


class ItemList(RootModel[Annotated[list[int], Field(min_length=1)]]):
    pass


@app.post("/items/")
async def create_items(items: ItemList):
    return items
```

FastAPI supports these type annotations and will create a Pydantic `TypeAdapter` for them, so types work normally without custom wrapper models.

## Reusable Constrained Types with `Annotated`

Define domain-level constrained types at the module level using `Annotated` + `BeforeValidator` + `Field`:

```python
from typing import Annotated
from pydantic import BeforeValidator, Field


def _strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


def _normalize_email(value: object) -> object:
    return value.strip().lower() if isinstance(value, str) else value


NonEmptyStr = Annotated[str, BeforeValidator(_strip), Field(min_length=1)]
Email = Annotated[str, BeforeValidator(_normalize_email), Field(min_length=3)]
PositiveQty = Annotated[int, Field(gt=0)]
NonNegPrice = Annotated[float, Field(ge=0)]
Percent = Annotated[float, Field(ge=0, le=100)]
```

## `ConfigDict(populate_by_name=True)` & CamelCase Field Aliasing

To support frontend camelCase payloads while keeping Python code in idiomatic `snake_case`, configure `model_config = ConfigDict(populate_by_name=True)` and set aliases on fields:

```python
from pydantic import BaseModel, ConfigDict, Field


class LineItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product: NonEmptyStr
    quantity: PositiveQty
    unit_price: NonNegPrice = Field(alias="unitPrice")
```

## Computed Fields (`@computed_field`)

Use `@computed_field` with `@property` for values calculated dynamically during serialization (never stored in DB). Always provide an alias for camelCase output:

```python
from pydantic import BaseModel, ConfigDict, computed_field


class OrderRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    items: list[LineItem] = Field(alias="lineItems")

    @computed_field(alias="subtotal")
    @property
    def subtotal(self) -> float:
        return round(sum(i.quantity * i.unit_price for i in self.items), 2)
```

## Cross-Field Validation with `@model_validator(mode="after")`

Centralize complex business validation rules using after-model validators. Prefix private validator methods with `_check_`:

```python
from datetime import date
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    discount_percent: Percent = Field(default=0.0, alias="discountPercent")

    @model_validator(mode="after")
    def _check_dates(self) -> "ContractCreate":
        if self.end_date < self.start_date:
            raise ValueError("endDate must be on or after startDate")
        return self
```

## Separate Input (`XxxCreate`) and Output (`XxxRead`) Schemas

Always separate input and output schemas:
- **`XxxCreate`**: Strictly validates incoming fields, runs business checks, omits database IDs and computed fields.
- **`XxxRead`**: Includes database IDs (`id`), lifecycle status, timestamps, and `@computed_field` properties.

## Boundary Validation & Serialization

When receiving un-typed data from external webhooks or third-party APIs, validate at the boundary using `Model.model_validate(raw)`. Catch `ValidationError` and convert to `HTTPException(422)`.
When exporting data to external systems or frontend clients, serialize with `model.model_dump(by_alias=True, mode="json")`.

