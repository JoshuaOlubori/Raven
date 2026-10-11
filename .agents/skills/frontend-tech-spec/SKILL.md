---
name: frontend-tech-spec
description: Create the frontend technical specification (work/specs/frontend/00-frontend-architecture.md and domain specs) based on the backend API specs, Stitch designs, and PRD. Use after frontend-setup completes, or when the user says "write the frontend spec", "create the frontend architecture", "plan the frontend". Produces no production code.
---

# Frontend Technical Specification

Convert the approved backend specs, PRD, and Stitch designs into a coherent frontend technical specification that guides implementation.

## Inputs
- `work/prd.md` — Product requirements
- `work/specs/*.md` — Backend domain specifications (auth, patients, services, schedules, appointments, notifications)
- `docs/ui/stitch-prompts.md` — Stitch screen designs and interaction flows
- `CLAUDE.md` — Project standards and quality gates

## Output
`work/specs/frontend/` directory with:
- `00-frontend-architecture.md` — Overall architecture, stack, patterns, routing, state management
- `01-auth-ui.md` — Sign-in, token management, route guards
- `02-patients-ui.md` — Patient directory, profile, form
- `03-services-ui.md` — Services catalog
- `04-schedules-ui.md` — Provider shifts, time-off, availability
- `05-appointments-ui.md` — Today dashboard, Calendar, Booking flow, Detail, Audit
- `06-staff-ui.md` — Staff management
- `07-shared-components.md` — Design system, reusable components, constants
- `08-api-integration.md` — API client, error handling, SSE, types

## Specification Template (per domain)

Each domain spec follows the backend spec structure adapted for frontend:

```markdown
# <Domain> UI Module Spec

_Status: draft · Date: YYYY-MM-DD · Covers: <PRD requirements>_

## 1. Responsibility
What this UI module owns (screens, components, interactions). What it explicitly does NOT own.

## 2. Screens & Routes
| Screen | Route | Roles | Description |
|---|---|---|---|
| Sign In | /signin | Public | Staff authentication |
| Today Dashboard | /today | Admin, Receptionist | Operational overview |
| Appointments Calendar | /appointments | All | Week/day view with filters |
| ... | ... | ... | ... |

## 3. Component Hierarchy
Tree of components for this domain, showing composition and data flow.

## 4. State Management
- **Server State** (TanStack Query): Queries, mutations, cache keys, invalidation strategy
- **Client State** (Zustand): Auth, UI preferences, form drafts, optimistic updates
- **URL State** (TanStack Router): Search params, filters, pagination

## 5. API Contract
Mapping of UI actions to backend endpoints:
| UI Action | Endpoint | Method | Request Type | Response Type | Error Handling |
|---|---|---|---|---|---|

## 6. Types
TypeScript interfaces matching backend schemas (generated or manual):
- Request/Response types
- UI-specific extensions (e.g., `AppointmentWithRelations`)

## 7. Permissions & Role Guards
Component-level and route-level permission checks based on `CurrentUser.role`.

## 8. Responsive Breakpoints
| Breakpoint | Layout Changes |
|---|---|
| Desktop (≥1024px) | Full sidebar, multi-column tables |
| Tablet (768-1023px) | Collapsible sidebar, stacked cards |
| Mobile (<768px) | Drawer navigation, list views |

## 9. Accessibility
- Keyboard navigation, focus management
- ARIA labels, roles, live regions
- Color contrast (WCAG AA)
- Screen reader announcements for status changes

## 10. Loading / Error / Empty States
Standardized patterns per component type.

## 11. Test Strategy
- Component tests (React Testing Library)
- Integration tests (MSW for API mocking)
- E2E tests (Playwright) for critical flows

## 12. Traceability
| PRD Requirement | Spec Section | Screen/Component |
```

## Process

1. **Read all inputs** — Understand backend API contracts, PRD requirements, Stitch designs
2. **Draft 00-frontend-architecture.md** — Establish patterns, routing strategy, state architecture
3. **Draft domain specs** — One per backend domain, map screens to API endpoints
4. **Review with user** — Present spec table of contents, ask for approval on granularity and approach
5. **Finalize** — Mark specs as `approved`, update `updated` date

## Key Design Decisions to Document

- **Routing**: File-based with TanStack Router, route trees per role
- **Data Fetching**: TanStack Query with 5-minute stale time, background refetch on window focus
- **Mutations**: Optimistic updates for immediate UI feedback, rollback on error
- **SSE**: EventSource wrapper with reconnection, feed into TanStack Query cache invalidation
- **Forms**: React Hook Form + Zod resolvers, shared validation schemas with backend where possible
- **Design System**: shadcn/ui + Tailwind CSS variables, semantic color tokens for appointment states
- **Role-based Rendering**: Route guards + component-level `can()` helpers
- **Date/Time**: All timestamps in clinic local time (America/New_York), display via `date-fns-tz`

## Hand-off

Tell the user: frontend tech spec complete → **clear context** → run `frontend-tickets` to break down into implementation tickets.