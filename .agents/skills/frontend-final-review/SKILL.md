---
name: frontend-final-review
description: Review either the completed mock UI phase before user sign-off or the completed backend-wired frontend for release readiness. Use when all tickets in the selected phase are done.
---

# Frontend Final Review

Choose scope explicitly: `mock-phase` or `release`. Read the screen manifest, approved specs, all relevant tickets/reviews, tracker, journal, browser evidence, and current diff.

## Mock phase review

1. Confirm every screen mock ticket is done and each screen has Playwright MCP screenshots at 375, 768, 1024, and 1440 CSS-pixel widths.
2. Compare the complete screen set and navigation to the manifest, including reference use and audited design changes.
3. Confirm mock mode uses MSW and contract-shaped fixtures through the API client/hooks, with no API-unsupported feature represented as available behavior.
4. Inspect responsive layouts, accessibility behavior, loading/empty/error/permission states, and the configured quality gates.
5. Write `work/frontend/reviews/mock-phase-review.md`, summarize any required changes, then set the phase gate to `awaiting-signoff`.
6. Present the review and representative screenshots to the user. If they request changes, make/update tickets and keep the gate open. If they approve, set the gate ticket to `done`; this releases Phase B backend tickets.

Do not wire any screen to the live backend before the user approves the global mock-phase gate.

## Release review

1. Confirm every backend ticket is done and each audited API dependency is wired or marked `n/a` in the manifest.
2. Trace each approved screen and product requirement from manifest to spec, route, API operation, ticket, and evidence.
3. Verify authentication, role and permission behavior, server errors, loading/empty states, live updates when specified, and production mock-mode configuration.
4. Inspect responsive screenshots and the critical workflows in the Playwright MCP; run repository quality gates and the production build.
5. Check the final diff for unsupported features, stale API types, accessibility problems, data leaks, and unnecessary complexity.
6. Write `work/frontend/reviews/final-review.md` with a coverage matrix, findings, quality-gate evidence, and a clear release-ready or not-ready verdict. Record follow-up work as tickets only when it is in the approved scope.

## Completion

The selected review report exists, all conclusions cite evidence, and the tracker reflects the decision. A mock-phase review stops at user sign-off; a release review does not stand in for the user's product approval.
