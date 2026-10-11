---
name: frontend-implement
description: Implement exactly one frontend ticket from the work/frontend/ tracker test-first (red → green, one test at a time), following the frontend tech spec and frontend-setup standards, then run quality gates, commit, and hand the ticket to review. Use whenever the user says "implement FT-00X", "build the next frontend ticket", "start frontend coding", "address the frontend review comments", or after frontend-resume selects a ticket. Handles both first-time implementation and fixing a changes-requested review.
---

# Frontend Implement (one ticket per session)

One ticket, one context window, one commit series. Finishing a ticket and clearing context keeps each review small and each session sharp.

## 0. Pick and Claim
- If no ticket id was given, run `tracker.py next` (from frontend-tracker) and propose the first ready ticket; confirm with the user.
- Run `tracker.py set FT-NNN in-progress`.

## 1. Load Context (and only this)
Read, in order:
- The ticket
- The spec sections named in `spec_refs`
- `work/specs/frontend/00-frontend-architecture.md`
- `work/frontend/test-strategy.md`
- The `frontend-setup` skill sections for each layer the ticket touches
- `CONTEXT.md`
- Skim existing code for the modules involved and follow its patterns.

If the ticket is `changes-requested`, read the newest `work/frontend/reviews/FT-NNN-review-N.md` and treat its blockers and majors as the task list.

## 2. Build Test-First
For each row in the ticket's *Test plan*, in order:
1. **Red:** Write one test at its named seam. Run it and watch it fail for the right reason.
2. **Green:** Write the smallest code that passes it, in the correct layer per the architecture. Run the whole suite.
3. Move to the next row.

### Test Seams (Frontend)
| Seam | Tooling | Used For |
|---|---|---|
| **Component Unit** | Vitest + React Testing Library | Component rendering, props, user interactions, accessibility |
| **Hook Unit** | Vitest | Custom hook logic, state transitions, API integration |
| **Integration** | Vitest + MSW | Component + API mock, form submissions, data flows |
| **E2E** | Playwright | Critical user flows, auth, routing, responsive breakpoints |

### Rules of the Loop
- Expected values come from the spec or mock data, never from calling the code under test again.
- Test through public interfaces (component props, hook returns, API contracts) rather than private helpers.
- Components stay thin: each component declares its data needs via hooks. Business logic lives in hooks or utilities.
- Use the naming conventions from the architecture spec.
- Add only what the ticket's acceptance criteria require. Spot an adjacent need? Write it under *Notes* as a proposed follow-up ticket and continue.
- **Responsive tests**: Test at desktop (≥1024px), tablet (768px), mobile (375px) viewports where layout changes.
- **Accessibility tests**: Test keyboard navigation, ARIA attributes, focus management.

## 3. Deviations
When the spec turns out wrong or incomplete, stop, state the conflict, and ask the user (or, for a small clarification, record your assumption in the ticket's *Implementation log* and `tracker.py log`). The spec stays the source of truth; propose a spec edit rather than silently diverging.

## 4. Implementation Standards (from frontend-setup & tech spec)

### Component Patterns
- **Server Components**: Use TanStack Query hooks for data fetching
- **Client Components**: Mark with `'use client'` when using Zustand, browser APIs, or interactivity
- **Compound Components**: For complex UI (Table, Select, DatePicker) use shadcn/ui patterns
- **Form Components**: React Hook Form + Zod resolver, controlled/uncontrolled appropriately

### State Management
- **TanStack Query**: All server state. Keys: `['domain', 'action', params]`. Stale time: 5 min. Cache time: 10 min.
- **Zustand**: Auth store, UI preferences (sidebar open, theme), form drafts, optimistic updates
- **URL State**: TanStack Router search params for filters, pagination, sorting

### API Integration
- Use `api.ts` axios instance with interceptors
- Mutations: Optimistic update → API call → Invalidate queries → Rollback on error
- SSE: `useEventSource` hook feeds into queryClient.invalidateQueries()

### Styling
- Tailwind CSS variables for theming (light/dark)
- `cn()` utility for class merging
- Semantic color tokens for appointment states
- 8-point spacing rhythm (`space-y-4`, `gap-4`, `p-4`)
- Responsive: `md:` for tablet, `lg:` for desktop

### Accessibility
- Semantic HTML (`<table>`, `<button>`, `<nav>`, `<main>`)
- Focus visible: `focus-visible:ring-2 focus-visible:ring-ring`
- ARIA labels on icon buttons, status badges
- Live regions for dynamic updates (SSE notifications)
- Color contrast: WCAG AA minimum

## 5. Finish
1. Walk the ticket's acceptance criteria and tick each with the test that proves it.
2. Run the **quality gates**:
   ```bash
   npm run lint        # biome check
   npm run format      # biome format --check
   npm run typecheck   # tsc --noEmit
   npm run test        # vitest run
   npm run test:e2e    # playwright test (for tickets marked with E2E)
   ```
   All green.
3. Fill the ticket's *Implementation log*: what was built, files touched, decisions, deviations, commands run.
4. Commit: `FT-NNN: <title>` (conventional-commit prefix welcome). Record the sha in the log.
5. `tracker.py set FT-NNN in-review`.

## 6. Hand-off
Tell the user: ticket built → **clear context** → run `frontend-ticket-review` for FT-NNN in a fresh session, because a reviewer who did not write the code reads it more honestly.