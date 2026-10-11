---
name: frontend-retro
description: Analyze frontend journal entries, ticket reviews, and final review to identify repeated workflow problems and improve the reusable frontend process. Use after release review, after a ticket that went poorly, or when the user asks for a frontend retrospective.
---

# Frontend Retrospective

Review `work/frontend/JOURNAL.md`, ticket review reports, phase/release review reports, and the changed files for the selected period.

## Process

1. Group concrete incidents by cause: unclear manifest inputs, contract drift, design audit gaps, ticket slicing/dependencies, mock/live seams, responsive/browser validation, quality gates, or hand-off.
2. Separate repeated process failures from one-off product decisions. Support each finding with ticket IDs or file references.
3. Propose the smallest reusable change to a `frontend-*` skill, manifest template, tracker, or quality gate that would prevent recurrence.
4. Write `work/frontend/reviews/retrospective-<date>.md` with evidence, proposed changes, expected effect, and an owner.
5. Apply only changes already authorized by the user or clearly local, reversible documentation fixes. Keep product code out of scope.

## Completion

The retrospective distinguishes evidence from recommendations and leaves the reusable workflow easier to run. Record the session in `work/frontend/JOURNAL.md`.
