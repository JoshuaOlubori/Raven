---
name: sdd-tech-spec
description: Break an approved PRD (work/prd.md) into technical specifications that follow the fastapi-production-architecture skill — one architecture spec plus one spec per domain module, each organised by the five layers (contracts, persistence, wiring, concurrency, shared state) with requirement traceability. Use after the PRD is approved, whenever the user says "tech spec", "technical design", "break the PRD down", "design the API/schema/architecture", or before any ticket is written. Do not write implementation code here.
---

# SDD Tech Spec

Turn *what and why* (PRD) into *how* (specs), using the user's `fastapi-production-architecture` skill as the binding standard.

## Before you start

1. **Read the standard.** Open the `fastapi-production-architecture` skill in full. Section map: §1 layer map, §2 layout and naming, §3 contracts, §4 persistence, §5 wiring and authorization (incl. testing the dependency graph), §6 concurrency and SSE, §7 shared state and multi-worker, §8 enterprise standards, §9 checklists. Quote section numbers in specs so reviewers can verify conformance.
2. **Read the inputs:** `work/prd.md`, `CONTEXT.md`, `docs/adr/*`, and any existing code (`src/`). Existing code is a fact to look up, not to ask about.
3. **Confirm the tracker exists** (`work/`). Run `sdd-setup` first if not.

## Process

### Step 1 — Architecture spec (`work/specs/00-architecture.md`)

Read `references/spec-templates.md` (Architecture section) and fill it in. Decide, per §2 of the standard, between the by-file-type layout (§2a) and the by-module layout (§2b). Recommend §2b when the PRD has more than ~2 domain areas. Cover: stack and versions, folder tree, config and secrets (§8), structured logging and correlation ids (§8), global error model, authN mechanism, DB engine/session strategy, migration tool, worker/process model (§7), test approach and seams, quality gates.

Take open technical **decisions** to the user one at a time with a recommendation (database engine, auth provider, cache, queue, hosting). Look up **facts** yourself. Record each hard-to-reverse decision as an ADR.

### Step 2 — Module specs (`work/specs/<domain>.md`)

Group PRD requirements into domain modules (one vertical slice each: router, schemas, models, service, dependencies, exceptions). For each module, read the Module section of `references/spec-templates.md` and fill every layer heading. Write "N/A — <reason>" for a layer that does not apply, so omissions are deliberate.

Each module spec ends with:
- **Traceability table:** PRD requirement id → spec section → endpoint(s).
- **Test seams:** for each behaviour, the seam where it is tested (schema unit, repository against a real DB, service with fakes, API through the dependency graph with `dependency_overrides`). `sdd-tickets` turns these into test suites.

### Step 3 — Cross-check

Run the standard's §9 *Generation checklist* against the specs and fix gaps. Then verify:
- every PRD requirement (`R-n`, `NFR-n`) appears in at least one traceability table;
- every endpoint names its auth guard and its error responses;
- no module spec relies on module-level mutable state (§7);
- naming follows §2's table (`DealCreate`, `get_deal_service`, `DbSessionDep`, `require_roles`…).

### Step 4 — Review with the user

Present a ≤20-line summary per spec: modules, endpoints count, key decisions, risks. Apply requested changes. Mark `Status: approved` in each spec's header only after the user says so.

### Step 5 — Log and hand off

`tracker.py log "tech specs approved: <list>" --phase spec`. Tell the user: specs approved → **clear context** → run `sdd-tickets` in a fresh session.

## Quality bar

A spec is ready when an engineer who has not seen the grilling could build the module from it without asking a question. Prefer tables (endpoints, schemas, state transitions) over prose. Show signatures and field lists; leave function bodies to implementation.
