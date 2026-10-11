---
name: frontend-ticket-review
description: Review the code for one completed frontend ticket along three axes — Spec (does it do what the ticket, tech spec and Stitch design ask), Standards (frontend-setup checklist plus code-smell baseline) and Tests (are the tests meaningful) — write a review report to work/frontend/reviews/, and move the ticket to done or changes-requested. Use right after frontend-implement finishes a ticket, or when the user says "review FT-00X", "check this frontend ticket", "is this frontend ready to merge". Best run in a fresh context.
---

# Frontend Ticket Review

Independent review of a completed frontend ticket. The reviewer did not write the code.

## Inputs
- Ticket file: `work/frontend/tickets/FT-NNN-<slug>.md`
- Spec refs from ticket's `spec_refs`
- Implementation log in the ticket
- Diff: `git diff <base>..HEAD` (or the commit series for this ticket)

## Review Axes

### 1. Spec Compliance
- **Acceptance Criteria**: Every AC has a passing test that proves it.
- **Stitch Design Fidelity**: Visual design matches Stitch screens (colors, spacing, typography, components). Responsive behavior matches spec breakpoints.
- **Role-Based Visibility**: Correct components/actions shown/hidden per role (Admin, Receptionist, Dentist).
- **API Contract**: All API calls match backend spec (endpoints, request/response types, error handling).
- **State Transitions**: Appointment status transitions match FSM from backend spec.
- **Missing Features**: No implied features absent from backend API (no patient portal, no billing, no clinical notes, no drag-and-drop rescheduling unless specified).

### 2. Standards Compliance
- **Architecture**: Follows `00-frontend-architecture.md` patterns (routing, state, data fetching).
- **Component Structure**: Thin components, logic in hooks, proper separation of concerns.
- **TypeScript**: Strict mode, no `any`, proper generic types for hooks/components.
- **Forms**: React Hook Form + Zod, proper validation, error display.
- **Styling**: Tailwind CSS variables, semantic tokens, `cn()` utility, responsive classes.
- **Accessibility**: Semantic HTML, focus management, ARIA, color contrast, keyboard navigation.
- **Performance**: No unnecessary re-renders, proper query keys, cache invalidation.
- **Code Quality**: Biome passes, no console.log, no commented code, meaningful names.

### 3. Test Quality
- **Coverage**: All ACs covered, edge cases tested (empty, error, loading, permission states).
- **Seams**: Tests at the right level (component, hook, integration, E2E).
- **Assertions**: Expected values from spec/mock data, not from implementation.
- **Responsive**: Tests at multiple viewports where layout changes.
- **Accessibility**: Automated a11y checks (axe) in component tests.
- **MSW**: API mocks match backend contract, not implementation details.

## Review Process

1. **Read the ticket** — Understand what was asked (ACs, test plan, spec refs).
2. **Read the spec refs** — Know the expected behaviour and design.
3. **Read the diff** — See what was actually built.
4. **Run the tests** — `npm run test` and `npm run test:e2e` (if applicable). All must pass.
5. **Run quality gates** — `npm run lint`, `npm run format`, `npm run typecheck`. All must pass.
6. **Check the build** — `npm run build` succeeds.
7. **Write the review report** to `work/frontend/reviews/FT-NNN-review-M.md`.

## Review Report Template

```markdown
---
ticket: FT-NNN
review: 1
status: approved | changes-requested
reviewer: <model-id>
date: YYYY-MM-DD
---

# Review: FT-NNN <title>

## Summary
<2-3 sentences: what was built, overall assessment>

## Spec Compliance
| AC | Status | Evidence |
|---|---|---|
| AC1 | ✅/❌ | Test name / observation |
| AC2 | ✅/❌ | ... |

### Stitch Design Fidelity
- [ ] Colors match design system tokens
- [ ] Spacing follows 8-point rhythm
- [ ] Typography matches spec (Inter, hierarchy)
- [ ] Corner radius consistent (--radius)
- [ ] Shadows/surfaces match
- [ ] Responsive breakpoints work correctly
- [ ] Role-based visibility correct

### API Contract
- [ ] All endpoints match backend spec
- [ ] Request/response types correct
- [ ] Error handling per spec (401, 403, 404, 409, 422)
- [ ] SSE integration works (if applicable)

### Missing/Extra Features
- No patient portal, billing, insurance, clinical notes implied
- No drag-and-drop rescheduling unless specified
- No global audit log screen
- No notification settings screen

## Standards Compliance
| Check | Status | Notes |
|---|---|---|
| Architecture patterns followed | ✅/❌ | |
| Thin components, logic in hooks | ✅/❌ | |
| TypeScript strict, no `any` | ✅/❌ | |
| React Hook Form + Zod | ✅/❌ | |
| Tailwind CSS variables, semantic tokens | ✅/❌ | |
| Accessibility (semantic HTML, focus, ARIA, contrast) | ✅/❌ | |
| Performance (memo, query keys, invalidation) | ✅/❌ | |
| Biome lint/format clean | ✅/❌ | |
| TypeScript compiles | ✅/❌ | |
| Build succeeds | ✅/❌ | |

## Test Quality
| Check | Status | Notes |
|---|---|---|
| All ACs have tests | ✅/❌ | |
| Tests at correct seams | ✅/❌ | |
| Expected values from spec | ✅/❌ | |
| Responsive viewport tests | ✅/❌ | |
| Accessibility tests (axe) | ✅/❌ | |
| MSW mocks match backend contract | ✅/❌ | |
| No flaky tests | ✅/❌ | |

## Findings

### Blockers (must fix before merge)
- **B1**: <description> — <file:line> — <why it blocks>

### Majors (should fix)
- **M1**: <description> — <file:line> — <suggestion>

### Minors (nice to fix)
- **m1**: <description> — <file:line> — <suggestion>

### Nits (style/preference)
- **n1**: <description> — <file:line> — <suggestion>

## Verdict
- **Approved**: No blockers, majors ≤ 2, all gates green → `tracker.py set FT-NNN done`
- **Changes Requested**: Any blockers or majors > 2 → `tracker.py set FT-NNN changes-requested`

## Next Steps
<If changes-requested: specific list of what to fix. If approved: note any follow-up tickets created.>
```

## Hand-off

Tell the user: review complete → ticket moved to `done` or `changes-requested` → **clear context** → next ticket via `frontend-resume`.