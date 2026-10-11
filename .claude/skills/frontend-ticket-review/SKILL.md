---
name: frontend-ticket-review
description: Independently review one completed frontend ticket against its acceptance criteria, screen audit, API contract, responsive behavior, and tests. Use after frontend-implement or when the user requests review of an FT ticket.
---

# Frontend Ticket Review

Review one ticket at a time. Read its full ticket, referenced specs, screen audit, implementation log, relevant diff, and existing evidence before reaching a verdict.

## Review

1. Verify every acceptance criterion against the implementation and evidence.
2. Compare visible content and behavior to the audited Stitch screen. Confirm that removed/modified design elements stay removed and that no API-unsupported feature is implied.
3. Verify role visibility against actual endpoint authorization. Treat client-side filtering as presentation only.
4. For backend tickets, compare requests, response types, error handling, and exact URL paths against OpenAPI.
5. Inspect the screen in the Playwright MCP at 375, 768, 1024, and 1440 CSS-pixel widths. Save evidence to `work/frontend/evidence/<ticket-id>/` and visually inspect every screenshot for clipping, overflow, unusable controls, and broken hierarchy.
6. Review test seams, expected values, loading/empty/error states, form validation, keyboard navigation, and focus behavior.
7. Run the configured lint, format, typecheck, relevant tests, and build when repository instructions require them. Report commands that could not run.

## Report

Write `work/frontend/reviews/<ticket-id>-review-<n>.md` with:

- ticket, review number, date, and verdict
- concise summary
- acceptance-criteria table with evidence
- design/responsive/browser evidence, including four screenshot paths
- API/permission assessment for backend work
- tests and quality-gate results
- findings grouped by blocker, major, minor, and nit, each with file/line evidence
- next action

Request changes for any blocker, an unmet acceptance criterion, a material design/API mismatch, or missing required browser evidence. Minor polish findings may accompany an approval.

## Tracker status

- On changes requested, set the ticket to `changes-requested` and give ordered, actionable fixes.
- On approval of a mock ticket, set it to `done`; the global mock-phase gate still requires final phase review and explicit user sign-off.
- On approval of a backend ticket, set it to `done`.

Never mark the mock phase gate `done` as part of an individual ticket review. Only `frontend-final-review` presents the whole mock phase for user sign-off.
