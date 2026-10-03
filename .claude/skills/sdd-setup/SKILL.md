---
name: sdd-setup
description: One-time repo setup for spec-driven backend development with the sdd-* skills. Use at the very start of a new backend project, or when the user says "set up the SDD workflow", "initialise the tracker", "bootstrap the project for spec-driven development". Creates the work/ tracker, CONTEXT.md glossary, docs/adr/, and the agent-instruction block that points every sdd-* skill at the right files.
---

# SDD Setup

Run once per repo. Explore, confirm with the user, then write.

## Steps

1. **Explore.** Read `git remote -v`, any existing `CLAUDE.md` / `AGENTS.md`, `pyproject.toml`, `work/`, `CONTEXT.md`, `docs/adr/`. Note the Python version, package manager (uv/poetry/pip), and whether a test runner and linters already exist.
2. **Confirm the standards skill.** The technical standard for this backend is the `fastapi-production-architecture` skill. Check it is installed in the same skills directory. If it is missing, ask the user where it lives and record the path.
3. **Confirm the quality gates** with the user (propose these defaults): `ruff check`, `ruff format --check`, `mypy`, `pytest -q`. Record the exact commands.
4. **Initialise the tracker:** run `python <skills-dir>/sdd-tracker/scripts/tracker.py init`.
5. **Create `CONTEXT.md`** at the repo root with a `# Glossary` heading and one line explaining that terms get added during grilling. Create `docs/adr/` with a short `README.md` stating the ADR convention: `NNNN-title.md`, sections Context / Decision / Consequences.
6. **Write the agent block** into `CLAUDE.md` (or `AGENTS.md` if that is what exists; ask if neither does):

```
## Spec-driven development
- Pipeline: sdd-grill-prd → sdd-tech-spec → sdd-tickets → (sdd-implement → sdd-ticket-review)* → sdd-final-review → sdd-retro
- All state lives in work/ (see sdd-tracker). Start every fresh session with sdd-resume.
- Technical standard: fastapi-production-architecture skill. Glossary: CONTEXT.md. Decisions: docs/adr/.
- Quality gates: <commands confirmed in step 3>
- Conventional commits; one commit per ticket, message starts with the ticket id.
```

7. **Log and report.** Run `tracker.py log "repo set up for SDD" --phase setup`. Tell the user the next step is `sdd-grill-prd`, in a fresh context window.
