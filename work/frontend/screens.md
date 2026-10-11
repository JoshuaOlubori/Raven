# Frontend screen manifest — Raven Dental Clinic Operations Portal

Edit this file when the screen set, roles, API contract, or design decisions change. The `frontend-screens` skill exports and audits these rows; `frontend-tickets` generates work only from audited screen rows and approved specifications.

## Project

- Product: Raven Dental Clinic Operations Portal
- Stitch project ID: `3296426393629084197`
- Stitch project URL: not supplied
- Manifest owner: project owner

## Screen retrieval request

Use the configured Google Stitch integration to retrieve each screen's screenshot and code. The IDs below identify Stitch items; they are not hosted download URLs. Download returned hosted URLs with `curl -L` and save them under the output paths below.

## Output

- Asset root: `docs/ui/stitch/raven-dental-clinic-operations-portal/`
- Screens: `<slug>/screen.png`, `<slug>/code.html`, `<slug>/AUDIT.md`
- References: `<slug>/reference.png` plus a short design note

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

| Slug | Name | Stitch ID | Kind | Proposed route | Roles | API operations to audit | Asset status | Audit status | Mock ticket | Backend ticket |
|---|---|---|---|---|---|---|---|---|---|---|
| provider-schedules-time-off | Provider schedules and time off — Admin | `119396e3b04640fda1a0104f853c68c6` | screen |  | ADMIN |  | pending | pending |  |  |
| today-operations | Today operations dashboard — Admin and Receptionist | `2c1d393181c545c685a2afa93befa001` | screen |  | ADMIN, RECEPTIONIST |  | pending | pending |  |  |
| dental-services | Dental services catalog | `6b6c25cff47b4af4ad8e5f750ccd539f` | screen |  |  |  | pending | pending |  |  |
| patient-form | Create/edit patient form | `6f8dfd62db344651902d76f3d1cf680a` | screen |  |  |  | pending | pending |  |  |
| ref1 | ref1.webp | `15779978166096710616` | reference |  |  |  | pending | n/a |  |  |
| patient-profile-history | Patient profile and visit history | `b6efb93467cf494f83c69e9e7db8a4a1` | screen |  |  |  | pending | pending |  |  |
| dentist-workspace | Dentist workspace — own day and time off | `c174ff8944d04908b0e5c4836f48b1af` | screen |  | DENTIST |  | pending | pending |  |  |
| patient-directory | Patient directory | `e601baf565604badb0d007cd5c5aedba` | screen |  |  |  | pending | pending |  |  |
| ref2 | ref2.webp | `15779978166096709962` | reference |  |  |  | pending | n/a |  |  |
| staff-sign-in | Staff sign-in | `f109bfeaefc4408f9a3375f68f47ad85` | screen |  | public | `POST /api/v1/auth/token`; `GET /api/v1/auth/me` | pending | pending |  |  |
| appointment-detail-audit | Appointment detail and audit history | `f43223deabf040fd8fff0dcb57d60c3c` | screen |  |  |  | pending | pending |  |  |
| appointments-calendar | Appointments calendar | `f8225aa93d3045d9aee57380ead69f28` | screen |  |  |  | pending | pending |  |  |
| staff-management | Staff management | `fa440797e9f34e999f5d60e783b68faa` | screen |  |  |  | pending | pending |  |  |

Routes, role visibility, and all endpoint mappings except the authentication endpoints above remain pending the screen and OpenAPI audit. Do not infer them from screen titles.

## Open scope gaps

| Item | Source | Gap | Decision | Disposition |
|---|---|---|---|---|
| New appointment booking flow | Backend requirement `R-10` and appointment API | No booking screen appears in the supplied Stitch list | Project owner | Keep out of the Stitch screen backlog until a screen is supplied or an explicitly unstyled requirement ticket is approved |

The appointment API supports booking, but the current Stitch inventory does not define its screen. Ticket generation must not invent a Stitch design for it.

## Sign-off

- Screen set reviewed by:
- Mock UI phase approved by:
- Date:
- Notes:
