---
name: frontend-setup
description: Initialize the project's React 19 and Vite frontend with the agreed router, query/cache, state, UI, forms, validation, API types, mock transport, and quality gates. Use after screen intake is reviewed or when the user asks to bootstrap the frontend.
---

# Frontend Setup

Create the frontend foundation described by `work/frontend/specs/00-frontend-architecture.md`. Use the versions and generated configuration supported by the installed tools; commit the lockfile so the setup is repeatable.

## Before setup

1. Read `work/frontend/screens.md`, approved frontend specs, repository instructions, and current package/tool versions.
2. Confirm the screen inventory and API contract sources. Resolve any design or scope decisions needed for a coherent app shell.
3. Preserve existing project files. If `frontend/` contains work, inspect it and extend the current app instead of reinitializing it.

## Foundation

Use React 19, Vite, TanStack Router with file-based routes, TanStack Query, Zustand, shadcn/ui, Tailwind CSS, React Hook Form, Zod, and Biome. Create the route directory and router configuration required by the file-based router. Add a root layout, error/not-found routes, and shared app providers.

Configure Tailwind using the integration supported by the installed major version. For Tailwind v4, use the Vite plugin and CSS-first entry point; do not combine it with legacy v3 config files. Initialize Biome with the installed Biome CLI so its schema matches the package version. Use the shadcn CLI for supported primitives; compose a date picker from supported calendar/popover primitives when no date-picker registry item exists.

Use a Vite proxy for `/api` in local development so the browser talks to the frontend origin. Preserve each API path exactly as exposed by OpenAPI, including trailing slashes. For deployment, use the project's documented same-origin proxy or an explicitly configured CORS policy.

## API contract and mock mode

- Add `openapi-typescript` and generate types from the project's OpenAPI document when available. Keep the generation command and source URL configurable; regenerate types when the contract changes.
- If OpenAPI is not available, use approved backend specifications as a temporary source and mark unresolved contract questions. Do not claim handwritten types are generated.
- Implement one API client and TanStack Query hooks as the screen data boundary. Use the same hooks in both mock and live modes.
- Add MSW for development mock mode and tests. Fixtures and handlers must conform to generated OpenAPI types. Enable mock mode through a Vite environment setting; never include mock handlers in production.
- Do not add token refresh unless the backend exposes a refresh operation. Use only the auth lifecycle and token fields in the current contract.
- If the API exposes authenticated SSE, use a fetch-based SSE client capable of setting `Authorization: Bearer`; browser `EventSource` cannot set arbitrary auth headers. Treat the API's resync-required event as a query refetch signal.

## Suggested structure

```text
frontend/src/
  app/                 providers and router setup
  routes/              TanStack file-based routes
  components/ui/       generated shadcn primitives
  components/shared/   layout and common feedback components
  features/<domain>/   route sections, hooks, schemas, and UI
  lib/                 API client, query client, auth, utilities
  mocks/               MSW worker, handlers, contract-shaped fixtures
  types/               generated OpenAPI types and UI-only types
```

Keep domain modules aligned to audited screen groups and approved specs. Do not create features just because a design includes a control; first verify the API supports it.

## Quality gates

Configure package scripts for:

- `npm run lint` — Biome lint
- `npm run format` — Biome formatting check or formatting command supported by the pinned CLI
- `npm run typecheck` — TypeScript build-mode check (`tsc -b` for Vite project-reference templates)
- `npm run test` — Vitest and React Testing Library
- `npm run test:e2e` — the configured browser suite for critical interactions
- `npm run build` — Vite production build

Do not hand-copy a Biome schema from another major version. Verify each script against the generated app template and pinned package versions.

## Acceptance

- Vite starts and builds.
- File-based routes are generated and resolve the audited screen routes.
- Mock mode serves only contract-shaped data through the same API client/hooks intended for live mode.
- OpenAPI types can be regenerated from the declared source.
- The configured lint, format, typecheck, and test scripts run successfully.
- The local API proxy preserves the upstream API path and avoids cross-origin redirects.

## Hand-off

Record the setup and contract source in `work/frontend/JOURNAL.md`. The next skill is `frontend-tech-spec` unless the approved architecture spec already exists; then use `frontend-tickets`.
