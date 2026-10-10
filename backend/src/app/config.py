"""Application configuration management.

Centralized settings loaded from environment variables / ``.env`` via
``pydantic-settings``.  Validated once at import time and exposed both as a
module-level singleton and through the ``get_settings`` callable for
dependency-injection overrides.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

# Default insecure JWT secret used only for local development.
# Production must explicitly configure a strong secret.
_DEV_DEFAULT_JWT_SECRET = "dev-insecure-secret-change-in-production"
_GENERATED_SECRET_LENGTH = 43  # unpadded URL-safe base64 of 32 random bytes
_URLSAFE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def _is_strong_secret(secret: str) -> bool:
    """Validate the documented random-key format and reject obvious patterns.

    Non-development keys must be generated with ``secrets.token_urlsafe(32)``.
    The string format cannot prove its origin, so repeated and sequential
    patterns are rejected as an additional guard.
    """
    if len(secret) != _GENERATED_SECRET_LENGTH or not re.fullmatch(
        r"[A-Za-z0-9_-]{43}", secret
    ):
        return False

    frequencies = {char: secret.count(char) for char in set(secret)}
    if len(frequencies) < 12 or max(frequencies.values()) > 6:
        return False

    for period in range(1, _GENERATED_SECRET_LENGTH // 2 + 1):
        repeated = (secret[:period] * (_GENERATED_SECRET_LENGTH // period)) + secret[
            : _GENERATED_SECRET_LENGTH % period
        ]
        if secret == repeated:
            return False

    indexes = [_URLSAFE_ALPHABET.index(char) for char in secret]
    for direction in (-1, 1):
        run_length = 1
        for previous, current in zip(indexes, indexes[1:]):
            is_sequential = (
                (current - previous) % len(_URLSAFE_ALPHABET) == direction
            )
            run_length = run_length + 1 if is_sequential else 1
            if run_length >= 12:
                return False
    return True


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
        repr=False,
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

            # Non-development: require the documented generated-key format.
            if not _is_strong_secret(self.jwt_secret_key):
                raise ValueError(
                    "JWT_SECRET_KEY must be a non-patterned URL-safe key generated "
                    "from at least 32 cryptographically random bytes."
                )

        return self


def get_settings() -> Settings:
    """Return application settings (singleton-ish, cheap to construct)."""
    return Settings()
