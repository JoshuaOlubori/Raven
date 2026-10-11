---
name: frontend-implement
description: Implement exactly one ready frontend ticket, following its mock or backend phase, the approved screen audit and frontend specs, then verify it and hand it to review. Use for a named FT ticket, a ready ticket selected by frontend-resume, or requested fixes to a changes-requested ticket.
---

# Frontend Implement

Implement one `FT-*` ticket per run. Read repository instructions, the ticket, referenced specs, the corresponding screen audit, and the current diff before editing.

## 1. Verify scope and phase

- Confirm the ticket exists, its `blocked_by` entries are done, and it is not waiting for user sign-off.
- Read `phase` and follow the matching path below.
- Update the ticket to `in-progress` with `frontend-tracker`.
- If the ticket requires an unresolved design, scope, permission, or API decision, continue independent work and ask only for that decision.

## 2. Implement the ticket

Use the ticket's test plan and approved API/design sources. Add focused tests before implementation when the ticket requests behavior changes. Keep components small and accessible, forms on React Hook Form plus Zod, server state in TanStack Query, shared client state in Zustand, and shareable filters in the URL.

### Mock phase

- Use the stable API client and query hooks with MSW handlers in mock mode. Fixtures conform to OpenAPI-generated types or approved contract specs.
- Build only audited fields/actions. Remove or redesign unsupported Stitch content; do not make it look like a real backend capability through mock data.
- Keep MSW enabled in development mock mode and tests, and disabled in production.
- Use the Playwright MCP in the browser to inspect the route at 375, 768, 1024, and 1440 CSS-pixel widths. Save and inspect screenshots under `work/frontend/evidence/<ticket-id>/`.

### Backend phase

- Verify every request against the current OpenAPI contract and the backend ticket dependencies.
- Enable the live transport through the existing API client/hooks; preserve exact paths, methods, query names, payloads, and trailing slashes.
- Handle the error states the API can return, including authentication, permission, validation, conflict, and missing-resource errors when applicable.
- Keep MSW handlers for tests, but ensure the configured live mode does not intercept requests.
- If an authenticated SSE stream is part of the ticket, use fetch-based streaming so the bearer token can be sent. On the contract's resync-required event, invalidate/refetch the relevant TanStack Query data.

## 3. Verify

Run the ticket's tests and applicable repo quality gates from its spec. Use the Playwright MCP to exercise the screen in the browser and capture the four required widths for visual tickets. Check keyboard access, focus, overflow, loading/empty/error states, and that the displayed data/actions match the screen audit. Do not claim a browser check or command passed unless it ran successfully.

## 4. Finish

1. Mark each acceptance criterion with its concrete evidence.
2. Run lint, formatting, typecheck, relevant tests, and build using the project's configured scripts.
3. Record files, decisions, deviations, commands, and screenshot paths in the implementation log.
4. Commit one ticket using the repository's ticket-prefixed conventional commit format.
5. Set the ticket to `in-review` and log the transition.

## 5. Hand-off

Tell the user which ticket is ready for `frontend-ticket-review`. For mock-phase tickets, explain that code review does not release backend wiring: the global mock-phase gate remains blocked until every mock screen is reviewed and the user approves the rendered result.
