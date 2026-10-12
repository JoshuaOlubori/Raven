# Frontend screen manifest — Raven Dental Clinic Operations Portal

Edit this file when the screen set, roles, API contract, or design decisions change. The `frontend-screens` skill exports and audits these rows; `frontend-tickets` generates work only from audited screen rows and approved specifications.

## Project

- Product: Raven Dental Clinic Operations Portal
- Stitch project ID: `3296426393629084197`
- Stitch project URL: not supplied
- Manifest owner: project owner

## Local screen exports

- Export root: `stitch_screens/`
- Source artifacts: each screen folder contains `screen.png` and `code.html`; inspect them in place and preserve the original exports.
- Shared design guidance: `stitch_screens/raven_clinical_dental/DESIGN.md`
- Stitch MCP: unavailable during export. Use it only to fill an explicitly recorded local asset gap if it becomes available.
- IDs identify source items, not hosted download URLs.

## Output

- Local export root: `stitch_screens/`
- Screens: `<Local export folder>/screen.png`, `<Local export folder>/code.html`, and `<Local export folder>/AUDIT.md`
- References: record their actual local image path plus a short design note; shared `DESIGN.md` is supplementary guidance, not a substitute image

## Contract and product sources

- OpenAPI: `http://localhost:8000/openapi.json` when the backend is running
- Backend specifications: `work/specs/*.md`
- Product requirements: `work/prd.md`
- Frontend specifications: `work/frontend/specs/`
- API type generation source: OpenAPI document; use the approved backend specs only as a labeled fallback

### Contract facts to verify in the current OpenAPI document

These are based on the checked-in backend source and specifications. Confirm paths and payloads against the generated OpenAPI document before creating API tickets.

- Staff list filters by role and returns active staff only; there is no list query for inactive staff. `StaffRead` includes `is_active`.
- Patient search is paginated and excludes inactive patients by default; the list endpoint has no `include_inactive` query. The detail endpoint returns a patient by ID and `PatientRead` includes `is_active`.
- Appointment list supports filters but has no pagination parameters. A dentist ID filter is available; the appointment list does not enforce that a dentist can query only their own ID.
- Schedule and appointment list filters do not restrict a dentist to their own ID. The backend validates a dentist's identity when they create or delete their own time-off block; the UI filter is not an authorization boundary.
- The current API route declarations use trailing slashes for patients, services, and staff collection routes, while appointment collection routes have no trailing slash. Follow the actual OpenAPI paths, not documentation examples.
- The live appointment stream is authenticated and sends bearer-token protected SSE. The browser integration needs fetch-based SSE if it is used.
- The backend health check is `/health`. The backend currently has no CORS middleware; use the same-origin Vite proxy during development.

## Global design notes

- Target roles: `ADMIN`, `RECEPTIONIST`, `DENTIST`; public sign-in
- Responsive requirements: verify 375, 768, 1024, and 1440 CSS-pixel widths
- Product constraint: only render fields, actions, permissions, and server behavior supported by the API contract

## Screens and references

