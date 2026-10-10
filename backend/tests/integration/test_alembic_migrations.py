"""Alembic migration integration tests (T-013).

Tests verify:
1. Migration upgrade on empty database creates all expected tables and indexes
2. Migration downgrade then upgrade succeeds and restores schema
3. Application lifespan does not call create_all in production
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

# Expected tables from the models
EXPECTED_TABLES = {
    "staff",
    "patients",
    "dental_services",
    "working_shifts",
    "time_off_blocks",
    "appointments",
    "appointment_audit_logs",
    "alembic_version",
}

# Expected indexes (subset for verification)
EXPECTED_INDEXES = {
    "staff": {"ix_staff_email", "ix_staff_role"},
    "patients": {
        "ix_patients_last_first",
        "ix_patients_phone",
        "ix_patients_is_active",
    },
    "dental_services": {"ix_dental_services_name", "ix_dental_services_is_active"},
    "working_shifts": set(),  # unique constraint is separate from indexes
    "time_off_blocks": {"ix_time_off_blocks_dentist_start_end"},
    "appointments": {
        "ix_appointments_dentist_start_end_status",
        "ix_appointments_reminder_sent_at",
    },
    "appointment_audit_logs": {"ix_audit_logs_appointment_created"},
}

# Expected unique constraints
EXPECTED_UNIQUE_CONSTRAINTS = {
    "staff": {"uq_staff_email"},
    "dental_services": {"uq_dental_services_name"},
    "working_shifts": {"uq_dentist_day_start"},
}


@pytest.fixture(scope="session")
def alembic_config_path() -> Path:
    """Path to the alembic.ini configuration file."""
    return Path(__file__).parent.parent.parent / "alembic.ini"


@pytest.fixture(scope="session")
def alembic_script_location() -> Path:
    """Path to the alembic script directory."""
    return Path(__file__).parent.parent.parent / "alembic"


@pytest.fixture(scope="function")
def migration_test_db_url() -> str:
    """Create a temporary file-based SQLite database URL for migration testing.

    Uses a temporary file instead of :memory: so it persists across
    alembic subprocess calls.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    return f"sqlite+aiosqlite:///{db_path}"


@pytest.fixture(scope="function")
async def migration_test_engine(migration_test_db_url: str) -> AsyncEngine:
    """Create a fresh SQLite engine for migration testing."""
    engine = create_async_engine(
        migration_test_db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine
    await engine.dispose()


def run_alembic_command(
    command: list[str], cwd: Path, env: dict | None = None
) -> subprocess.CompletedProcess:
    """Run an alembic command and return the result."""
    cmd = [sys.executable, "-m", "alembic"] + command
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=merged_env)


def get_alembic_env(db_url: str) -> dict:
    """Get environment dict with DATABASE_URL set for alembic."""
    return {**os.environ, "DATABASE_URL": db_url}


