"""Application configuration management.

Centralized settings loaded from environment variables / ``.env`` via
``pydantic-settings``.  Validated once at import time and exposed both as a
module-level singleton and through the ``get_settings`` callable for
dependency-injection overrides.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Dental Clinic backend."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./app.db",
        validation_alias="DATABASE_URL",
    )
    clinic_timezone: str = Field(
        default="America/New_York",
        validation_alias="CLINIC_TIMEZONE",
    )
    jwt_secret_key: str = Field(
        default="dev-insecure-secret-change-in-production",
        validation_alias="JWT_SECRET_KEY",
    )
    app_env: str = Field(
        default="development",
        validation_alias="APP_ENV",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
    )
    enable_in_process_reminder_worker: bool = Field(
        default=True,
        validation_alias="ENABLE_IN_PROCESS_REMINDER_WORKER",
    )


def get_settings() -> Settings:
    """Return application settings (singleton-ish, cheap to construct)."""
    return Settings()
