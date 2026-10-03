# Auth & Staff Module Spec

_Status: approved · Date: 2026-10-03 · Covers: R-1, R-2, NFR-6_

## 1. Responsibility
This module owns internal staff account creation, credential verification, password hashing, JWT token issuance, session authentication, and role-based access control (RBAC) guards.
It explicitly does NOT own patient authentication (patients have no login in v1) or clinical appointments.

---

## 2. Layer 1 — Contracts (Standard §3)

### Shared Constrained Types
```python
StaffRole = Literal["ADMIN", "RECEPTIONIST", "DENTIST"]
EmailStr = Annotated[str, BeforeValidator(_normalize_email), Field(min_length=3, max_length=255)]
PasswordStr = Annotated[str, Field(min_length=8, max_length=128)]
NonEmptyStr = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=100)]
```

### Schemas Table
| Schema | Purpose | Fields (name: type, optional?) | Validators / computed fields |
|---|---|---|---|
| `TokenRequest` | Login input (OAuth2 / JSON) | `username: EmailStr`, `password: PasswordStr` | Validates format, strips email |
| `TokenResponse` | Access token output | `access_token: str`, `token_type: str = "bearer"`, `expires_in: int`, `role: StaffRole` | CamelCase aliases |
| `StaffCreate` | Staff registration (Admin only) | `email: EmailStr`, `password: PasswordStr`, `full_name: NonEmptyStr`, `role: StaffRole` | Role must be valid; password length >= 8 |
| `StaffUpdate` | Account update | `full_name: NonEmptyStr | None = None`, `role: StaffRole | None = None`, `is_active: bool | None = None` | None |
| `StaffRead` | Public staff representation | `id: UUID`, `email: EmailStr`, `full_name: NonEmptyStr`, `role: StaffRole`, `is_active: bool`, `created_at: datetime` | CamelCase aliases (`fullName`, `isActive`) |

---

## 3. Layer 2 — Persistence (Standard §4)

### ORM Model: `Staff` (`app/models/staff.py`)
| Model | Columns | Relationships | Indexes / Constraints |
|---|---|---|---|
| `Staff` | `id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)`<br>`email: Mapped[str] = mapped_column(unique=True, index=True)`<br>`hashed_password: Mapped[str]`<br>`full_name: Mapped[str]`<br>`role: Mapped[str] = mapped_column(index=True)`<br>`is_active: Mapped[bool] = mapped_column(default=True)`<br>`created_at: Mapped[datetime] = mapped_column(default=utcnow)` | `working_shifts: Mapped[list["WorkingShift"]] = relationship(back_populates="dentist")`<br>`time_off_blocks: Mapped[list["TimeOffBlock"]] = relationship(back_populates="dentist")`<br>`appointments: Mapped[list["Appointment"]] = relationship(back_populates="dentist")` | Unique index on `email`. Index on `role`. |

### Repository Signatures (`app/db/repository.py`)
```python
async def get_staff_by_id(session: AsyncSession, staff_id: UUID) -> Staff | None: ...
async def get_staff_by_email(session: AsyncSession, email: str) -> Staff | None: ...
async def list_staff(session: AsyncSession, role: str | None = None, active_only: bool = True) -> list[Staff]: ...
async def create_staff(session: AsyncSession, *, email: str, hashed_password: str, full_name: str, role: str) -> Staff: ...
async def update_staff(session: AsyncSession, staff: Staff, **kwargs) -> Staff: ...
```

---

## 4. Layer 3 — Wiring (Standard §5)

### Dependencies (`app/api/deps.py` & `app/api/auth.py`)
- `get_current_user`: Decodes Bearer JWT token, validates expiration, queries `get_staff_by_id`, ensures `is_active=True`, returns `CurrentUser(id, email, role)`.
- `CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]`
- `require_roles(*roles: str)`: Closure dependency factory raising `403 Forbidden` if `current_user.role not in roles`.
- `get_auth_service(session: DbSessionDep, settings: SettingsDep) -> AuthService`
- `AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]`

