---
id: T-013
title: Add reversible Alembic migrations for production schema changes
status: in-progress
mode: AFK
blocked_by: -
spec_refs: specs/00-architecture.md#4-cross-cutting-design, reviews/final-review.md#f-001-production-schema-lifecycle-has-no-migrations
covers: Architecture §2-§4
updated: 2026-10-10
---

## Outcome
The backend can create and evolve production databases through versioned, reversible Alembic migrations.

## What to build
Add the async Alembic configuration, environment and initial revision for all current models. Update application startup so it does not use `Base.metadata.create_all()` against the production database. Keep test schema setup explicit and test-only.

## Acceptance criteria
- [ ] Given an empty supported database, When all migrations are upgraded, Then every current model table and index exists.
- [ ] Given the initial revision is applied, When it is downgraded and upgraded again, Then both operations succeed and the schema is restored.
- [ ] Given a production app startup, When the lifespan initializes, Then it does not create or mutate the schema outside Alembic.
- [ ] Alembic can load application metadata and generate/check revisions without import errors.

## Test plan
| # | Test name | Seam | Asserts | Expected value comes from |
|---|---|---|---|---|
| 1 | migration upgrade on empty database | Alembic + DB | expected tables and indexes exist | architecture spec and models |
| 2 | migration downgrade then upgrade | Alembic + DB | both commands succeed; revision is current | reversible migration requirement |
| 3 | lifespan does not create production schema | app startup + DB | startup does not call `create_all` | F-001 |

## Out of scope
Production deployment orchestration and automated backup/restore procedures.

## Notes for the implementer
Keep SQLite test setup isolated from production migration behavior. Use the async Alembic template and preserve current model metadata.

## Implementation log

- Created Alembic configuration (alembic.ini, env.py, script.py.mako) in backend/alembic/
- Generated initial migration (65b4134a2687) with all 7 domain tables: staff, patients, dental_services, working_shifts, time_off_blocks, appointments, appointment_audit_logs
- Migration includes all indexes, unique constraints, and foreign keys matching the SQLAlchemy models
- Modified app/main.py lifespan to NOT call init_db() / create_all() - production deployments must run 'alembic upgrade head' before starting
- Test setup (conftest.py) continues to call init_db() explicitly against test databases
- Added comprehensive integration tests in tests/integration/test_alembic_migrations.py:
  - test_migration_upgrade_on_empty_database: verifies all tables, indexes, and unique constraints created
  - test_migration_downgrade_then_upgrade: verifies reversible migration (downgrade to base, upgrade to head)
  - test_alembic_can_load_metadata: verifies models load correctly for autogenerate
  - test_lifespan_does_not_create_production_schema: documents expected behavior
- All quality gates pass: ruff check, ruff format, mypy, pytest (160 passed, 2 skipped)

Commands run:
- uv run alembic revision --autogenerate -m "Initial migration: all models" (then manually wrote operations)
- uv run alembic upgrade head
- uv run alembic downgrade base && uv run alembic upgrade head
- uv run pytest tests/integration/test_alembic_migrations.py -v
- uv run pytest -q
- uv run ruff check
- uv run ruff format --check
- uv run mypy src

## Review history
