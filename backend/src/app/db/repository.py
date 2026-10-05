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
