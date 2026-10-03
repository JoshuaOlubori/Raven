---
name: sdd-retro
description: Post-build retrospective that improves the agent's environment, not the code — reads the journal and reviews, finds repeated failures, and proposes concrete changes to CLAUDE.md rules, skills, specs templates, lint rules, test helpers and tooling. Use after sdd-final-review ships, after a ticket that went sideways, or when the user says "retro", "what should we improve", "why did the agent keep making that mistake".
---

# SDD Retro

Target: make the next project go smoother. Findings about the code belong to review; findings about *how the agent works here* belong to this retro.

## Steps
1. Read `work/JOURNAL.md`, all `work/reviews/*.md`, and ticket *Implementation logs* (deviations and assumptions).
2. Mine for patterns, each with evidence (ticket ids):
   - findings that recurred across reviews (same smell, same layer);
   - tickets that needed ≥2 review rounds, and why;
   - spec ambiguities that surfaced during implementation;
   - sessions that stalled or lost context;
   - manual steps repeated by hand.
3. For each pattern, propose a fix in one of these homes, most durable first: an automated check (ruff rule, mypy setting, pre-commit hook, architecture test) → a steering rule in `CLAUDE.md` → an edit to the `fastapi-production-architecture` skill or an sdd-* skill → a test helper/fixture → a template change in `sdd-tech-spec` or `sdd-tickets`.
4. Write `work/retro.md`: findings ranked by severity, each with evidence, proposed fix, and its home. Keep it to the top 5–8.
5. Offer to apply the approved fixes now. `tracker.py log "retro written; N fixes proposed" --phase retro`.
