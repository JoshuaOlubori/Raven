---
name: frontend-tech-spec
description: Write the frontend architecture and domain specifications from the approved screen manifest, design audits, product requirements, and backend contract. Use after screen intake and before generating frontend tickets; produces no production code.
---

# Frontend Technical Specification

Write the approved design and API decisions in `work/frontend/specs/`. Keep the screen manifest and its per-screen audits as the project-specific design source; do not copy project names, routes, roles, or endpoint assumptions into this reusable skill.

## Inputs

- `work/frontend/screens.md`, each screen's local export folder, and its `AUDIT.md`
- `work/prd.md` when present
- `work/specs/*.md` or the current OpenAPI schema
- repository instructions and existing frontend code

## Output

- `work/frontend/specs/00-frontend-architecture.md`
- one domain spec per audited screen group
- `work/frontend/specs/08-api-integration.md` when API integration warrants a separate spec

Use filenames and domain groupings that match the current project instead of assuming a fixed set of screens. Every screen row must map to a route, a spec section, and its supporting API operations or an explicit `n/a` disposition.

## Required sections

1. Responsibility and explicit exclusions
2. Screen/route matrix, roles, and navigation
3. Component composition and module boundaries
4. State ownership: TanStack Query for server state, Zustand for shared client state, URL state for shareable filters
5. API operation and schema mapping, auth and error behavior
6. Mock-to-live boundary: MSW handlers and fixtures first, one stable API client/hooks interface, live transport after user approval
7. Responsive behavior for phone, tablet, small desktop, and wide desktop
8. Accessibility and keyboard behavior
9. Loading, empty, error, permission, and conflict states
10. Test and browser-evidence strategy
11. Traceability to screen slugs and product requirements

## Process

1. Read all sources, then list unresolved product or contract questions.
2. Map every design element accepted by its audit to real schema fields, operations, and permissions. Use exact OpenAPI paths and do not assume a client filter is server authorization.
3. Specify the React/Vite client-rendered SPA architecture and TanStack Router file-based routes. Define component data needs through the agreed query hooks and browser interactions through ordinary React components.
4. Specify mock mode with MSW and fixtures conforming to generated OpenAPI types. Keep screens on the same query hooks and API client when live mode is enabled.
5. For authenticated SSE, specify a fetch-based stream that can send the bearer token. Define reconnect and resync behavior from the actual event contract.
6. Write the specs under `work/frontend/specs/`, mark them `draft`, and present the decisions and file list for user review. Mark them `approved` only after approval.

## Completion

Every screen row has traceability to a route and a spec section. Every visible field, action, role gate, and API dependency agrees with the screen audit and backend source. Unknowns remain named questions; the specs contain no inferred product capabilities. The next skill is `frontend-tickets` after approval.
