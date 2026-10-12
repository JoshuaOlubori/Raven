---
name: frontend-screens
description: Prepare or refresh the project-specific screen manifest from local design exports or a design source such as Google Stitch, and audit every visible field and action against the backend contract. Use before frontend setup or whenever the screen set or backend contract changes.
---

# Frontend Screens

`work/frontend/screens.md` is the single project-specific input for design assets, screen routes, roles, API mappings, and scope gaps. The skill body stays reusable; project names and IDs belong in the manifest.

## Process

1. Read `work/frontend/screens.md`. If it is missing, copy `docs/templates/frontend-screen-manifest.md` there and fill in the project, design-source instructions, asset paths, and screen/reference rows. Treat the manifest as the project-specific source of truth; set its local export root to the supplied folder (conventionally `stitch_screens/`).
2. Read the product requirements, approved backend specs, and the current OpenAPI schema. Prefer the running backend's `/openapi.json`; inspect repository route/auth code when runtime OpenAPI is unavailable. Record the exact source and date in each audit.
3. Inspect the manifest's local export root before using any design connector. Read any shared design guidance file listed there (such as `DESIGN.md`). For each screen row, map its `Local export folder` to the exported `screen.png` and `code.html`. Read both in place and preserve the original exports. Record the folder path in the manifest; write its audit as `<export-root>/<folder>/AUDIT.md`. A local export is complete when both expected artifacts exist.
4. Use a configured design-source connector or MCP only for assets that are missing locally. A project or screen ID identifies an item; it is not a download URL. Use `curl -L` only on a hosted URL returned by the integration. Record unavailable assets instead of claiming retrieval succeeded.
5. For each `kind: reference` row, locate the local reference image and record its folder/path and a short note about the visual tokens or patterns it informs. If the listed reference was not exported, record it as missing; shared design-token files (for example `DESIGN.md`) inform styling but do not replace a missing reference image. Reference-only rows do not receive routes or tickets.
6. Write one `AUDIT.md` per screen. Map each visible data field, status, filter, action, and permission to a schema field, endpoint, and authorization rule. Mark each item `keep`, `modify`, or `remove`; cite the contract source. Rework content that has no API support so the remaining screen stays coherent. Do not create MSW fixtures for unsupported product features.
7. Record the local export folder, proposed route, roles, API operations, asset status, audit status, and unresolved scope gaps in the manifest. Leave uncertain values blank and ask the user only for decisions the sources cannot settle.
8. Show the screen inventory, scope gaps, and audit summaries for user review before technical specs and tickets are finalized.

## API audit rules

- Use exact paths, methods, query parameter names, payloads, response schemas, and auth requirements from OpenAPI. Preserve path spelling and trailing slashes exactly.
- Distinguish UI filtering from a backend authorization rule. A client-side dentist filter is not row-level server authorization.
- Do not infer pagination, inactive-record inclusion, nested visit history, audit fields, notifications, or actions from a visual design. Confirm that the API provides each one.
- When a design asks for unsupported data, remove that element or redesign the screen around supported data. Add the rationale to `AUDIT.md` and the manifest's scope gaps.
- For a screen with no backend operations, record that it is static/public or mark backend wiring `n/a`; do not invent an endpoint.
- Keep requested but unsupplied screens in `Open scope gaps`. Do not turn them into Stitch screens or ticket rows without a user decision.

## Completion

Every screen row points to local screenshot and code assets, has an audit with contract evidence, and has a proposed route/role mapping or an explicit unresolved question. Every reference has a local image and design note, or is explicitly recorded as missing. The user has seen the scope gaps before ticket generation begins. If an asset is unavailable from both local exports and the connector, record it and stop short of claiming the screen audit is complete.
