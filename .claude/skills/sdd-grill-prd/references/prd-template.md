# PRD template (write to work/prd.md)

```markdown
# <Product / service name> — PRD

_Status: draft | approved · Date · Owner_

## 1. Problem and goals
Why this exists, who it serves, what success looks like (measurable).

## 2. Actors and roles
| Actor | Description | Can | Cannot |
|---|---|---|---|

## 3. Glossary
Link to CONTEXT.md; list the 5–10 terms the reader must know.

## 4. Functional requirements
Each requirement has a stable id and an acceptance criterion.

### R-1 <short name>
- **Behaviour:** what the system does.
- **Rules:** invariants and edge cases.
- **Acceptance:** Given … When … Then …
- **Priority:** must | should | could

(repeat R-2 … R-n; group by domain area)

## 5. Domain model (conceptual)
Entities, relationships, lifecycles/state transitions (a small state table or mermaid diagram).

## 6. Non-functional requirements
Performance, availability, scale, security, compliance, observability — each as a testable statement with an id (NFR-1 …).

## 7. Integrations and constraints
External systems, hard technology constraints stated by the user, deployment target.

## 8. Out of scope (v1)
Explicitly excluded items and the reason.

## 9. Risks and open questions
| # | Question / risk | Owner | Needed by |
|---|---|---|---|

## 10. Decision log
Links to ADRs created during grilling.
```
