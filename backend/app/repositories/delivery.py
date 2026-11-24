"""Delivery and attempt data access."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.delivery import WebhookDelivery, WebhookDeliveryAttempt
from app.models.enums import DeliveryStatus


class DeliveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, delivery: WebhookDelivery) -> WebhookDelivery:
        self.session.add(delivery)
        await self.session.flush()
        return delivery

    async def add_attempt(self, attempt: WebhookDeliveryAttempt) -> WebhookDeliveryAttempt:
        self.session.add(attempt)
        await self.session.flush()
        return attempt

    async def get_for_org(
        self, delivery_id: uuid.UUID, organization_id: uuid.UUID
    ) -> WebhookDelivery | None:
        result = await self.session.execute(
            select(WebhookDelivery)
            .where(
                WebhookDelivery.id == delivery_id,
                WebhookDelivery.organization_id == organization_id,
            )
            .options(selectinload(WebhookDelivery.attempts))
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, delivery_id: uuid.UUID) -> WebhookDelivery | None:
        result = await self.session.execute(
            select(WebhookDelivery)
            .where(WebhookDelivery.id == delivery_id)
            .options(
                selectinload(WebhookDelivery.event),
                selectinload(WebhookDelivery.endpoint),
            )
            .with_for_update(skip_locked=True)
        )
        return result.scalar_one_or_none()

    async def list_for_org(
        self,
        organization_id: uuid.UUID,
        *,
        offset: int,
        limit: int,
        status: str | None = None,
        event_id: uuid.UUID | None = None,
        endpoint_id: uuid.UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        dead_letter_only: bool = False,
    ) -> tuple[list[WebhookDelivery], int]:
        filters = [WebhookDelivery.organization_id == organization_id]
        if dead_letter_only:
            filters.append(WebhookDelivery.status == DeliveryStatus.DEAD_LETTER.value)
        elif status:
            filters.append(WebhookDelivery.status == status)
        if event_id:
            filters.append(WebhookDelivery.event_id == event_id)
        if endpoint_id:
            filters.append(WebhookDelivery.endpoint_id == endpoint_id)
        if created_from:
            filters.append(WebhookDelivery.created_at >= created_from)
        if created_to:
            filters.append(WebhookDelivery.created_at <= created_to)

        total = await self.session.scalar(
            select(func.count()).select_from(WebhookDelivery).where(*filters)
        )
        result = await self.session.execute(
            select(WebhookDelivery)
            .where(*filters)
            .order_by(WebhookDelivery.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), int(total or 0)

    async def list_attempts(
        self, delivery_id: uuid.UUID, organization_id: uuid.UUID
    ) -> list[WebhookDeliveryAttempt]:
        result = await self.session.execute(
            select(WebhookDeliveryAttempt)
            .where(
                WebhookDeliveryAttempt.delivery_id == delivery_id,
                WebhookDeliveryAttempt.organization_id == organization_id,
            )
            .order_by(WebhookDeliveryAttempt.attempt_number.asc())
        )
        return list(result.scalars().all())

    def due_recoverable_query(self, *, now: datetime, stale_before: datetime) -> Select:
        return (
            select(WebhookDelivery.id)
            .where(
                or_(
                    and_(
                        WebhookDelivery.status == DeliveryStatus.PENDING.value,
                        WebhookDelivery.enqueued_at.is_(None),
                    ),
                    and_(
                        WebhookDelivery.status == DeliveryStatus.RETRYING.value,
                        WebhookDelivery.next_attempt_at.is_not(None),
                        WebhookDelivery.next_attempt_at <= now,
                    ),
                    and_(
                        WebhookDelivery.status == DeliveryStatus.PROCESSING.value,
                        WebhookDelivery.processing_started_at.is_not(None),
                        WebhookDelivery.processing_started_at <= stale_before,
                    ),
                )
            )
            .order_by(WebhookDelivery.created_at.asc())
        )
