# Spec-driven backend workflow — playbook

## The idea in one paragraph

Every phase writes its result to a markdown file in `work/`. Because the files hold the memory, each phase can start in a clean context window, and the model only ever sees what it needs. `sdd-resume` is the first thing you type in every new session; `sdd-tracker` is how every skill records what happened.

```
work/
  prd.md → specs/ → tickets/ → reviews/ → final-review.md → retro.md
  TRACKER.md (board)        JOURNAL.md (history, append-only)
```

## Setup (once)

1. `./install.sh` (copies `sdd-*` into `.claude/skills/`; copy your `fastapi-production-architecture` skill next to them).
2. New session → `sdd-setup`. Confirms quality-gate commands, creates `work/`, `CONTEXT.md`, `docs/adr/`, and the block in `CLAUDE.md`.
3. Commit. Commit `work/` too: the tracker and journal are your project history.

## The sessions, in order

| # | Session | You type | Reads | Writes | Model tier |
|---|---|---|---|---|---|
| 1 | Grill + PRD | `sdd-grill-prd` + your idea | CONTEXT.md | `prd.md`, CONTEXT.md, ADRs | Strongest |
| 2 | Tech spec | `sdd-resume` → `sdd-tech-spec` | prd.md, standard, code | `specs/*.md`, ADRs | Strongest |
| 3 | Tickets + tests | `sdd-resume` → `sdd-tickets` | prd, specs | `tickets/*`, `test-strategy.md` | Strongest |
| 4a | Implement ticket T-n | `sdd-resume` → `sdd-implement` | ticket, spec refs, standard | code, tests, ticket log | Cheaper |
| 4b | Review ticket T-n | `sdd-ticket-review T-n` | diff, ticket, specs | `reviews/T-n-review-k.md` | Strong, ideally a different model from 4a |
| 4c | Fix round (if needed) | `sdd-implement T-n` | review report | code, log | Cheaper |
| 5 | Final review | `sdd-final-review` | everything | `final-review.md`, follow-up tickets | Strongest |
| 6 | Retro | `sdd-retro` | journal, reviews | `retro.md` | Strong |

Steps 4a/4b repeat per ticket. 4c repeats until 4b approves (after two failed rounds, stop and re-examine the spec or the slicing with the user).

## When to clear the session

**Clear at these boundaries** (state is already in `work/`):

1. **After the PRD is approved** (session 1 → 2). Tech design is a different kind of thinking and loads heavy context (the standard, the codebase); starting fresh keeps it sharp. The PRD, glossary and ADRs are the hand-off.
2. **After specs are approved** (2 → 3), and again **after tickets are approved** (3 → 4).
3. **After every ticket commit** (4a → 4b → next 4a). One ticket per session keeps diffs reviewable and context small.
4. **Before every review**, so the reviewer judges the code without the author's reasoning in its head.
5. **Before the final review and the retro.**
6. **When you switch model tier** (planning on the strong model, build on the cheap one): a new session carries the files, not the old model's chat.
7. **When a session degrades:** the agent repeats itself, forgets a decision, contradicts the spec, or has failed the same fix three times. Run `sdd-resume` in checkpoint mode, clear, and resume. A fresh read of the ticket usually solves what the long thread could not.

**Keep the window open at these points:**

- **Grill → PRD stays in one window.** The PRD is a synthesis of the whole interview, so the model needs the conversation to write it.
- **Mid-ticket.** Finish the red → green loop and commit before clearing; if you must stop early, run checkpoint mode first.
- **Mid-review**, until the report is written and the ticket status is set.
- **Small projects:** if the whole grilling is short and the context window is under roughly a third full when the PRD is approved, you can continue straight into `sdd-tech-spec`. Clearing is cheap insurance, not a ritual.

**Every new session starts the same way:** type `sdd-resume`. It reads the tracker, tells you the phase and the next skill, and checks git agrees.

## Model tiers (spend where thinking is hard)

- **Strongest model:** grilling, tech spec, ticket slicing, final review. Mistakes here multiply downstream.
- **Cheaper model:** `sdd-implement`. Specs and tickets are detailed enough that implementation becomes execution, and the test plan keeps it honest.
- **Strong model for ticket review**, ideally different from the implementer. A strong reviewer over a cheap builder catches the most per dollar.

## Cadence for a typical day

1. `sdd-resume` → shows the next ticket.
2. `sdd-implement` (cheap model) → commit → clear.
3. `sdd-ticket-review` (strong model) → `done` or `changes-requested` → clear.
4. Repeat. End of day: `sdd-resume` checkpoint.

For independent tickets (several in `tracker.py next`), run implementations in parallel git worktrees, one session each; merge after each ticket's review approves.

## When things change

| Situation | Do this |
|---|---|
| Spec is wrong or incomplete | Stop the ticket. New session: edit the spec (`sdd-tech-spec`, amendment), log it, then update affected tickets. |
| New requirement | Amend `prd.md` with a new `R-n` (grill the delta with `sdd-grill-prd`), update the spec, add tickets with `sdd-tickets` (append). |
| Bug after merge | Add a ticket describing the failing behaviour; the test that reproduces it is the first row of its test plan. |
| Project too large for one planning session | Run grill → PRD per area, or use Matt Pocock's `wayfinder` to map the decisions first, then feed each area into `sdd-tech-spec`. |
| Final review finds problems | Follow-up tickets enter the normal loop; re-run the final review only on the areas touched. |

## Pairing with Matt Pocock's skills

These skills adapt ideas from his repo (`mattpocock/skills`, MIT): `grill-me` / `grill-with-docs` (interview, glossary, ADRs), `to-spec` + `to-tickets` (vertical slices, blocking edges, HITL/AFK), `tdd` (red → green at agreed seams), `code-review` (Standards + Spec axes, Fowler smells), `retro`, and `setup-matt-pocock-skills` (local-markdown tracker). Skills worth installing beside them: `diagnosing-bugs` for stubborn failures, `domain-modeling` for sharpening the glossary, `research` for background reading on a library, `improve-codebase-architecture` after the final review.