### Endpoints
| Method | Path | Request | Response | Success | Errors | Guard | Covers |
|---|---|---|---|---|---|---|---|
| `POST` | `/api/v1/auth/token` | `TokenRequest` | `TokenResponse` | 200 | 401, 422 | None (Public) | R-1 |
| `GET` | `/api/v1/auth/me` | None | `StaffRead` | 200 | 401 | `CurrentUserDep` | R-1 |
| `POST` | `/api/v1/staff` | `StaffCreate` | `StaffRead` | 201 | 401, 403, 409, 422 | `require_roles("ADMIN")` | R-2 |
| `GET` | `/api/v1/staff` | Query: `role: StaffRole | None` | `list[StaffRead]` | 200 | 401, 403 | `require_roles("ADMIN", "RECEPTIONIST")` | R-2 |
| `GET` | `/api/v1/staff/{staff_id}` | Path: `staff_id: UUID` | `StaffRead` | 200 | 401, 403, 404 | `require_roles("ADMIN", "RECEPTIONIST")` | R-2 |
| `PATCH` | `/api/v1/staff/{staff_id}` | `StaffUpdate` | `StaffRead` | 200 | 401, 403, 404, 422 | `require_roles("ADMIN")` | R-2 |

### Authorization Matrix
| Action | Role / Permission | Row-Level (ABAC) Rule |
|---|---|---|
| Login / Refresh | Any active staff | Account must have `is_active=True` |
| View Profile (`/me`) | Authenticated staff | Only access own profile |
| Create / Edit Staff | `ADMIN` only | None |
| List Dentists / Staff | `ADMIN`, `RECEPTIONIST` | Receptionists need to see active dentists for booking |

---

## 5. Layer 4 — Concurrency and Real-Time (Standard §6)
- **Password Hashing:** Argon2 hashing is CPU-bound. In `AuthService.hash_password` and `AuthService.verify_password`, offload calculation to worker thread pool using `loop.run_in_executor(None, argon2_hasher.verify, ...)` so ASGI event loop is never blocked.
- Real-time SSE: N/A for staff login.

---

## 6. Layer 5 — State and Hardening (Standard §7)
- **Shared State:** No module-level mutable state. Token verification is completely stateless via asymmetric/symmetric JWT signatures.
- **Brute Force Protection:** Invalid login attempts return generic `401 Unauthorized` ("Invalid email or password").

---

## 7. Errors
| Exception | Raised when | HTTP Status | Error Code |
|---|---|---|---|
| `InvalidCredentialsError` | Email not found or password mismatch | 401 | `AUTH_INVALID_CREDENTIALS` |
| `InactiveAccountError` | Staff member is marked `is_active=False` | 401 | `AUTH_INACTIVE_ACCOUNT` |
| `EmailAlreadyExistsError` | Admin creates staff with existing email | 409 | `STAFF_EMAIL_EXISTS` |
| `StaffNotFoundError` | Staff ID does not exist | 404 | `STAFF_NOT_FOUND` |

---

## 8. State Machine
N/A — Staff account lifecycle is limited to active/inactive toggle via `is_active`.

---

## 9. Test Seams
| Behaviour | Seam | Notes |
|---|---|---|
| Token issuance & password hashing | Service unit test with mock session | Validates Argon2 + JWT expiry claim |
| Email uniqueness constraint | Repository test against real DB | 409 raised on duplicate insert |
| Non-admin denied staff creation | API test with `dependency_overrides` for `get_current_user` | Asserts 403 Forbidden |
| Admin successfully creates staff | API test with Admin user | Asserts 201 Created and password not in response |

---

## 10. Traceability
| Requirement | Spec Section | Endpoint(s) |
|---|---|---|
| **R-1** Staff Authentication | §2 Contracts, §3 Persistence, §4 Wiring | `POST /api/v1/auth/token`, `GET /api/v1/auth/me` |
| **R-2** Role-Based Access Control | §4 Authorization Matrix, §4 Wiring | `POST /api/v1/staff`, `GET /api/v1/staff`, `PATCH /api/v1/staff/{id}` |
| **NFR-6** Security & Password Hashing | §2 Passwords, §5 Concurrency | All auth operations using Argon2 |

---

## 11. Open Questions / ADRs
None.
