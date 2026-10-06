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
| 2026-10-05 12:35 | - | T-003 | status -> in-review |
| 2026-10-05 12:35 | - | - | T-003 changes-requested fixes committed (c6e7dbe): 5 new tests (404 paths, DENTIST sub-case, 401 on staff endpoints, hardened list-filter assertion), 22 tests green, all 4 quality gates pass -> in-review |
| 2026-10-05 12:52 | - | T-003 | status -> done |
| 2026-10-05 12:52 | - | T-003 | review round 2: approve, 0B/0M/1m/3n � all round-1 findings addressed, gates green |
| 2026-10-05 13:46 | - | T-004 | status -> in-progress |
| 2026-10-05 14:23 | - | T-004 | status -> in-review |
| 2026-10-05 14:23 | build | - | T-004 built: ServiceDuration constrained type, DentalService model, ServiceCatalog domain service (create/get/list/update with name-uniqueness + existence guards), 4 endpoints (POST Admin, GET list + GET /{id} any staff, PATCH Admin), 5 tests (schema unit + 4 API). All 4 quality gates green (27 passed). -> in-review |
| 2026-10-05 15:10 | review | T-004 | T-004 round 1: changes-requested, 0B/1M/5m/0n — missing 404 tests for GET/{id} and PATCH (major); 5 minors (AC3 upper bound, AC2 edit/DENTIST sub-cases, GET/{id} 200, PATCH 409) |
| 2026-10-05 15:10 | - | T-004 | status -> in-progress |
| 2026-10-05 15:30 | build | T-004 | T-004 changes-requested fixes committed (25ba105): 6 new tests (GET/{id} 404, PATCH 404, GET/{id} 200, PATCH 403, DENTIST 403, PATCH 409) + extended schema unit test (AC3 upper bound) + dentist_staff fixture. No implementation changes. All 4 quality gates green (33 passed). -> in-review |
| 2026-10-05 15:35 | review | T-004 | T-004 round 2: approve, 0B/0M/0m/1n — all round-1 findings resolved. PATCH 422 nit optional. |
| 2026-10-05 15:35 | - | T-004 | status -> done |
| 2026-10-05 14:44 | - | T-004 | status -> changes-requested |
| 2026-10-05 14:44 | - | T-004 | review round 1: changes-requested, 1B/5m/0n � missing 404 tests for GET/{id} and PATCH (major); 5 minors (AC3 upper bound, AC2 edit/DENTIST sub-cases, GET/{id} 200, PATCH 409) |
| 2026-10-05 15:02 | - | T-004 | status -> in-progress |
| 2026-10-05 15:10 | - | T-004 | status -> in-review |
| 2026-10-05 16:14 | - | T-005 | status -> in-progress |
| 2026-10-05 16:45 | - | T-005 | status -> in-review |
| 2026-10-05 16:45 | build | - | T-005 built: Patient model, schemas (PhoneStr, PatientCreate/Update/Read with computed fullName, PatientPage), repository (search+pagination), PatientService, 5 RBAC-guarded endpoints. 7 tests (6 API + 1 schema unit), 40 total, all 4 quality gates green. Committed as 0204012. |
| 2026-10-05 20:41 | - | T-005 | review round 1: changes-requested, 1B/4M/0m/1n |
| 2026-10-05 20:42 | - | T-005 | status -> changes-requested |
| 2026-10-05 21:50 | - | T-005 | status -> in-review |
| 2026-10-05 22:05 | - | T-005 | Addressed T-005-review-1 findings: added 7 tests (404 failure paths for GET/PATCH/DELETE non-existent patient, DENTIST 403 on write endpoints, GET/PATCH 200 happy paths, PATCH 422 future DOB) and documented get_current_user guard pattern in Spec 02 �4. All quality gates green (ruff, format, mypy, 47 tests). |
| 2026-10-06 10:40 | - | T-005 | status -> done |
| 2026-10-06 10:40 | - | T-005 | review round 2: approve, 0B/0M/0m/0n |
| 2026-10-06 10:49 | - | T-004 | status -> done |
| 2026-10-06 10:49 | - | T-004 | review round 2: approve, 0B/0M/0m/1n (previously approved, backfilling tracker) |
| 2026-10-06 12:38 | - | T-006 | status -> in-progress |
| 2026-10-06 12:55 | build | T-006 | T-006 built: WorkingShift/TimeOffBlock models, schedule service (overlap validation, ABAC), 6 endpoints, 14 tests (12 API + 2 schema). All 4 quality gates green (61 tests). -> in-review |
| 2026-10-06 12:55 | - | T-006 | status -> in-review |
| 2026-10-06 14:30 | - | T-006 | review round 1: approve, 0B/0M/1m/0n |
| 2026-10-06 14:30 | - | T-006 | status -> done |
| 2026-10-06 22:56 | - | T-007 | status -> in-review |
| 2026-10-06 23:09 | - | T-006 | status -> done |
| 2026-10-06 23:09 | - | T-007 | status -> changes-requested |
| 2026-10-06 23:10 | - | T-006 | review round 2: approve, 0B/0M/0m/0n |
| 2026-10-06 23:10 | - | T-007 | review round 2: changes requested, 2B/2M/4m/2n |
