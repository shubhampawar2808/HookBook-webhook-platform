"""Subscription data access — organization-scoped."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import EndpointSubscription


class SubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_org(
        self,
        subscription_id: uuid.UUID,
        organization_id: uuid.UUID,
        *,
        endpoint_id: uuid.UUID | None = None,
    ) -> EndpointSubscription | None:
        stmt = select(EndpointSubscription).where(
            EndpointSubscription.id == subscription_id,
            EndpointSubscription.organization_id == organization_id,
        )
        if endpoint_id is not None:
            stmt = stmt.where(EndpointSubscription.endpoint_id == endpoint_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_endpoint(
        self,
        endpoint_id: uuid.UUID,
        organization_id: uuid.UUID,
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[EndpointSubscription], int]:
        filters = (
            EndpointSubscription.endpoint_id == endpoint_id,
            EndpointSubscription.organization_id == organization_id,
        )
        total = await self.session.scalar(
            select(func.count()).select_from(EndpointSubscription).where(*filters)
        )
        result = await self.session.execute(
            select(EndpointSubscription)
            .where(*filters)
            .order_by(EndpointSubscription.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), int(total or 0)

    async def add(self, subscription: EndpointSubscription) -> EndpointSubscription:
        self.session.add(subscription)
        await self.session.flush()
        return subscription

    async def delete(self, subscription: EndpointSubscription) -> None:
        await self.session.delete(subscription)
        await self.session.flush()
