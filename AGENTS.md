# Agent Instructions

## Spec-driven development
- Backend pipeline: sdd-grill-prd → sdd-tech-spec → sdd-tickets → (sdd-implement → sdd-ticket-review)* → sdd-final-review → sdd-retro. Start backend sessions with sdd-resume.
- Frontend pipeline: frontend-resume → frontend-screens → frontend-setup → frontend-tech-spec → frontend-tickets → (frontend-implement → frontend-ticket-review)* → frontend-final-review (mock phase and explicit user sign-off) → (frontend-implement → frontend-ticket-review)* → frontend-final-review (release) → frontend-retro.
- Project state lives in work/ and work/frontend/; follow the matching tracker skill. Start each session with the resume skill for the workstream.
- Backend standard: fastapi-production-architecture. Frontend stack and quality gates: frontend-setup. Product contract: backend OpenAPI/specs. Screen set and project-specific Stitch retrieval instructions: work/frontend/screens.md, copied from docs/templates/frontend-screen-manifest.md for new projects. Glossary: CONTEXT.md. Decisions: docs/adr/.
- Quality gates: `uv run --directory backend ruff check`, `uv run --directory backend ruff format --check`, `uv run --directory backend mypy src`, `uv run --directory backend pytest -q`
- Frontend quality gates: configured `npm run lint`, `format`, `typecheck`, `test`, `test:e2e`, and `build`; visual tickets also require Playwright MCP browser evidence at their listed responsive widths.
- Conventional commits; one commit per ticket, message starts with the ticket id.
