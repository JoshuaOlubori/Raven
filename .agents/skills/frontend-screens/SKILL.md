---
name: frontend-screens
description: Prepare or refresh the project-specific screen manifest from a design source such as Google Stitch, export the referenced screen assets, and audit every visible field and action against the backend contract. Use before frontend setup or whenever the screen set or backend contract changes.
---

# Frontend Screens

`work/frontend/screens.md` is the single project-specific input for design assets, screen routes, roles, API mappings, and scope gaps. The skill body stays reusable; project names and IDs belong in the manifest.

## Process

1. Read `work/frontend/screens.md`. If it is missing, copy `docs/templates/frontend-screen-manifest.md` there and fill in the project, design-source instructions, asset paths, and screen/reference rows.
2. Read the product requirements, approved backend specs, and the current OpenAPI schema. Prefer the running backend's `/openapi.json`; inspect repository route/auth code when runtime OpenAPI is unavailable. Record the exact source and date in each audit.
3. For each `kind: screen` row, use the configured design-source connector or MCP to fetch the screenshot and source/code. A project or screen ID identifies an item; it is not a download URL. Use `curl -L` only on a hosted URL returned by the integration. Save `screen.png` and `code.html` under the manifest's asset root and the screen slug.
4. For each `kind: reference` row, save the reference image and write a short note about the reusable visual tokens or patterns it informs. Reference-only rows do not receive routes or tickets.
5. Write `<screen-slug>/AUDIT.md`. Map each visible data field, status, filter, action, and permission to a schema field, endpoint, and authorization rule. Mark each item `keep`, `modify`, or `remove`; cite the contract source. Rework content that has no API support so the remaining screen stays coherent. Do not create MSW fixtures for unsupported product features.
6. Record a proposed route, roles, API operations, asset status, audit status, and unresolved scope gaps in the manifest. Leave uncertain values blank and ask the user only for decisions the sources cannot settle.
7. Show the screen inventory, scope gaps, and audit summaries for user review before technical specs and tickets are finalized.

## API audit rules

- Use exact paths, methods, query parameter names, payloads, response schemas, and auth requirements from OpenAPI. Preserve path spelling and trailing slashes exactly.
- Distinguish UI filtering from a backend authorization rule. A client-side dentist filter is not row-level server authorization.
- Do not infer pagination, inactive-record inclusion, nested visit history, audit fields, notifications, or actions from a visual design. Confirm that the API provides each one.
- When a design asks for unsupported data, remove that element or redesign the screen around supported data. Add the rationale to `AUDIT.md` and the manifest's scope gaps.
- For a screen with no backend operations, record that it is static/public or mark backend wiring `n/a`; do not invent an endpoint.
- Keep requested but unsupplied screens in `Open scope gaps`. Do not turn them into Stitch screens or ticket rows without a user decision.

## Completion

Every screen row has local screenshot and code assets, an audit with contract evidence, and a proposed route/role mapping or an explicit unresolved question. Every reference has a local image and design note. The user has seen the scope gaps before ticket generation begins. If a connector or URL is unavailable, record precisely which assets remain unavailable and stop short of claiming the screen audit is complete.
