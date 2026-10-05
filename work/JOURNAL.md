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
| 2026-10-05 10:47 | build | T-002 | T-002 changes-requested fixes committed (af3d419): AC5 tests, AC2 non-existent email test, 500 handler sanitized |
| 2026-10-05 11:07 | - | T-002 | status -> done |
| 2026-10-05 11:07 | - | T-002 | review round 2: approve, 0B/0M/2m/4n |
| 2026-10-05 11:19 | - | T-003 | status -> in-progress |
| 2026-10-05 11:53 | - | T-003 | status -> in-review |
| 2026-10-05 12:15 | - | T-003 | status -> changes-requested |
| 2026-10-05 12:16 | - | T-003 | review round 1: changes-requested, 0B/1M/3m/4n |
| 2026-10-05 12:25 | - | T-003 | status -> in-progress |
| 2026-10-05 12:45 | build | T-003 | T-003 changes-requested fixes: 5 new tests (404 paths, DENTIST sub-case, 401 on staff endpoints, hardened list-filter assertion), 22 tests green, all 4 quality gates pass -> in-review |
