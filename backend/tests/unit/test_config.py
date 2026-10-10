"""Settings validation unit tests — T-015.

Verifies that JWT secret validation enforces strong secrets in non-development
environments while allowing the default in development.

Expected values come from T-015 acceptance criteria and NFR-6.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings

_DEV_DEFAULT = "dev-insecure-secret-change-in-production"
_STRONG_SECRET = "this-is-a-strong-secret-key-with-32-chars"


def test_development_allows_default_secret() -> None:
    """Development environment accepts the default insecure secret."""
    settings = Settings(app_env="development", jwt_secret_key=_DEV_DEFAULT)
    assert settings.jwt_secret_key == _DEV_DEFAULT


def test_development_allows_weak_secret() -> None:
    """Development environment accepts any secret (no strength enforcement)."""
    settings = Settings(app_env="development", jwt_secret_key="weak")
    assert settings.jwt_secret_key == "weak"


def test_production_rejects_default_secret() -> None:
    """Production environment rejects the development default secret."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(app_env="production", jwt_secret_key=_DEV_DEFAULT)

    error_msg = str(exc_info.value)
    assert "development default is not permitted" in error_msg
    # Secret value must not appear in error message
    assert _DEV_DEFAULT not in error_msg


def test_production_rejects_short_secret() -> None:
    """Production environment rejects secrets below minimum length."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(app_env="production", jwt_secret_key="short")

    error_msg = str(exc_info.value)
    assert "at least 32 characters" in error_msg
    # Secret value must not appear in error message
    assert "short" not in error_msg


def test_production_accepts_strong_secret() -> None:
    """Production environment accepts a sufficiently strong explicit secret."""
    settings = Settings(app_env="production", jwt_secret_key=_STRONG_SECRET)
    assert settings.jwt_secret_key == _STRONG_SECRET


def test_production_case_insensitive() -> None:
    """Environment check is case-insensitive (Production, PRODUCTION, etc.)."""
    with pytest.raises(ValidationError):
        Settings(app_env="Production", jwt_secret_key=_DEV_DEFAULT)

    with pytest.raises(ValidationError):
        Settings(app_env="PRODUCTION", jwt_secret_key=_DEV_DEFAULT)


def test_test_env_requires_strong_secret() -> None:
    """Test environment (non-development) requires strong secret."""
    with pytest.raises(ValidationError):
        Settings(app_env="test", jwt_secret_key=_DEV_DEFAULT)

    # But strong secret works
    settings = Settings(app_env="test", jwt_secret_key=_STRONG_SECRET)
    assert settings.jwt_secret_key == _STRONG_SECRET


def test_staging_env_requires_strong_secret() -> None:
    """Staging environment (non-development) requires strong secret."""
    with pytest.raises(ValidationError):
        Settings(app_env="staging", jwt_secret_key=_DEV_DEFAULT)

    settings = Settings(app_env="staging", jwt_secret_key=_STRONG_SECRET)
    assert settings.jwt_secret_key == _STRONG_SECRET
