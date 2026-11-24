"""Event data access — organization-scoped."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, event: Event) -> Event:
        self.session.add(event)
        await self.session.flush()
        return event
