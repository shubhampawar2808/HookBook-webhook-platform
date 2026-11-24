"""User data access — always organization-scoped where applicable."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        # populate_existing avoids stale organization.status from the identity map
        # (critical for suspension checks on authenticated requests).
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.organization))
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_by_org_email(self, organization_id: uuid.UUID, email: str) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(
                User.organization_id == organization_id,
                User.email == email.lower(),
            )
            .options(selectinload(User.organization))
        )
        return result.scalar_one_or_none()

    async def add(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user
