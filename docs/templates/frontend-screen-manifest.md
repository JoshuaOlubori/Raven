# Frontend screen manifest

Copy this file to `work/frontend/screens.md` when starting a frontend project. It is the project-specific source for screen intake and ticket generation; edit it for each new project.

## Project

- Product:
- Stitch project ID:
- Stitch project URL:
- Manifest owner:

## Screen retrieval request

Record the project and screen IDs and required artifacts here. If screen exports are supplied locally, list their root and folder mapping in the table below and use those files first. Use a configured Stitch integration only to fill gaps in the local exports. A screen ID is not a hosted download URL; use `curl -L` only for hosted URLs returned by the integration.

## Output

- Local export root (editable): `stitch_screens/`
- Per screen export: `<folder>/screen.png` and `<folder>/code.html`; preserve source exports in place and add `<folder>/AUDIT.md`
- Per reference: record its path and a short note describing how it informs the design system

## Contract and product sources

- OpenAPI URL or checked-in schema:
- Backend specifications:
- Product requirements:
- Frontend specifications: `work/frontend/specs/`
- API type generation source:

Use the OpenAPI schema as the endpoint and payload source of truth. Use approved backend specs when the OpenAPI document is not available yet, and label any unresolved contract question in the audit. Do not invent a supported field, operation, permission, or server-side rule.

## Global design notes

- Target users and roles:
- Supported languages and locale:
- Responsive requirements:
- Known product constraints:

## Screens and references

| Slug | Name | Design source ID | Kind (`screen` / `reference`) | Local export folder | Proposed route | Roles | API operations to audit | Asset status | Audit status | Mock ticket | Backend ticket |
|---|---|---|---|---|---|---|---|---|---|

Use `pending` for asset and audit status until the files and contract audit exist. Keep reference-only rows out of the route and ticket lists. Leave uncertain routes, roles, or endpoint mappings blank until audited.

## Open scope gaps

Record product requirements that have no supplied screen, and screen content that has no matching API capability. For each item, record the source, decision owner, and disposition. Keep unresolved items out of the implementation backlog until a person chooses a disposition.

| Item | Source | Gap | Decision | Disposition |
|---|---|---|---|---|

## Sign-off

- Screen set reviewed by:
- Mock UI phase approved by:
- Date:
- Notes:
