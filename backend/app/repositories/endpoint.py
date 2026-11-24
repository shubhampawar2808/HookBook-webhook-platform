"""Webhook endpoint data access — organization-scoped."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.endpoint import WebhookEndpoint


class EndpointRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_org(
        self, endpoint_id: uuid.UUID, organization_id: uuid.UUID
    ) -> WebhookEndpoint | None:
        result = await self.session.execute(
            select(WebhookEndpoint).where(
                WebhookEndpoint.id == endpoint_id,
                WebhookEndpoint.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_org(
        self, organization_id: uuid.UUID, *, offset: int, limit: int
    ) -> tuple[list[WebhookEndpoint], int]:
        total = await self.session.scalar(
            select(func.count())
            .select_from(WebhookEndpoint)
            .where(WebhookEndpoint.organization_id == organization_id)
        )
        result = await self.session.execute(
            select(WebhookEndpoint)
            .where(WebhookEndpoint.organization_id == organization_id)
            .order_by(WebhookEndpoint.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), int(total or 0)

    async def add(self, endpoint: WebhookEndpoint) -> WebhookEndpoint:
        self.session.add(endpoint)
        await self.session.flush()
        return endpoint

    async def delete(self, endpoint: WebhookEndpoint) -> None:
        await self.session.delete(endpoint)
        await self.session.flush()