| Slug | Name | Stitch ID | Kind | Local export folder | Proposed route | Roles | API operations to audit | Asset status | Audit status | Mock ticket | Backend ticket |
|---|---|---|---|---|---|---|---|---|---|---|---|
| staff-sign-in | Staff sign-in | `f109bfeaefc4408f9a3375f68f47ad85` | screen | `raven_dental_staff_sign_in` | `/sign-in` | public | `POST /api/v1/auth/token`; `GET /api/v1/auth/me` | available | complete |  |  |
| today-operations | Today operations dashboard — Admin and Receptionist | `2c1d393181c545c685a2afa93befa001` | screen | `today_front_desk_operations_dashboard` | `/today` | ADMIN, RECEPTIONIST | `GET /api/v1/auth/me`; `GET /api/v1/appointments` (date, status, dentist_id filters); `POST /api/v1/appointments/{id}/status`; `GET /api/v1/staff?role=DENTIST`; `GET /api/v1/schedules/shifts`; `GET /api/v1/schedules/time-off`; `GET /api/v1/schedules/availability`; `GET /api/v1/appointments/live` (SSE); `GET /api/v1/patients?search` | available | complete |  |  |
| patient-directory | Patient directory | `e601baf565604badb0d007cd5c5aedba` | screen | `patients_patient_directory_chart_records` | `/patients` | ADMIN, RECEPTIONIST, DENTIST (read-only) | `GET /api/v1/auth/me`; `GET /api/v1/patients` (search, pagination); `POST /api/v1/patients`; `PATCH /api/v1/patients/{id}`; `DELETE /api/v1/patients/{id}`; `GET /api/v1/patients/{id}` | available | complete |  |  |
| patient-form | Create/edit patient form | `6f8dfd62db344651902d76f3d1cf680a` | screen | `patients_patient_intake_demographics_form` | `/patients/new` (create), `/patients/{id}/edit` (edit) | ADMIN, RECEPTIONIST | `GET /api/v1/auth/me`; `GET /api/v1/patients/{id}`; `POST /api/v1/patients`; `PATCH /api/v1/patients/{id}` | available | complete |  |  |
| patient-profile-history | Patient profile and visit history | `b6efb93467cf494f83c69e9e7db8a4a1` | screen | `patients_patient_profile_clinical_history` | `/patients/{id}` | ADMIN, RECEPTIONIST, DENTIST (read-only) | `GET /api/v1/auth/me`; `GET /api/v1/patients/{id}`; `PATCH /api/v1/patients/{id}` (restore); `GET /api/v1/appointments?patient_id`; `POST /api/v1/appointments/{id}/reschedule`; `POST /api/v1/appointments/{id}/cancel`; `GET /api/v1/appointments/{id}/audit-logs` | available | complete |  |  |
| dentist-workspace | Dentist workspace — own day and time off | `c174ff8944d04908b0e5c4836f48b1af` | screen | `my_schedule_clinical_dentist_workspace` | `/my-schedule` | DENTIST | `GET /api/v1/auth/me`; `GET /api/v1/appointments?dentist_id=me&date`; `POST /api/v1/appointments/{id}/status`; `POST /api/v1/schedules/time-off`; `GET /api/v1/schedules/time-off?dentist_id=me`; `DELETE /api/v1/schedules/time-off/{id}`; `GET /api/v1/appointments/live` (SSE); `GET /api/v1/patients/{id}` | available | complete |  |  |
| appointments-calendar | Appointments calendar | `f8225aa93d3045d9aee57380ead69f28` | screen | `appointments_staff_calendar_provider_lanes` | `/appointments` | ADMIN, RECEPTIONIST, DENTIST (own lane) | `GET /api/v1/auth/me`; `GET /api/v1/staff?role=DENTIST`; `GET /api/v1/appointments` (date range, dentist_id, status); `GET /api/v1/schedules/shifts`; `GET /api/v1/schedules/time-off`; `GET /api/v1/schedules/availability`; `GET /api/v1/appointments/{id}`; `GET /api/v1/patients/{id}`; `GET /api/v1/appointments/live` (SSE) | available | complete |  |  |
| appointment-detail-audit | Appointment detail and audit history | `f43223deabf040fd8fff0dcb57d60c3c` | screen | `appointments_appointment_detail_audit_history` | `/appointments/{id}` | ADMIN, RECEPTIONIST, DENTIST | `GET /api/v1/auth/me`; `GET /api/v1/appointments/{id}`; `GET /api/v1/appointments/{id}/audit-logs`; `POST /api/v1/appointments/{id}/reschedule`; `POST /api/v1/appointments/{id}/cancel`; `POST /api/v1/appointments/{id}/status` | available | complete |  |  |
| dental-services | Dental services catalog | `6b6c25cff47b4af4ad8e5f750ccd539f` | screen | `services_clinical_services_catalog` | `/services` | ADMIN (CRUD), RECEPTIONIST (read), DENTIST (read) | `GET /api/v1/auth/me`; `GET /api/v1/services` (active_only); `POST /api/v1/services`; `PATCH /api/v1/services/{id}`; `GET /api/v1/services/{id}` | available | complete |  |  |
| provider-schedules-time-off | Provider schedules and time off — Admin | `119396e3b04640fda1a0104f853c68c6` | screen | `provider_schedules_recurring_shifts_provider_availability` | `/provider-schedules` | ADMIN (CRUD), RECEPTIONIST (read), DENTIST (own time-off) | `GET /api/v1/auth/me`; `GET /api/v1/staff?role=DENTIST`; `GET /api/v1/schedules/shifts`; `POST /api/v1/schedules/shifts`; `DELETE /api/v1/schedules/shifts/{id}`; `GET /api/v1/schedules/time-off`; `POST /api/v1/schedules/time-off`; `DELETE /api/v1/schedules/time-off/{id}`; `GET /api/v1/schedules/availability`; `GET /api/v1/services` | available | complete |  |  |
| staff-management | Staff management | `fa440797e9f34e999f5d60e783b68faa` | screen | `staff_practice_staff_directory_account_management` | `/staff` | ADMIN only | `GET /api/v1/auth/me`; `GET /api/v1/staff`; `POST /api/v1/staff`; `PATCH /api/v1/staff/{id}`; `GET /api/v1/staff/{id}` | available | complete |  |  |
| ref1 | ref1.webp | `15779978166096710616` | reference |  |  |  |  | missing | n/a |  |  |
| ref2 | ref2.webp | `15779978166096709962` | reference |  |  |  |  | missing | n/a |  |  |

All screens audited against approved backend specifications (work/specs/*.md dated 2026-10-03) and OpenAPI contract facts. Routes, roles, and API operations are now populated. Dev-only preview components (role simulators, state previews) marked for removal in implementation.

## Open scope gaps

| Item | Source | Gap | Decision | Disposition |
|---|---|---|---|---|
| New appointment booking flow | Backend requirement `R-10` and appointment API | No booking screen appears in the supplied Stitch list | Project owner | Keep out of the Stitch screen backlog until a screen is supplied or an explicitly unstyled requirement ticket is approved |
| ref1.webp and ref2.webp | Original Stitch retrieval request | No local reference images were found under `stitch_screens/`; shared `DESIGN.md` is available | Project owner | Keep as missing design references; do not create image assets or routes by inference |

The appointment API supports booking, but the current Stitch inventory does not define its screen. Ticket generation must not invent a Stitch design for it.

## Sign-off

- Screen set reviewed by:
- Mock UI phase approved by:
- Date:
- Notes: