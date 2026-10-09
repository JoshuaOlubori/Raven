# T-011 local implementation handoff

Use this runbook from the local development machine to finish the in-progress `sdd-implement` workflow for T-011. The remote edits are intentionally a draft; do not merge until every gate passes.

- Draft PR: https://github.com/JoshuaOlubori/Raven/pull/2
- Branch: `implement/T-011-redis-multiworker`
- Decision: multi-worker production support using Redis Pub/Sub (ADR 0003).

## Local agent instructions

1. Read `.agents/skills/sdd-implement/SKILL.md`, `.agents/skills/fastapi-production-architecture/SKILL.md`, `work/tickets/T-011-live-appointment-sse-stream.md`, the latest T-011 review, Spec 06, Architecture §4–§6, and ADR 0003.
2. Preserve the local working tree. Run `git status --short --branch`, `git fetch origin`, then `gh pr checkout 2` only if doing so will not overwrite local work.
3. Regenerate the lockfile from the repository root using the installed uv version (`uv lock` or `uv lock --directory backend`, as appropriate). Verify `backend/uv.lock` includes the Redis package and is consistent with `backend/pyproject.toml`.
4. Inspect the full PR diff. In particular verify:
   - Redis startup/shutdown and listener reconnect behaviour.
   - Cross-worker pub/sub and what happens during broker outages.
   - Bounded queue overflow emits `appointment.resync_required` and terminates the stream.
   - SSE auth DB session closes before streaming starts.
   - Event callbacks run only after successful DB commit and are not run after rollback.
   - Tests cover booking, rescheduling, cancellation, status changes, heartbeat, fan-out, disconnect cleanup, slow-consumer resync, and auth-session cleanup.
5. Run all quality gates exactly as specified by `CLAUDE.md`:
   ```bash
   uv run --directory backend ruff check
   uv run --directory backend ruff format --check
   uv run --directory backend mypy src
   uv run --directory backend pytest -q
   ```
6. Start an isolated Redis instance and set `TEST_REDIS_URL`; run the cross-worker Redis integration test explicitly. Do not report it as passing if it was skipped.
7. Fix failures test-first, following `sdd-implement`. Do not weaken tests to make them green. Re-run the focused tests and all four gates after fixes.
8. Review `git diff --check`, confirm no secrets or unrelated changes, commit any local fixes with a T-011-prefixed message, and push to the existing branch with `git push origin HEAD`. Never force-push.
9. Update the ticket's implementation log with actual commands/results and commit SHA. Keep the ticket `in-progress` until the implementation is complete and all gates pass; then set it to `in-review`. Do not merge PR #2 from this runbook.
10. Report exact test counts, whether the Redis integration test ran, any unresolved issues, commits pushed, and the current PR status.

## Stop conditions

Stop and report the blocker if a design/spec conflict appears, Redis cannot be provisioned, the lockfile cannot be regenerated, any gate fails without a clear safe fix, or local user changes would be overwritten. Do not mark T-011 done or merge PR #2 while validation is incomplete.
