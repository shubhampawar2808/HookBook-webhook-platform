"""Organization-scoped delivery query and replay."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.enums import DeliveryStatus, UserRole
from app.models.user import User
from app.repositories.delivery import DeliveryRepository
from app.services.delivery_dispatch import enqueue_delivery_jobs
from app.utils.pagination import Page, PaginationParams


class DeliveryManagementService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repo = DeliveryRepository(session)

    async def list_deliveries(
        self,
        user: User,
        pagination: PaginationParams,
        *,
        status: str | None = None,
        event_id: uuid.UUID | None = None,
        endpoint_id: uuid.UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        dead_letter_only: bool = False,
    ) -> Page:
        items, total = await self.repo.list_for_org(
            user.organization_id,
            offset=pagination.offset,
            limit=pagination.page_size,
            status=status,
            event_id=event_id,
            endpoint_id=endpoint_id,
            created_from=created_from,
            created_to=created_to,
            dead_letter_only=dead_letter_only,
        )
        return Page.create(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def get_delivery(self, user: User, delivery_id: uuid.UUID):
        delivery = await self.repo.get_for_org(delivery_id, user.organization_id)
        if delivery is None:
            raise NotFoundError("Delivery not found")
        return delivery

    async def list_attempts(self, user: User, delivery_id: uuid.UUID):
        delivery = await self.get_delivery(user, delivery_id)
        return await self.repo.list_attempts(delivery.id, user.organization_id)

    async def replay(self, user: User, delivery_id: uuid.UUID):
        if user.role not in {UserRole.OWNER.value, UserRole.ADMIN.value}:
            raise ForbiddenError("Insufficient permissions to replay deliveries")

        delivery = await self.get_delivery(user, delivery_id)
        if delivery.status not in {
            DeliveryStatus.DEAD_LETTER.value,
            DeliveryStatus.FAILED.value,
        }:
            raise ConflictError("Only failed or dead-letter deliveries can be replayed")

        if delivery.status == DeliveryStatus.PROCESSING.value:
            raise ConflictError("Delivery is currently processing")

        now = datetime.now(UTC)
        delivery.status = DeliveryStatus.PENDING.value
        delivery.next_attempt_at = now
        delivery.enqueued_at = None
        delivery.processing_started_at = None
        delivery.last_error = None
        delivery.replay_count = (delivery.replay_count or 0) + 1
        delivery.last_replayed_at = now
        # Keep attempt_count / history; retries continue numbering
        await self.session.flush()
        return delivery

    def enqueue_replay(self, delivery_id: uuid.UUID) -> dict[str, int]:
        return enqueue_delivery_jobs([delivery_id])
