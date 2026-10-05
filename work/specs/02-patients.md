# Patient Management Module Spec

_Status: approved · Date: 2026-10-03 · Covers: R-3, R-4, R-5, NFR-6_

## 1. Responsibility
This module owns patient profile creation, update, demographic queries, case-insensitive search by name or phone, and soft deletion (`is_active = false`).
It explicitly does NOT own appointment scheduling or clinical treatment notes.

---

## 2. Layer 1 — Contracts (Standard §3)

### Shared Constrained Types
```python
PhoneStr = Annotated[str, BeforeValidator(_strip), Field(min_length=7, max_length=20, pattern=r"^\+?[0-9\s\-()]+$")]
NonEmptyStr = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=100)]
```

### Schemas Table
| Schema | Purpose | Fields (name: type, optional?) | Validators / computed fields |
|---|---|---|---|
| `PatientCreate` | Patient registration input | `first_name: NonEmptyStr`, `last_name: NonEmptyStr`, `date_of_birth: date`, `phone: PhoneStr`, `email: EmailStr | None = None`, `emergency_contact_name: str | None = None`, `emergency_contact_phone: PhoneStr | None = None`, `medical_alerts: str | None = None` | DOB cannot be in the future; phone validated |
| `PatientUpdate` | Patient profile updates | All fields optional: `first_name`, `last_name`, `date_of_birth`, `phone`, `email`, `emergency_contact_name`, `emergency_contact_phone`, `medical_alerts` | If DOB provided, cannot be in future |
| `PatientRead` | Public patient representation | `id: UUID`, `first_name: NonEmptyStr`, `last_name: NonEmptyStr`, `date_of_birth: date`, `phone: PhoneStr`, `email: EmailStr | None`, `emergency_contact_name: str | None`, `emergency_contact_phone: PhoneStr | None`, `medical_alerts: str | None`, `is_active: bool`, `created_at: datetime`, `updated_at: datetime` | Computed `@computed_field` `full_name: str = f"{first_name} {last_name}"` |
| `PatientPage` | Paginated search output | `items: list[PatientRead]`, `total: int`, `page: int`, `size: int`, `pages: int` | Standard paginated collection |

---

## 3. Layer 2 — Persistence (Standard §4)

### ORM Model: `Patient` (`app/models/patient.py`)
| Model | Columns | Relationships | Indexes / Constraints |
|---|---|---|---|
| `Patient` | `id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)`<br>`first_name: Mapped[str]`<br>`last_name: Mapped[str]`<br>`date_of_birth: Mapped[date]`<br>`phone: Mapped[str] = mapped_column(index=True)`<br>`email: Mapped[str | None]`<br>`emergency_contact_name: Mapped[str | None]`<br>`emergency_contact_phone: Mapped[str | None]`<br>`medical_alerts: Mapped[str | None]`<br>`is_active: Mapped[bool] = mapped_column(default=True, index=True)`<br>`created_at: Mapped[datetime] = mapped_column(default=utcnow)`<br>`updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)` | `appointments: Mapped[list["Appointment"]] = relationship(back_populates="patient")` | Composite index on `(last_name, first_name)`. Index on `phone`. Index on `is_active`. |

### Repository Signatures (`app/db/repository.py`)
```python
async def get_patient_by_id(session: AsyncSession, patient_id: UUID) -> Patient | None: ...
async def list_patients(
    session: AsyncSession,
    search: str | None = None,
    include_inactive: bool = False,
    page: int = 1,
    size: int = 50,
) -> tuple[list[Patient], int]: ...
async def create_patient(session: AsyncSession, **kwargs) -> Patient: ...
async def update_patient(session: AsyncSession, patient: Patient, **kwargs) -> Patient: ...
async def soft_delete_patient(session: AsyncSession, patient: Patient) -> Patient: ...
```

---

## 4. Layer 3 — Wiring (Standard §5)

### Dependencies
- `get_patient_service(session: DbSessionDep) -> PatientService`
- `PatientServiceDep = Annotated[PatientService, Depends(get_patient_service)]`

