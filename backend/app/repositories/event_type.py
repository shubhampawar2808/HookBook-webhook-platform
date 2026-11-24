"""Event type data access — organization-scoped."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_type import EventType


class EventTypeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_org(
        self, event_type_id: uuid.UUID, organization_id: uuid.UUID
    ) -> EventType | None:
        result = await self.session.execute(
            select(EventType).where(
                EventType.id == event_type_id,
                EventType.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_name_for_org(self, name: str, organization_id: uuid.UUID) -> EventType | None:
        result = await self.session.execute(
            select(EventType).where(
                EventType.organization_id == organization_id,
                EventType.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_org(
        self, organization_id: uuid.UUID, *, offset: int, limit: int
    ) -> tuple[list[EventType], int]:
        total = await self.session.scalar(
            select(func.count())
            .select_from(EventType)
            .where(EventType.organization_id == organization_id)
        )
        result = await self.session.execute(
            select(EventType)
            .where(EventType.organization_id == organization_id)
            .order_by(EventType.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), int(total or 0)

    async def add(self, event_type: EventType) -> EventType:
        self.session.add(event_type)
        await self.session.flush()
        return event_type
