---
name: sdd-tickets
description: Break approved technical specs into tracer-bullet vertical-slice tickets and test suites, written as markdown files in the work/ tracker with blocking edges, acceptance criteria, and per-ticket test lists, plus a project test strategy. Use after the tech specs are approved, or whenever the user says "break this into tickets", "create the backlog", "plan the work", "write the test suites", "what should we build first". Produces no production code.
---

# SDD Tickets + Test Suites

Convert `work/specs/*` into the backlog the implementation loop will consume. One ticket = one reviewable, independently verifiable unit of behaviour.

## Inputs
`work/prd.md`, `work/specs/00-architecture.md`, `work/specs/<domain>.md`, `CONTEXT.md`. Read the `sdd-tracker` skill for the ticket format.

## Slicing rules

1. **Vertical slices (tracer bullets).** Each ticket cuts through every layer it needs (schema → persistence → provider → endpoint → test) and delivers observable behaviour through the API. Horizontal tickets such as "create all models" strand work that cannot be verified.
2. **Ticket 1 is the walking skeleton:** app factory, config, health endpoint, DB session provider, error handler, test client fixtures, CI gates green. Everything else builds on it.
3. **Size:** one session of work, ≤ ~400 changed lines, 3–8 acceptance criteria. Split anything bigger along a behaviour boundary (create → read → update → transition → list/filter).
4. **Dependencies:** declare `blocked_by` edges explicitly. Keep the graph shallow so several tickets stay ready at once.
5. **Mode:** mark a ticket `HITL` when a human must decide or act (provisioning a secret, choosing a provider, signing off a migration on real data). Mark everything else `AFK`.
6. **Cross-cutting concerns become tickets of their own** when they carry risk: authorization matrix, audit log, SSE stream, background job, rate limiting, observability. Place each right after the first endpoint that needs it.
7. **Trace everything.** Every PRD requirement is covered by ≥1 ticket; every ticket cites `spec_refs` and requirement ids.

## Process

1. **Draft the slice list** as a table (id, title, requirements, blocked_by, mode) and show it to the user. Ask: granularity right? dependencies right? anything to merge or split? Iterate until approved.
2. **Write the test strategy** `work/test-strategy.md` from `references/test-strategy-template.md`: test pyramid for this service, seams, fixtures, data builders, which suites run where, and the cross-cutting suites (authorization matrix, N+1 query-count guards, contract/OpenAPI snapshot, SSE reconnection, concurrency/failure paths).
3. **Write each ticket** to `work/tickets/T-NNN-<slug>.md` using `references/ticket-template.md`. The *Test plan* lists the tests by name, with the seam and the assertion's source of truth, so implementation can go red → green one test at a time.
4. **Validate:** run `tracker.py board` and `tracker.py next`; confirm exactly the expected tickets are ready and no ticket is orphaned or cyclic. Check the coverage table (requirement → tickets) has no empty rows.
5. **Log:** `tracker.py log "N tickets created, coverage complete" --phase tickets`.

## Hand-off

Tell the user: backlog approved → **clear context** → start the implementation loop with `sdd-resume`, which picks the first ready ticket and hands it to `sdd-implement`.