### Endpoints
| Method | Path | Request | Response | Success | Errors | Guard | Covers |
|---|---|---|---|---|---|---|---|
| `POST` | `/api/v1/patients` | `PatientCreate` | `PatientRead` | 201 | 401, 403, 422 | `require_roles("ADMIN", "RECEPTIONIST")` | R-3 |
| `GET` | `/api/v1/patients` | Query: `search: str | None`, `page: int = 1`, `size: int = 50` | `PatientPage` | 200 | 401, 403 | `Depends(get_current_user)`¹ | R-4 |
| `GET` | `/api/v1/patients/{patient_id}` | Path: `patient_id: UUID` | `PatientRead` | 200 | 401, 403, 404 | `Depends(get_current_user)`¹ | R-4 |
| `PATCH` | `/api/v1/patients/{patient_id}` | `PatientUpdate` | `PatientRead` | 200 | 401, 403, 404, 422 | `require_roles("ADMIN", "RECEPTIONIST")` | R-3 |
| `DELETE` | `/api/v1/patients/{patient_id}` | Path: `patient_id: UUID` | `None` (204) | 204 | 401, 403, 404 | `require_roles("ADMIN", "RECEPTIONIST")` | R-5 |

¹ `Depends(get_current_user)` is the accepted guard for all-staff read endpoints. It is behaviourally equivalent to `require_roles("ADMIN", "RECEPTIONIST", "DENTIST")` because `StaffRole = Literal["ADMIN", "RECEPTIONIST", "DENTIST"]` — any authenticated, active staff member is one of these roles, so the role-check can never raise 403. This pattern is established by T-004 (services router) and applied consistently across read-only GET endpoints.

### Authorization Matrix
| Action | Role / Permission | Row-Level Rule |
|---|---|---|
| View / Search Patients | `ADMIN`, `RECEPTIONIST`, `DENTIST` | Any authenticated clinical staff |
| Create / Edit Patient | `ADMIN`, `RECEPTIONIST` | Receptionists manage demographics; Dentists view medical alerts |
| Soft Delete Patient | `ADMIN`, `RECEPTIONIST` | Patient `is_active` set to `False`; historical records preserved |

---

## 5. Layer 4 — Concurrency and Real-Time (Standard §6)
- Pure async CRUD database queries.
- Concurrency: N/A — Standard row-level persistence.
- Real-time SSE: N/A.

---

## 6. Layer 5 — State and Hardening (Standard §7)
- **Shared State:** No module-level mutable state.
- **Data Protection:** Medical alerts and emergency contacts are filtered behind staff authentication (NFR-6). Soft-deleted patients are excluded from search queries by default (`WHERE is_active = true`).

---

## 7. Errors
| Exception | Raised when | HTTP Status | Error Code |
|---|---|---|---|
| `PatientNotFoundError` | Patient ID does not exist | 404 | `PATIENT_NOT_FOUND` |
| `PatientInactiveError` | Attempting to book an appointment for an inactive patient | 400 | `PATIENT_INACTIVE` |

---

## 8. State Machine
N/A — Patients have an active flag (`is_active`).

---

## 9. Test Seams
| Behaviour | Seam | Notes |
|---|---|---|
| DOB in future rejected | Schema unit test | 422 raised by Pydantic validator |
| Case-insensitive partial name & phone search | Repository test against real DB | Validates SQL ILIKE / prefix query |
| Soft delete hides patient from default search | Integration test | Verifies `is_active=False` and excluded from `list_patients` |
| Patient with past appointments retains integrity | Integration test | Foreign keys in appointments table remain valid |

---

## 10. Traceability
| Requirement | Spec Section | Endpoint(s) |
|---|---|---|
| **R-3** Patient Profile Management | §2 Contracts, §3 Persistence, §4 Endpoints | `POST /api/v1/patients`, `PATCH /api/v1/patients/{id}` |
| **R-4** Patient Search & Retrieval | §2 Contracts, §3 Repository, §4 Endpoints | `GET /api/v1/patients`, `GET /api/v1/patients/{id}` |
| **R-5** Patient Soft Deletion | §3 Persistence, §4 Endpoints | `DELETE /api/v1/patients/{id}` |
| **NFR-6** Security & PII Protection | §4 Authorization Matrix, §6 Data Protection | All patient endpoints restricted to staff |

---

## 11. Open Questions / ADRs
None.
