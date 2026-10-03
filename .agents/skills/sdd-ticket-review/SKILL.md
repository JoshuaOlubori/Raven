---
name: sdd-ticket-review
description: Review the code for one completed ticket along three axes — Spec (does it do what the ticket, tech spec and PRD ask), Standards (fastapi-production-architecture checklist plus code-smell baseline) and Tests (are the tests meaningful) — write a review report to work/reviews/, and move the ticket to done or changes-requested. Use right after sdd-implement finishes a ticket, or when the user says "review T-00X", "check this ticket", "is this ready to merge". Best run in a fresh context.
---

# SDD Ticket Review

Review the diff of one ticket against what was asked and how this repo builds things. Report findings; leave the code as you found it (the implementer fixes).

## 1. Gather
- Ticket id from the user, else `tracker.py list --status in-review`.
- Diff: the ticket's commit(s) from its *Implementation log* (`git diff <base>..<sha>`).
- Spec sources: the ticket, the specs in `spec_refs`, PRD requirements in `covers`.
- Standards sources: `fastapi-production-architecture` (§9 checklists and review smells), `work/specs/00-architecture.md`, `CONTEXT.md`, `docs/adr/`, and the Fowler baseline below.
- Run the quality gates yourself (ruff, mypy, pytest) and record the results.

When the environment supports sub-agents, run the three axes as parallel sub-agents with their own context, then aggregate. Otherwise review the axes one after another.

## 2. Axes

### Spec — "does it do what was asked?"
For each acceptance criterion: find the code and the test that satisfy it, or flag it. Quote the spec line for every finding. Flag missing behaviour, extra behaviour not in the ticket (scope creep), and silent deviations from the spec's endpoints, status codes, error codes, or state machine.

### Standards — "does it follow how we build?"
Check the diff against the standard's smells and checklist:
- Handler opens its own session or builds services inline (Layer 3) · role checks scattered as `if user.role` (Layer 3) · business rules in handlers instead of schema validators (Layer 1) · v1 idioms `parse_obj()` / `dict()` (Layer 1) · per-row queries / missing eager loading (Layer 2) · blocking work on the event loop (Layer 4) · module-level mutable state (Layer 5) · sessions held open across streaming (Layer 4) · wrong 401 vs 403 · naming deviations from §2 · missing correlation id / structured logging · secrets or config inline.
- Fowler baseline (judgement calls; a documented repo rule overrides): Mysterious Name, Duplicated Code, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man, Refused Bequest.

### Tests — "would these tests catch a regression?"
- Every acceptance criterion has a test at the seam the ticket named.
- Expected values are independent of the implementation (flag tautological assertions that recompute the answer the way the code does).
- Tests assert behaviour, not private structure; they would survive a refactor.
- Failure paths exist: 401/403/404/409/422 where the spec lists them.
- No sleeps, order dependence, or shared mutable fixtures.

## 3. Report
Write `work/reviews/T-NNN-review-N.md` (N counts rounds):

```markdown
# Review T-NNN round N — <verdict>
Gates: ruff ✓/✗ · mypy ✓/✗ · pytest ✓/✗ (n passed)
## Spec        — findings (quote the spec line)
## Standards   — findings (cite standard § or smell)
## Tests       — findings
## Summary     — counts per severity; the single worst issue
```

Severity: **blocker** (wrong behaviour, security hole, failing gate) · **major** (standard violation, missing test for a criterion) · **minor** · **nit**. Each finding states file:line, the problem, and the fix direction.

## 4. Verdict and tracker
- **Approve** (no blockers, no majors, gates green): `tracker.py set T-NNN done`.
- **Changes requested:** `tracker.py set T-NNN changes-requested`. The implementer addresses blockers and majors; minors are optional.
- Append the review link to the ticket's *Review history* and `tracker.py log "review round N: <verdict>, B/M/m counts" --ticket T-NNN`.
- After two changes-requested rounds on the same ticket, stop and ask the user: the spec or the slicing is probably the real problem.

## 5. Hand-off
Approved → **clear context** → `sdd-resume` for the next ticket. Changes requested → **clear context** → `sdd-implement` for the same ticket.
