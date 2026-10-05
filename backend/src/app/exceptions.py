"""Domain exception hierarchy (Architecture §4 — Global Error Model).

All application-level errors inherit from ``DomainError`` so that a single
exception handler in ``main.py`` maps them to the standardized error body:

    {"error": "<code_string>", "message": "<str>", "correlation_id": "<str>"}
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain/application exceptions.

    Subclasses set ``error_code`` (the machine-readable error string returned
    in the ``error`` field), ``message`` (human-readable text), and
    ``status_code`` (the HTTP status).  ``main.py`` registers one handler for
    ``DomainError`` that covers all subclasses (Architecture §4).
    """

    error_code: str = "DOMAIN_ERROR"
    message: str = "Domain error"
    status_code: int = 400


class EmailAlreadyExistsError(DomainError):
    """Raised when a staff member is created with an email already in use."""

    error_code = "STAFF_EMAIL_EXISTS"
    message = "A staff member with this email already exists"
    status_code = 409


class StaffNotFoundError(DomainError):
    """Raised when a staff member lookup by ID finds no match."""

    error_code = "STAFF_NOT_FOUND"
    message = "Staff member not found"
    status_code = 404


class ForbiddenError(DomainError):
    """Raised when an authenticated user lacks the role(s) required for a resource."""

    error_code = "RBAC_FORBIDDEN"
    message = "Insufficient role"
    status_code = 403
