# Ticket template (work/tickets/T-NNN-slug.md)

```markdown
---
id: T-004
title: Approve a deal (RBAC + audit log)
status: todo
mode: AFK
blocked_by: T-002, T-003
spec_refs: specs/deals.md#4-layer-3, specs/deals.md#8-state-machine
covers: R-7, R-9
updated: YYYY-MM-DD
---

## Outcome
One or two sentences in domain language: what a user/client can do after this ticket that they could not before.

## What to build
End-to-end behaviour across layers (schema → persistence → provider → endpoint). Reference spec sections instead of restating them. Name the files expected to change.

## Acceptance criteria
- [ ] Given … When … Then …  (3–8 items, each observable through the API or a named seam)

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | test_approve_pending_deal_returns_200_and_sets_status | API + dependency_overrides | status code, body.status | PRD R-7 acceptance |
| 2 | test_approve_by_non_approver_returns_403 | API | 403 | authorization matrix |
| 3 | test_discount_above_cap_rejected | schema unit | ValidationError | PRD R-4 |

Rules: expected values come from the spec or PRD, never recomputed with the code's own logic. Tests live where the spec's *Test seams* table puts them.

## Out of scope
What this ticket deliberately leaves to other tickets.

## Notes for the implementer
Gotchas from the spec (e.g. close the session before streaming; use `TaskGroup`).

## Implementation log
_(filled by sdd-implement: decisions, deviations, commands run, commit sha)_

## Review history
_(links to work/reviews/T-004-review-N.md)_
```
