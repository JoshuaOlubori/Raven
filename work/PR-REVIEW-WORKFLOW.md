# Local pull request review, validation, and merge workflow

Use this runbook when a GitHub pull request is ready for local validation. For the current T-010/T-011 fixes, the PR is https://github.com/JoshuaOlubori/Raven/pull/1 and the branch is `fix/t010-t011-review-gaps`.

## Goal

Review the PR on GitHub, validate and troubleshoot it on the local development machine, push any justified fixes to the same PR branch, merge only when safe, and update the local checkout. Follow the repository's `sdd-ticket-review` and `sdd-implement` skills throughout. Do not claim tests passed unless the commands actually pass.

## Step-by-step instructions for the local coding agent

1. **Inspect local state first.** From the repository root run `git status --short --branch` and `git branch --show-current`. If there are uncommitted changes, identify them and preserve them; do not stash, discard, reset, or overwrite user work without permission. Confirm the repo root and read `.agents/skills/sdd-ticket-review`, `.agents/skills/sdd-implement`, `work/TRACKER.md`, both T-010/T-011 tickets, and their latest review notes.
2. **Open the PR on GitHub.** Visit the PR URL above. Read the description, changed-files diff, conversation, review comments, merge-conflict indicator, and CI/check results. Do not assume the PR is mergeable just because it is open.
3. **Fetch the PR branch locally.** If the working tree is clean, run:
   ```bash
   git fetch origin
   gh pr checkout 1
   git status --short --branch
   ```
   If `gh` is not installed or authenticated, use `git fetch origin pull/1/head:fix/t010-t011-review-gaps` and check out that branch. Never force-push.
4. **Review the actual diff.** Run `gh pr diff 1` (or inspect `git diff origin/master...HEAD`). Verify each change against the ticket acceptance criteria, specs, skills, and review findings. Pay particular attention to cancellation validation/audit behavior, UTC timestamp consistency, SSE heartbeat formatting, concurrent fan-out, subscriber cleanup, and broadcaster thread safety. Look for regressions and unrelated changes.
5. **Run quality gates from `backend/`.** Use the project's documented commands and environment. At minimum run:
   ```bash
   uv run ruff check .
   uv run ruff format --check .
   uv run mypy src
   uv run pytest -q
   ```
   If a command differs from the repo's actual configuration, inspect `pyproject.toml` and use the documented equivalent. Do not describe skipped or environment-blocked tests as passing. Record the exact command and result.
6. **Troubleshoot failures.** Reproduce failures, trace the root cause, and make the smallest spec-consistent fix. Read the relevant skill before implementing. Add or update regression tests for bugs; do not weaken assertions, skip failing tests, or change expected behavior merely to get a green run. Re-run the failing test first, then all quality gates.
7. **Commit and push fixes to the PR branch.** Inspect `git diff` and `git diff --check`; ensure no secrets, local configuration, generated artifacts, or unrelated user changes are included. Commit only the intended files with a descriptive message, then push the current PR branch with `git push origin HEAD`. Do not amend other people's commits or force-push. Confirm the new commit appears in PR #1.
8. **Re-check GitHub.** Refresh the PR. Review all new CI checks and review comments. Confirm there are no unresolved requested changes or merge conflicts. If the branch conflicts with `master`, inspect the conflicting changes and resolve them carefully on the PR branch; do not blindly take either side. Re-run relevant tests after conflict resolution and push the resolution.
9. **Merge only when safe.** Merge only if all required checks pass, the diff is reviewed, the PR is mergeable, and no required approval is outstanding. If repository rules require a human approval or the state is ambiguous, stop and report what is needed rather than bypassing protections. Otherwise use the repository's preferred merge method; for this PR, squash merge is acceptable:
   ```bash
   gh pr checks 1
   gh pr view 1
   gh pr merge 1 --squash --delete-branch
   ```
   Do not run the merge command until the preceding conditions are verified. If checks fail, conflicts remain, or merge is blocked, do not merge; report the blocker and next action.
10. **Sync local default branch and verify.** After GitHub confirms the PR is merged, run `git switch master` and `git pull --ff-only origin master`, but only if switching will not overwrite uncommitted work. Run `git status --short --branch` and confirm the checkout is clean or clearly report any pre-existing changes. Do not delete local branches containing unmerged work.
11. **Report outcome and tracker state.** Summarize the files changed, root causes found, exact test results, commit(s), PR URL, and whether it was merged. Update ticket statuses/review history in `work/TRACKER.md` and the T-010/T-011 ticket files only when the acceptance criteria and repository workflow justify the change. Do not mark tickets done solely because a PR was opened or merged; use the project's defined completion criteria.

## Stop conditions

Stop without merging and explain the blocker if:
- local user changes may be overwritten;
- credentials or permissions are missing;
- tests cannot be run and no accepted CI result is available;
- required checks fail, the branch is not mergeable, or review is unresolved;
- resolving a failure requires a product/spec decision;
- GitHub rules require a human approval.

## Current PR-specific focus

- PR: https://github.com/JoshuaOlubori/Raven/pull/1
- Head branch: `fix/t010-t011-review-gaps`
- Base branch: `master`
- Files changed by the initial fix: `backend/tests/unit/test_schemas.py`, `backend/tests/api/test_live_sse.py`, `backend/src/app/services/event_broadcaster.py`
- Important: the PR was reported as `mergeable: false` when opened, and local tests have not yet been executed. Investigate mergeability and validate the changes before considering a merge.
