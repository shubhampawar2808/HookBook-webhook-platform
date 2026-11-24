"""API key data access."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.api_key import APIKey


class APIKeyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id_for_org(
        self, key_id: uuid.UUID, organization_id: uuid.UUID
    ) -> APIKey | None:
        result = await self.session.execute(
            select(APIKey).where(
                APIKey.id == key_id,
                APIKey.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, key_hash: str) -> APIKey | None:
        result = await self.session.execute(
            select(APIKey)
            .where(APIKey.key_hash == key_hash)
            .options(selectinload(APIKey.organization))
        )
        return result.scalar_one_or_none()

    async def list_for_org(
        self, organization_id: uuid.UUID, *, offset: int, limit: int
    ) -> tuple[list[APIKey], int]:
        total = await self.session.scalar(
            select(func.count())
            .select_from(APIKey)
            .where(APIKey.organization_id == organization_id)
        )
        result = await self.session.execute(
            select(APIKey)
            .where(APIKey.organization_id == organization_id)
            .order_by(APIKey.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), int(total or 0)

    async def add(self, api_key: APIKey) -> APIKey:
        self.session.add(api_key)
        await self.session.flush()
        return api_key
