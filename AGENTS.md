# Agent Instructions

## Spec-driven development
- Pipeline: sdd-grill-prd → sdd-tech-spec → sdd-tickets → (sdd-implement → sdd-ticket-review)* → sdd-final-review → sdd-retro
- All state lives in work/ (see sdd-tracker). Start every fresh session with sdd-resume.
- Technical standard: fastapi-production-architecture skill. Glossary: CONTEXT.md. Decisions: docs/adr/.
- Quality gates: `uv run --directory backend ruff check`, `uv run --directory backend ruff format --check`, `uv run --directory backend mypy src`, `uv run --directory backend pytest -q`
- Conventional commits; one commit per ticket, message starts with the ticket id.
