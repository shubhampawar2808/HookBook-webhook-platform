"""Event type service — tenant-scoped."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.enums import UserRole
from app.models.event_type import EventType
from app.models.user import User
from app.repositories.event_type import EventTypeRepository
from app.schemas.event_type import EventTypeCreateRequest
from app.utils.pagination import Page, PaginationParams


class EventTypeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = EventTypeRepository(session)

    def _require_write(self, user: User) -> None:
        if user.role not in {UserRole.OWNER.value, UserRole.ADMIN.value}:
            raise ForbiddenError("Insufficient permissions to manage event types")

    async def create(self, user: User, data: EventTypeCreateRequest) -> EventType:
        self._require_write(user)
        existing = await self.repo.get_by_name_for_org(data.name, user.organization_id)
        if existing is not None:
            raise ConflictError("Event type name already exists")
        event_type = EventType(
            organization_id=user.organization_id,
            name=data.name,
            description=data.description,
        )
        try:
            return await self.repo.add(event_type)
        except IntegrityError as exc:
            raise ConflictError("Event type name already exists") from exc

    async def list(self, user: User, pagination: PaginationParams) -> Page[EventType]:
        items, total = await self.repo.list_for_org(
            user.organization_id,
            offset=pagination.offset,
            limit=pagination.page_size,
        )
        return Page.create(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def get(self, user: User, event_type_id: uuid.UUID) -> EventType:
        event_type = await self.repo.get_for_org(event_type_id, user.organization_id)
        if event_type is None:
            raise NotFoundError("Event type not found")
        return event_type