class TestAlembicMigrations:
    """Test suite for Alembic migration operations."""

    @pytest.mark.asyncio
    async def test_migration_upgrade_on_empty_database(
        self, migration_test_db_url: str, alembic_config_path: Path
    ) -> None:
        """Test that upgrading all migrations on an empty database creates all
        tables and indexes.
        """
        # Run alembic upgrade head
        result = run_alembic_command(
            ["upgrade", "head"],
            cwd=alembic_config_path.parent,
            env=get_alembic_env(migration_test_db_url),
        )
        assert result.returncode == 0, f"Alembic upgrade failed: {result.stderr}"

        # Verify all expected tables exist using a synchronous engine for inspection
        from sqlalchemy import create_engine

        sync_engine = create_engine(migration_test_db_url.replace("+aiosqlite", ""))
        inspector = inspect(sync_engine)
        tables = set(inspector.get_table_names())
        sync_engine.dispose()

        missing_tables = EXPECTED_TABLES - tables
        assert not missing_tables, f"Missing tables: {missing_tables}"

        # Verify key indexes exist
        sync_engine = create_engine(migration_test_db_url.replace("+aiosqlite", ""))
        inspector = inspect(sync_engine)
        for table, expected_indexes in EXPECTED_INDEXES.items():
            if table not in tables:
                continue
            actual_indexes = {idx["name"] for idx in inspector.get_indexes(table)}
            missing_indexes = expected_indexes - actual_indexes
            assert not missing_indexes, f"Missing indexes on {table}: {missing_indexes}"

        # Verify unique constraints exist
        for table, expected_constraints in EXPECTED_UNIQUE_CONSTRAINTS.items():
            if table not in tables:
                continue
            actual_constraints = {
                c["name"] for c in inspector.get_unique_constraints(table)
            }
            missing_constraints = expected_constraints - actual_constraints
            assert not missing_constraints, (
                f"Missing unique constraints on {table}: {missing_constraints}"
            )
        sync_engine.dispose()

    @pytest.mark.asyncio
    async def test_migration_downgrade_then_upgrade(
        self, migration_test_db_url: str, alembic_config_path: Path
    ) -> None:
        """Test that downgrading and upgrading the initial revision succeeds."""
        # First upgrade to head
        result = run_alembic_command(
            ["upgrade", "head"],
            cwd=alembic_config_path.parent,
            env=get_alembic_env(migration_test_db_url),
        )
        assert result.returncode == 0, f"Alembic upgrade failed: {result.stderr}"

        # Get the current revision
        result = run_alembic_command(
            ["current"],
            cwd=alembic_config_path.parent,
            env=get_alembic_env(migration_test_db_url),
        )
        assert result.returncode == 0
        # Extract revision from output (format: "<revision> (head)")
        match = re.search(r"^([a-f0-9]+)\s+\(head\)", result.stdout.strip())
        assert match, f"Could not determine current revision from: {result.stdout}"
        head_revision = match.group(1)

        # Downgrade to base (before initial revision)
        result = run_alembic_command(
            ["downgrade", "base"],
            cwd=alembic_config_path.parent,
            env=get_alembic_env(migration_test_db_url),
        )
        assert result.returncode == 0, f"Alembic downgrade failed: {result.stderr}"

        # Verify tables are gone (except alembic_version)
        from sqlalchemy import create_engine

        sync_engine = create_engine(migration_test_db_url.replace("+aiosqlite", ""))
        inspector = inspect(sync_engine)
        tables_after_downgrade = set(inspector.get_table_names())
        sync_engine.dispose()
        # Only alembic_version should remain
        assert tables_after_downgrade <= {"alembic_version"}, (
            f"Tables remain after downgrade: {tables_after_downgrade}"
        )

        # Upgrade again
        result = run_alembic_command(
            ["upgrade", "head"],
            cwd=alembic_config_path.parent,
            env=get_alembic_env(migration_test_db_url),
        )
        assert result.returncode == 0, f"Alembic re-upgrade failed: {result.stderr}"

        # Verify all tables exist again
        sync_engine = create_engine(migration_test_db_url.replace("+aiosqlite", ""))
        inspector = inspect(sync_engine)
        tables_after_reupgrade = set(inspector.get_table_names())
        sync_engine.dispose()

        missing_tables = EXPECTED_TABLES - tables_after_reupgrade
        assert not missing_tables, f"Missing tables after re-upgrade: {missing_tables}"

        # Verify indexes and unique constraints after re-upgrade
        sync_engine = create_engine(migration_test_db_url.replace("+aiosqlite", ""))
        inspector = inspect(sync_engine)
        for table, expected_indexes in EXPECTED_INDEXES.items():
            if table not in tables_after_reupgrade:
                continue
            actual_indexes = {idx["name"] for idx in inspector.get_indexes(table)}
            missing_indexes = expected_indexes - actual_indexes
            assert not missing_indexes, (
                f"Missing indexes on {table} after re-upgrade: {missing_indexes}"
            )
        for table, expected_constraints in EXPECTED_UNIQUE_CONSTRAINTS.items():
            if table not in tables_after_reupgrade:
                continue
            actual_constraints = {
                c["name"] for c in inspector.get_unique_constraints(table)
            }
            missing_constraints = expected_constraints - actual_constraints
            assert not missing_constraints, (
                f"Missing unique constraints on {table} after "
                f"re-upgrade: {missing_constraints}"
            )
        sync_engine.dispose()

        # Verify revision is back at head
        result = run_alembic_command(
            ["current"],
            cwd=alembic_config_path.parent,
            env=get_alembic_env(migration_test_db_url),
        )
        assert result.returncode == 0
        match = re.search(r"^([a-f0-9]+)\s+\(head\)", result.stdout.strip())
        assert match, (
            f"Could not determine current revision after re-upgrade: {result.stdout}"
        )
        assert match.group(1) == head_revision, "Revision mismatch after re-upgrade"

    @pytest.mark.asyncio
    async def test_lifespan_does_not_create_production_schema(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Starting the real application lifespan never invokes create_all."""
        from app import main
        from app.config import Settings
        from app.models import Base

        class FakeBroadcaster:
            async def start(self, redis_url: str) -> None:
                pass

            async def stop(self) -> None:
                pass

        def fail_create_all(*args: object, **kwargs: object) -> None:
            raise AssertionError("application startup attempted to create schema")

        monkeypatch.setattr(main, "get_event_broadcaster", lambda: FakeBroadcaster())
        monkeypatch.setattr(
            main,
            "get_settings",
            lambda: Settings(ENABLE_IN_PROCESS_REMINDER_WORKER=False),
        )
        monkeypatch.setattr(Base.metadata, "create_all", fail_create_all)

        async with main.lifespan(main.app):
            pass

    def test_postgresql_migration_uses_boolean_defaults(
        self, alembic_config_path: Path
    ) -> None:
        """PostgreSQL offline migration SQL must use boolean literals."""
        result = run_alembic_command(
            ["upgrade", "head", "--sql"],
            cwd=alembic_config_path.parent,
            env=get_alembic_env("postgresql+asyncpg://user:pass@localhost/db"),
        )

        assert result.returncode == 0, result.stderr
        assert "DEFAULT true" in result.stdout
        assert "BOOLEAN DEFAULT 1" not in result.stdout


class TestAlembicConfig:
    """Test that Alembic configuration is valid."""

    def test_alembic_ini_exists(self, alembic_config_path: Path) -> None:
        """Verify alembic.ini exists."""
        assert alembic_config_path.exists(), "alembic.ini not found"

    def test_alembic_env_py_exists(self, alembic_script_location: Path) -> None:
        """Verify alembic/env.py exists."""
        assert (alembic_script_location / "env.py").exists(), "alembic/env.py not found"

    def test_alembic_script_mako_exists(self, alembic_script_location: Path) -> None:
        """Verify alembic/script.py.mako exists."""
        assert (alembic_script_location / "script.py.mako").exists(), (
            "alembic/script.py.mako not found"
        )

    def test_alembic_versions_dir_exists(self, alembic_script_location: Path) -> None:
        """Verify alembic/versions directory exists."""
        assert (alembic_script_location / "versions").exists(), (
            "alembic/versions directory not found"
        )

    def test_alembic_can_load_metadata(self, alembic_script_location: Path) -> None:
        """Verify alembic can load application metadata and generate revisions.

        This test ensures the alembic environment can import the application
        models without configuration errors. It does not require a database
        connection.
        """
        # Import the models directly to verify they load without error
        # This tests that the models can be imported and Base.metadata is populated
        import sys

        sys.path.insert(0, str(alembic_script_location.parents[1] / "src"))

        from app.models import Base

        # Verify all expected tables are registered in the metadata
        expected_tables = EXPECTED_TABLES - {"alembic_version"}
        for table_name in expected_tables:
            assert table_name in Base.metadata.tables, (
                f"Table {table_name} not registered in Base.metadata"
            )
