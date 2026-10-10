# Journal

Append-only history. Newest entries at the bottom.

| When | Phase | Ticket | Entry |
|---|---|---|---|
| 2026-10-03 17:39 | setup | - | tracker initialised |
| 2026-10-03 17:40 | setup | - | repo set up for SDD |
| 2026-10-03 17:56 | prd | - | PRD written (17 requirements) |
| 2026-10-03 18:05 | spec | - | tech specs approved: 00-architecture, 01-auth-staff, 02-patients, 03-services, 04-schedules, 05-appointments, 06-notifications-events |
| 2026-10-03 18:09 | tickets | - | 12 tickets created, coverage complete |
| 2026-10-03 20:40 | - | T-001 | status -> in-progress |
| 2026-10-03 21:38 | - | T-001 | status -> in-review |
| 2026-10-03 21:38 | build | T-001 | T-001 built: skeleton + test infra, 3 tests green, all 4 quality gates pass (commit ff7c1d2) -> in-review |
| 2026-10-03 21:55 | - | T-001 | review round 1: approve, 0B/0M/1m/4n |
| 2026-10-03 21:55 | - | T-001 | status -> done |
| 2026-10-05 09:16 | - | T-002 | status -> in-progress |
| 2026-10-05 09:45 | build | T-002 | T-002 built: Staff model, AuthService (Argon2id + HS256 JWT), auth router (/token, /me), 5 tests green, all 4 quality gates pass -> in-review |
| 2026-10-05 09:59 | - | T-002 | status -> in-review |
| 2026-10-05 09:59 | build | - | T-002 built and committed (39caac5) |
| 2026-10-05 10:22 | - | T-002 | status -> changes-requested |
| 2026-10-05 10:23 | - | T-002 | review round 1: changes-requested, 0B/1M/2m/3n |
| 2026-10-05 10:37 | - | T-002 | status -> in-progress |
| 2026-10-05 10:47 | - | T-002 | status -> in-review |
| 2026-10-05 10:47 | build | - | T-002 changes-requested fixes committed (af3d419): AC5 tests, AC2 non-existent email test, 500 handler sanitized |
| 2026-10-05 11:07 | - | T-002 | status -> done |
| 2026-10-05 11:07 | - | T-002 | review round 2: approve, 0B/0M/2m/4n |
| 2026-10-05 11:19 | - | T-003 | status -> in-progress |
| 2026-10-05 11:53 | - | T-003 | status -> in-review |
| 2026-10-05 12:15 | - | T-003 | status -> changes-requested |
| 2026-10-05 12:16 | - | T-003 | review round 1: changes-requested, 0B/1M/3m/4n |
| 2026-10-05 12:25 | - | T-003 | status -> in-progress |
| 2026-10-05 12:45 | build | T-003 | T-003 changes-requested fixes committed (c6e7dbe): additional 5 tests; quality gates green |
| 2026-10-05 12:52 | - | T-003 | status -> done |
| 2026-10-05 12:52 | - | T-003 | review round 2: approve, 0B/0M/1m/3n |
| 2026-10-05 13:46 | - | T-004 | status -> in-progress |
| 2026-10-05 14:23 | - | T-004 | status -> in-review |
| 2026-10-05 15:10 | review | T-004 | T-004 round 1: changes-requested, missing 404 tests and other test gaps |
| 2026-10-05 15:30 | build | T-004 | T-004 fixes committed (25ba105): added missing API/schema tests; gates green |
| 2026-10-05 15:35 | review | T-004 | T-004 round 2: approve, 0B/0M/0m/1n |
| 2026-10-05 15:35 | - | T-004 | status -> done |
| 2026-10-05 16:14 | - | T-005 | status -> in-progress |
| 2026-10-05 16:45 | - | T-005 | status -> in-review |
| 2026-10-05 16:45 | build | - | T-005 built and committed (0204012); API tests and gates green |
| 2026-10-05 20:41 | - | T-005 | review round 1: changes-requested, 1B/4M/0m/1n |
| 2026-10-05 22:05 | build | - | T-005 review fixes: 7 API tests and validation coverage; gates green |
| 2026-10-06 10:40 | - | T-005 | review round 2: approve, 0B/0M/0m/0n; status -> done |
| 2026-10-06 12:38 | - | T-006 | status -> in-progress |
| 2026-10-06 12:55 | build | T-006 | T-006 built: schedules, service and tests; gates green |
| 2026-10-06 14:30 | - | T-006 | review round 1: approve, 0B/0M/1m/0n; status -> done |
| 2026-10-06 22:56 | - | T-007 | status -> in-review |
| 2026-10-06 23:10 | review | T-007 | review round 2: changes-requested, 2B/2M/4m/2n |
| 2026-10-07 04:52 | build | - | T-007 fixes: N+1 roundtrip optimization, documented SLOT_STEP rationale |
| 2026-10-07 07:52 | review | T-007 | review round 4: changes-requested, 1B/0M/1m/0n |
| 2026-10-07 08:03 | - | T-007 | status -> done |
| 2026-10-07 08:05 | - | T-008 | status -> in-progress |
| 2026-10-07 10:47 | implement | - | T-008 booking implementation; tests and quality gates green |
| 2026-10-07 11:16 | review | T-008 | review round 1: changes-requested, 1B/1M/3m/3n |
| 2026-10-07 11:21 | review | T-008 | review round 2: changes-requested, blocker remains |
| 2026-10-07 12:14 | - | T-009 | status -> in-progress |
| 2026-10-07 12:55 | review | T-009 | review round 1: approve, 0B/0M/1m/1n; status -> done |
| 2026-10-07 14:10 | - | T-010 | status -> in-review |
| 2026-10-08 08:43 | review | T-010 | review round 1: changes-requested, B1/M2/m4/n1 |
| 2026-10-08 08:57 | build | T-010 | Fixed actor binding and added tests; gates green |
| 2026-10-08 12:01 | review | T-010 | review round 2: changes-requested, B1/M2/m5 |
| 2026-10-08 13:50 | review | T-010 | review round 3 approved; status -> done |
| 2026-10-09 08:30 | - | T-011 | status -> in-review |
| 2026-10-09 08:49 | review | T-011 | review round 1: changes-requested, B2/M4/m3/n1 |
| 2026-10-09 10:30 | review | T-011 | review round 2: changes-requested, B2/M4/m1/n0; owner then chose required multi-worker production support via Redis Pub/Sub |
| 2026-10-09 15:11 | review | T-011 | review round 3: changes-requested, B0/M2/m0/n0. Report: work/reviews/T-011-review-3.md. Redis cross-instance integration test is absent at documented path; quality gates and Redis integration test remain unverified. Ticket status -> changes-requested. |
| 2026-10-09 16:43 | implement | T-011 | Added Redis cross-instance integration test at backend/tests/integration/test_redis_event_broker.py; test and quality gates not run in remote GitHub editor. Ticket remains in-progress pending owner-run validation. |

| 2026-10-09 22:38 | review | T-011 | Round 4 approved (B0/M0/m0/n0); owner confirmed Redis integration 1 passed, Ruff/format/mypy clean, full pytest 141 passed; status -> done. See work/reviews/T-011-review-4.md. |
| 2026-10-10 04:58 | - | T-012 | status -> in-progress |
| 2026-10-10 05:28 | - | T-012 | status -> in-review |
| 2026-10-10 05:32 | - | T-010 | status -> done |
| 2026-10-10 05:34 | - | T-012 | status -> changes-requested |
| 2026-10-10 05:34 | - | T-012 | review round 1: changes-requested, 1 blocker/2 majors/0 minors/0 nits |
| 2026-10-10 06:02 | - | T-012 | status -> changes-requested |
| 2026-10-10 06:03 | - | T-012 | review round 2: changes-requested, 2 blockers/4 majors/1 minor/0 nits; see work/reviews/T-012-review-2.md |
| 2026-10-10 06:05 | - | T-012 | status -> in-progress |
| 2026-10-10 06:14 | - | T-012 | status -> in-review |
| 2026-10-10 06:14 | - | T-012 | T-012 implementation committed as 89530af after removing .codex from reachable ticket history; ready for review. |
