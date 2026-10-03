# Dental Services Catalog Module Spec

_Status: approved · Date: 2026-10-03 · Covers: R-6_

## 1. Responsibility
This module owns the definition and management of dental procedures/services offered by the clinic (e.g. Routine Cleaning, Root Canal, Crown Fitting), including procedure standard duration in minutes and active status toggle.
It explicitly does NOT own appointment scheduling or dentist shift assignment.

---

## 2. Layer 1 — Contracts (Standard §3)

### Shared Constrained Types
```python
ServiceDuration = Annotated[int, Field(gt=0, le=480, description="Duration in minutes (e.g. 15, 30, 45, 60, 90)")]
NonEmptyStr = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=100)]
```

### Schemas Table
| Schema | Purpose | Fields (name: type, optional?) | Validators / computed fields |
|---|---|---|---|
| `ServiceCreate` | Procedure catalog creation | `name: NonEmptyStr`, `description: str | None = None`, `duration_minutes: ServiceDuration`, `is_active: bool = True` | `duration_minutes` must be > 0 and <= 480 minutes (8 hrs) |
| `ServiceUpdate` | Procedure catalog updates | All fields optional: `name`, `description`, `duration_minutes`, `is_active` | `duration_minutes` must be > 0 if provided |
| `ServiceRead` | Public procedure representation | `id: UUID`, `name: NonEmptyStr`, `description: str | None`, `duration_minutes: int`, `is_active: bool`, `created_at: datetime` | CamelCase aliases (`durationMinutes`, `isActive`) |

---

## 3. Layer 2 — Persistence (Standard §4)

### ORM Model: `DentalService` (`app/models/service.py`)
| Model | Columns | Relationships | Indexes / Constraints |
|---|---|---|---|
| `DentalService` | `id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)`<br>`name: Mapped[str] = mapped_column(unique=True, index=True)`<br>`description: Mapped[str | None]`<br>`duration_minutes: Mapped[int]`<br>`is_active: Mapped[bool] = mapped_column(default=True, index=True)`<br>`created_at: Mapped[datetime] = mapped_column(default=utcnow)` | `appointments: Mapped[list["Appointment"]] = relationship(back_populates="service")` | Unique index on `name`. Index on `is_active`. |

### Repository Signatures (`app/db/repository.py`)
```python
async def get_service_by_id(session: AsyncSession, service_id: UUID) -> DentalService | None: ...
async def list_services(session: AsyncSession, active_only: bool = True) -> list[DentalService]: ...
async def create_service(session: AsyncSession, *, name: str, description: str | None, duration_minutes: int) -> DentalService: ...
async def update_service(session: AsyncSession, service: DentalService, **kwargs) -> DentalService: ...
```

---

## 4. Layer 3 — Wiring (Standard §5)

### Dependencies
- `get_service_catalog(session: DbSessionDep) -> ServiceCatalog`
- `ServiceCatalogDep = Annotated[ServiceCatalog, Depends(get_service_catalog)]`

### Endpoints
| Method | Path | Request | Response | Success | Errors | Guard | Covers |
|---|---|---|---|---|---|---|---|
| `POST` | `/api/v1/services` | `ServiceCreate` | `ServiceRead` | 201 | 401, 403, 409, 422 | `require_roles("ADMIN")` | R-6 |
| `GET` | `/api/v1/services` | Query: `active_only: bool = True` | `list[ServiceRead]` | 200 | 401 | `CurrentUserDep` | R-6 |
| `GET` | `/api/v1/services/{service_id}` | Path: `service_id: UUID` | `ServiceRead` | 200 | 401, 404 | `CurrentUserDep` | R-6 |
| `PATCH` | `/api/v1/services/{service_id}` | `ServiceUpdate` | `ServiceRead` | 200 | 401, 403, 404, 409, 422 | `require_roles("ADMIN")` | R-6 |

### Authorization Matrix
| Action | Role / Permission | Row-Level Rule |
|---|---|---|
| List / View Services | Authenticated staff (`ADMIN`, `RECEPTIONIST`, `DENTIST`) | Anyone can view catalog for booking/consultation |
| Create / Edit / Deactivate Service | `ADMIN` only | Only Admins manage clinic service definitions |

---

## 5. Layer 4 — Concurrency and Real-Time (Standard §6)
- N/A — Standard transactional database persistence.

---

## 6. Layer 5 — State and Hardening (Standard §7)
- **Shared State:** No module-level mutable state.
- **Deactivation Policy:** Deactivating a service (`is_active = false`) prevents new bookings from selecting it, while preserving referential integrity for all past appointments.

---

## 7. Errors
| Exception | Raised when | HTTP Status | Error Code |
|---|---|---|---|
| `ServiceNotFoundError` | Service ID does not exist | 404 | `SERVICE_NOT_FOUND` |
| `ServiceNameExistsError` | Service name is already taken | 409 | `SERVICE_NAME_EXISTS` |
| `ServiceInactiveError` | Booking attempted with inactive service | 400 | `SERVICE_INACTIVE` |

---

## 8. State Machine
N/A — Active toggle (`is_active`).

---

## 9. Test Seams
| Behaviour | Seam | Notes |
|---|---|---|
| Duration <= 0 rejected | Schema unit test | 422 raised by Pydantic validator |
| Unique service name | Repository test against real DB | 409 raised on duplicate name insert |
| Deactivated service hidden from booking | Integration test | Query with `active_only=True` excludes deactivated items |
| Receptionist denied creation | API test with `dependency_overrides` | Asserts 403 Forbidden |

---

## 10. Traceability
| Requirement | Spec Section | Endpoint(s) |
|---|---|---|
| **R-6** Dental Service Management | §2 Contracts, §3 Persistence, §4 Endpoints | `POST /api/v1/services`, `GET /api/v1/services`, `PATCH /api/v1/services/{id}` |

---

## 11. Open Questions / ADRs
None.
