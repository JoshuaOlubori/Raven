"""Authentication service: password hashing, JWT issuance, and token validation.

Implements Spec 01 §5 (Concurrency — Argon2 offloaded to thread pool) and
Spec 01 §6 (State — stateless JWT signing).

Public API:
  * ``AuthService.hash_password`` — Argon2id hash (CPU-bound, offloaded).
  * ``AuthService.verify_password`` — Argon2id verification (CPU-bound, offloaded).
  * ``AuthService.create_token`` — Encode a signed HS256 JWT for a staff member.
  * ``AuthService.decode_token`` — Decode and validate an HS256 JWT.
  * ``AuthError`` / ``InvalidCredentialsError`` / ``InactiveAccountError`` —
    domain exceptions mapped to HTTP responses by ``main.py``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt as pyjwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings

# ---------------------------------------------------------------------------
# Token duration (Architecture §4 — "short-lived JWT access tokens")
# ---------------------------------------------------------------------------

TOKEN_EXPIRY_MINUTES: int = 30


# ---------------------------------------------------------------------------
# Domain exceptions (Spec 01 §7 — Errors)
# ---------------------------------------------------------------------------


class AuthError(Exception):
    """Base class for authentication / authorization domain errors.

    Subclasses set ``error_code``, ``message``, and optionally ``status_code``.
    ``main.py`` registers a single handler for ``AuthError`` that maps all
    subclasses to the standardized error body (Architecture §4).
    """

    error_code: str = "AUTH_ERROR"
    message: str = "Authentication error"
    status_code: int = 401


class InvalidCredentialsError(AuthError):
    """Raised when the email is unknown or the password does not match."""

    error_code = "AUTH_INVALID_CREDENTIALS"
    message = "Invalid email or password"


class InactiveAccountError(AuthError):
    """Raised when the staff member exists but ``is_active`` is ``False``."""

    error_code = "AUTH_INACTIVE_ACCOUNT"
    message = "Account is inactive"


# ---------------------------------------------------------------------------
# Token payload
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TokenPayload:
    """Decoded JWT claims."""

    staff_id: str
    role: str


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AuthService:
    """Stateless authentication service (NFR-6).

    The ``session`` parameter is accepted per Architecture §4 (`get_auth_service`
    dependency signature) so the service can be extended by future tickets
    (e.g. staff management).  It is not required for the hashing/JWT methods
    exposed in T-002.
    """

    def __init__(
        self,
        settings: Settings,
        session: AsyncSession | None = None,
    ) -> None:
        self._settings = settings
        self._session = session
        self._hasher = PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            salt_len=16,
        )

    # -- Password hashing (Spec 01 §5: offload to thread pool) ----------------

    async def hash_password(self, password: str) -> str:
        """Hash a password using Argon2id, offloaded to the default thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._hasher.hash, password)

    async def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against an Argon2id hash, offloaded to the thread pool."""
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self._hasher.verify, hashed, password)
            return True
        except VerifyMismatchError:
            return False

    # -- JWT token issuance / validation (Architecture §4: HS256) ------------

    def create_token(self, staff_id: str, role: str) -> str:
        """Encode a signed HS256 JWT with ``sub``, ``role``, ``exp``, ``iat``."""
        now = datetime.now(UTC)
        payload = {
            "sub": staff_id,
            "role": role,
            "iat": now,
            "exp": now + timedelta(minutes=TOKEN_EXPIRY_MINUTES),
        }
        return pyjwt.encode(payload, self._settings.jwt_secret_key, algorithm="HS256")

    def decode_token(self, token: str) -> TokenPayload:
        """Decode and validate an HS256 JWT, returning the claims payload.

        Raises ``jwt.PyJWTError`` (or a subclass such as
        ``ExpiredSignatureError``) if the token is invalid or expired.
        """
        payload = pyjwt.decode(
            token,
            self._settings.jwt_secret_key,
            algorithms=["HS256"],
        )
        return TokenPayload(
            staff_id=payload["sub"],
            role=payload["role"],
        )
