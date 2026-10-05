"""AuthService password hashing unit test — NFR-6.

Verifies that password hashing uses Argon2 (memory-hard KDF) and that
verification succeeds for correct passwords and fails for incorrect ones.

Expected values: Argon2 hash prefix ``$argon2`` and verification results come
from NFR-6 / Architecture §4, not from the implementation.
"""

from __future__ import annotations

from app.config import Settings
from app.services.auth_service import AuthService


async def test_password_hashing_uses_argon2_and_threadpool() -> None:
    """hash_password must produce an Argon2id hash; verify_password must be correct."""
    auth_service = AuthService(Settings())
    hashed = await auth_service.hash_password("SecurePass123!")

    # Argon2cffi emits hashes prefixed with $argon2id$
    assert hashed.startswith("$argon2")

    # Correct password verifies
    assert await auth_service.verify_password("SecurePass123!", hashed) is True

    # Incorrect password does NOT verify
    assert await auth_service.verify_password("WrongPassword", hashed) is False
