# Review T-013 round 3 — changes requested
Gates: ruff ✓ · format ✓ · mypy ✓ · pytest ✓ (161 passed, 2 skipped)

## Spec — findings

- **[major]** `backend/alembic/versions/65b4134a2687_initial_migration_all_models.py:44-46,70-72` creates named unique constraints for `staff.email` and `dental_services.name` in addition to unique indexes, while the models declare only `unique=True, index=True` (`backend/src/app/models/staff.py:26`, `backend/src/app/models/service.py:25`). The migration also persists defaults for timestamps and status fields that are client-side model defaults, not metadata server defaults (for example migration lines 30-41 and 186; `backend/src/app/models/base.py:31-32`). This leaves the migrated schema different from the application metadata and can make Alembic autogenerate/check report changes immediately after upgrade. Align the revision with metadata or deliberately update the models, and verify a clean metadata comparison. Acceptance criterion: “Alembic can load application metadata and generate/check revisions without import errors.”
- **[major]** `backend/tests/integration/test_alembic_migrations.py:36-58,115-154,330-350` checks only a hand-picked subset of indexes and unique constraints, and `test_alembic_can_load_metadata` imports `Base` and checks table names without invoking Alembic revision generation or `check`. As a result, missing model indexes and migration/metadata drift can pass the suite. Assert the complete expected schema or compare the migrated schema to model metadata, and exercise Alembic's autogenerate/check path. Acceptance criteria: “Given an empty supported database, When all migrations are upgraded, Then every current model table and index exists” and “Alembic can load application metadata and generate/check revisions without import errors.”

## Standards — findings

- The migration duplicates uniqueness enforcement for two fields, adding redundant database structures and diverging from ORM metadata (Mysterious/duplicated schema representation; architecture spec §4 migrations).

## Tests — findings

- Upgrade/downgrade and lifespan tests provide meaningful coverage, PostgreSQL offline SQL verifies boolean literals, and the metadata drift/coverage gaps above remain.
- Temporary SQLite database files created by `migration_test_db_url` are not removed after use (`backend/tests/integration/test_alembic_migrations.py:77-86`); clean them up as minor test hygiene.

## Summary

0 blockers, 2 majors, 0 minors, 1 nit. Worst issue: the initial migration does not match the model metadata, so a successful upgrade does not establish a stable Alembic autogenerate/check baseline.
