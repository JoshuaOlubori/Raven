"""Stateless asynchronous data-access functions (Standard §2 / §4).

Repository functions are pure: they accept a session and return domain
objects.  No business logic lives here — queries only.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staff import Staff


async def get_staff_by_id(session: AsyncSession, staff_id: UUID) -> Staff | None:
    """Fetch a single staff member by primary key."""
    return await session.get(Staff, staff_id)


async def get_staff_by_email(session: AsyncSession, email: str) -> Staff | None:
    """Fetch a single staff member by unique email address."""
    result = await session.scalars(select(Staff).where(Staff.email == email))
    return result.one_or_none()


async def create_staff(
    session: AsyncSession,
    *,
    email: str,
    hashed_password: str,
    full_name: str,
    role: str,
) -> Staff:
    """Insert a new staff member and return the persisted object."""
    staff = Staff(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        role=role,
    )
    session.add(staff)
    await session.flush()
    await session.refresh(staff)
    return staff


async def list_staff(
    session: AsyncSession,
    role: str | None = None,
    active_only: bool = True,
) -> list[Staff]:
    """Return staff members, optionally filtered by role and active status."""
    query = select(Staff)
    if role is not None:
        query = query.where(Staff.role == role)
    if active_only:
        query = query.where(Staff.is_active.is_(True))
    result = await session.execute(query)
    return list(result.scalars().all())


async def update_staff(
    session: AsyncSession,
    staff: Staff,
    **kwargs: object,
) -> Staff:
    """Apply keyword field updates to a staff row and return the refreshed object."""
    for key, value in kwargs.items():
        setattr(staff, key, value)
    session.add(staff)
    await session.flush()
    await session.refresh(staff)
    return staff
