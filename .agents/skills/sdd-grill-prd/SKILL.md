---
name: sdd-grill-prd
description: Grill the user relentlessly about a backend idea until every branch of the decision tree is resolved, then write a detailed, traceable PRD to work/prd.md. Use at the start of any new backend, API or service, whenever the user says "I have an idea", "let's plan", "grill me", "write a PRD", or hands over a vague feature description — even if they do not mention a PRD. Do not skip to design or code; this skill is the front door of the spec-driven pipeline.
---

# SDD Grill → PRD

Two stages in one unbroken context window: **grill**, then **write**. The PRD is only as good as the grilling, so grill first and write second.

## Stage 1 — Grill

Interview the user until both of you share one understanding of what is being built and why.

**Rules of the interview**

- Ask **one question at a time** and give your **recommended answer** with it, so the user can accept in a word ("yes", "B").
- Split **facts** from **decisions**. Facts (existing code, repo conventions, library behaviour) you look up yourself. Decisions (scope, priorities, trade-offs, business rules) go to the human; you wait for their answer and you do not answer them yourself.
- Walk the decision tree depth-first: resolve a parent decision before its children, and revisit earlier answers when a later one contradicts them.
- Restate contradictions plainly and ask which side wins.
- Challenge fuzzy terms. When the user uses a word that could mean two things (customer, account, approval), pin the definition and add it to `CONTEXT.md` immediately.
- Stress-test with concrete scenarios: "A manager approves a deal while the customer is being merged — what should happen?"
- Offer an ADR (`docs/adr/NNNN-*.md`) when a decision is hard to reverse, surprising without context, and the result of a real trade-off. Write it as you go.

**Coverage.** Work through the branches in `references/question-bank.md` (problem and users, domain model, API behaviour, auth, data, async and streaming, integrations, non-functional needs, compliance, operations, scope). Skip branches that do not apply and say so in one line. Open the file when you start grilling.

**Pacing.** Group the early questions around the outcome and users, then go deeper. Keep a running "Resolved / Open" list in your head and read it back every ~10 questions so the user can correct drift.

**Confirmation gate.** When no open branches remain, summarise the shared understanding in ≤15 lines and ask: "Is this the right shape — shall I write the PRD?" Move to Stage 2 only after an explicit yes.

## Stage 2 — Write the PRD

Synthesize what was said. Ask no new questions here; anything still unknown goes under *Open questions* with an owner.

1. Read `references/prd-template.md` and fill it in. Write to `work/prd.md`.
2. Give every functional requirement a stable id (`R-1`, `R-2`…) and an acceptance criterion in Given/When/Then form, because later skills trace tickets and tests back to these ids.
3. Use the glossary terms from `CONTEXT.md` exactly.
4. Keep the PRD about *what and why* (behaviour, rules, constraints). Technology choices belong to `sdd-tech-spec`, except constraints the user stated as hard requirements.
5. Log: `tracker.py log "PRD written (N requirements)" --phase prd`.
6. Show the user a ≤10-line summary and ask them to review `work/prd.md`. Apply edits they request.

## Hand-off

Tell the user: PRD approved → **clear context** → run `sdd-tech-spec` in a fresh session (on your strongest model). The PRD and glossary carry the thinking forward, so the grilling transcript can be dropped.
