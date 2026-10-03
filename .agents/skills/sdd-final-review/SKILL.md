---
name: sdd-final-review
description: Overall review of the whole backend once every ticket is done — PRD coverage matrix, architecture conformance, cross-ticket consistency, security, multi-worker and performance audits, migrations, and release readiness — producing work/reviews/final-review.md and follow-up tickets. Use when all tickets are done, or when the user says "final review", "review the whole thing", "are we ready to ship", "audit the codebase against the PRD".
---

# SDD Final Review

Per-ticket reviews see slices. This review sees the whole: gaps between tickets, drift from the architecture, and risks that only appear in combination. Run it in a fresh context on your strongest model.

## 0. Preconditions
`tracker.py list` shows every ticket `done`. If not, say which are open and stop.

## 1. Mechanical checks (run, don't eyeball)
- Full gates: ruff, format check, mypy, pytest with coverage. Record numbers.
- Migrations: apply to an empty database, then downgrade and upgrade again.
- App boots with production-like config; OpenAPI loads and matches the spec's endpoint tables.
- Static scans: Bandit (or equivalent), dependency audit, secret scan.

## 2. Review passes
Take each pass as a focused read of the codebase (use parallel sub-agents per pass when available).

1. **PRD coverage matrix.** Table: requirement → tickets → tests → status. Every `R-n` and `NFR-n` has a passing, meaningful test, or a recorded gap. Check *Out of scope* items did not sneak in.
2. **Architecture conformance.** Compare to `00-architecture.md` and the `fastapi-production-architecture` §9 checklists across all modules: layout and naming (§2), thin handlers and provider-based wiring (§5), async persistence with request-scoped sessions (§4), consistent error shape and global handler (§8).
3. **Authorization completeness.** Enumerate every route from the OpenAPI schema; compare with each module's authorization matrix; confirm a test exists for each route × role. Unauthenticated routes are intentional and listed.
4. **Performance and persistence.** N+1 audit on every list/detail path; indexes match query patterns; pagination bounds; blocking calls on the event loop; connection-holding streams (§6).
5. **Shared state and workers.** Grep for module-level mutable state, caches and counters; confirm each lives in an external store or is justified (§7). Note the no-GIL red zone items.
6. **Security.** Input validation at all boundaries, JWT verification (signature + expiry), CORS, rate limits, secrets in a vault/env only, logs free of PII/secrets, error messages that do not leak internals; compliance items from the PRD (retention, audit trail, data-subject flows).
7. **Cross-ticket consistency.** Duplicated helpers, divergent patterns between modules, inconsistent naming, dead code, stale TODOs, abandoned feature flags.
8. **Operability.** Structured logs with correlation ids, health/readiness endpoints, config documentation, README/runbook (how to run, test, migrate, deploy), `.env.example`.

## 3. Report
Write `work/reviews/final-review.md`: gate results, coverage matrix, findings grouped by pass with severity (blocker/major/minor/nit), and a verdict: **ship**, **ship after fixes**, or **do not ship**.

## 4. Turn findings into work
For each blocker and major, create a follow-up ticket in `work/tickets/` (next free `T-NNN`, `spec_refs` pointing at the finding) using the sdd-tickets template. Minors go into a *Backlog* list at the end of the report. Then:
`tracker.py log "final review: <verdict>; N follow-up tickets" --phase final-review`.

Follow-up tickets go through the normal `sdd-implement` → `sdd-ticket-review` loop; repeat this review only for the areas they touch.

## 5. Hand-off
Verdict ship → **clear context** → `sdd-retro`. Otherwise → **clear context** → `sdd-resume` to start the follow-up tickets.
