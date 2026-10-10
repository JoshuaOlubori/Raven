"""Application configuration management.

Centralized settings loaded from environment variables / ``.env`` via
``pydantic-settings``.  Validated once at import time and exposed both as a
module-level singleton and through the ``get_settings`` callable for
dependency-injection overrides.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

# Default insecure JWT secret used only for local development.
# Production must explicitly configure a strong secret.
_DEV_DEFAULT_JWT_SECRET = "dev-insecure-secret-change-in-production"
_MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """Runtime configuration for the Dental Clinic backend."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        extra="ignore",
    )

    database_url: str = Field(
        default="sqlite+aiosqlite:///./app.db",
        validation_alias="DATABASE_URL",
    )
    clinic_timezone: str = Field(
        default="America/New_York",
        validation_alias="CLINIC_TIMEZONE",
    )
    jwt_secret_key: str = Field(
        default=_DEV_DEFAULT_JWT_SECRET,
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

    @model_validator(mode="after")
    def _validate_jwt_secret_for_env(self) -> Settings:
        """Validate JWT secret strength for non-development environments.

        Production and other non-development environments require an explicit,
        strong JWT secret. The development default is rejected.
        """
        is_dev = self.app_env.lower() == "development"

        if not is_dev:
            # Non-development: secret must be explicitly set (not the default)
            if self.jwt_secret_key == _DEV_DEFAULT_JWT_SECRET:
                raise ValueError(
                    "JWT_SECRET_KEY must be explicitly configured for non-development "
                    "environments; the development default is not permitted."
                )

            # Non-development: secret must meet minimum strength
            if len(self.jwt_secret_key) < _MIN_JWT_SECRET_LENGTH:
                raise ValueError(
                    f"JWT_SECRET_KEY must be at least {_MIN_JWT_SECRET_LENGTH} "
                    f"characters in non-development environments."
                )

        return self


def get_settings() -> Settings:
    """Return application settings (singleton-ish, cheap to construct)."""
    return Settings()
