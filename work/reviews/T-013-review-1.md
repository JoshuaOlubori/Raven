# Review T-013 round 1 — changes requested
Gates: ruff ✓ · format ✗ (65 files formatted; invalid UTF-8 in pre-existing work/TRACKER.md) · mypy ✓ · pytest ✓ (160 passed, 2 skipped)

## Spec — findings

- **[blocker]** `backend/alembic.ini` is required by the migration test fixture (`backend/tests/integration/test_alembic_migrations.py:57`) and is described in the implementation log, but it is untracked and absent from commit `b01f8a7`. A clean checkout cannot run `alembic upgrade head` or the committed migration tests. Add the config file to the ticket commit. Acceptance criterion: “Given an empty supported database, When all migrations are upgraded, Then every current model table and index exists.”
- **[blocker]** The initial migration uses `server_default=sa.text("1")` for PostgreSQL boolean columns (`backend/alembic/versions/65b4134a2687_initial_migration_all_models.py:31`, and the corresponding `dental_services`/`patients` columns). PostgreSQL does not accept integer `1` as a boolean default, so the initial revision cannot be applied on the supported production database. Use a PostgreSQL-compatible boolean literal (and verify cross-dialect behavior). Architecture spec §7: “Database: PostgreSQL with SQLAlchemy 2.0 ... and Alembic migrations.”
- **[major]** The test named `test_lifespan_does_not_create_production_schema` does not invoke the lifespan or assert a schema operation; it creates and disposes an unrelated in-memory engine (`backend/tests/integration/test_alembic_migrations.py:262-294`). This leaves acceptance criterion “Given a production app startup, When the lifespan initializes, Then it does not create or mutate the schema outside Alembic” without a regression test. Exercise startup with `create_all`/`init_db` observed or otherwise assert the production startup path.

## Standards — findings

- No additional FastAPI architecture or Fowler-baseline violations found in the reviewed commit.

## Tests — findings

- The SQLite upgrade/downgrade tests meaningfully check tables, indexes, constraints, and final revision.
- The lifespan test is a placeholder and does not test behavior (major finding above).
- No PostgreSQL migration test covers the supported production dialect; the boolean default incompatibility is not caught by the SQLite suite.

## Summary

2 blockers, 1 major, 0 minors, 0 nits. Worst issue: the initial migration cannot be applied to the supported PostgreSQL production database.
