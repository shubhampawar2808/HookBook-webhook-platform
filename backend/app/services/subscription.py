"""Subscription service with same-organization enforcement."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.enums import SubscriptionStatus, UserRole
from app.models.subscription import EndpointSubscription
from app.models.user import User
from app.repositories.endpoint import EndpointRepository
from app.repositories.event_type import EventTypeRepository
from app.repositories.subscription import SubscriptionRepository
from app.schemas.subscription import SubscriptionCreateRequest
from app.utils.pagination import Page, PaginationParams


class SubscriptionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SubscriptionRepository(session)
        self.endpoints = EndpointRepository(session)
        self.event_types = EventTypeRepository(session)

    def _require_write(self, user: User) -> None:
        if user.role not in {
            UserRole.OWNER.value,
            UserRole.ADMIN.value,
            UserRole.MEMBER.value,
        }:
            raise ForbiddenError("Insufficient permissions")

    async def create(
        self,
        user: User,
        endpoint_id: uuid.UUID,
        data: SubscriptionCreateRequest,
    ) -> EndpointSubscription:
        self._require_write(user)
        endpoint = await self.endpoints.get_for_org(endpoint_id, user.organization_id)
        if endpoint is None:
            raise NotFoundError("Endpoint not found")

        event_type = await self.event_types.get_for_org(data.event_type_id, user.organization_id)
        if event_type is None:
            # Do not leak whether the event type exists in another org
            raise NotFoundError("Event type not found")

        subscription = EndpointSubscription(
            organization_id=user.organization_id,
            endpoint_id=endpoint.id,
            event_type_id=event_type.id,
            status=SubscriptionStatus.ACTIVE.value,
        )
        try:
            return await self.repo.add(subscription)
        except IntegrityError as exc:
            raise ConflictError("Subscription already exists") from exc

    async def list_for_endpoint(
        self,
        user: User,
        endpoint_id: uuid.UUID,
        pagination: PaginationParams,
    ) -> Page[EndpointSubscription]:
        endpoint = await self.endpoints.get_for_org(endpoint_id, user.organization_id)
        if endpoint is None:
            raise NotFoundError("Endpoint not found")
        items, total = await self.repo.list_for_endpoint(
            endpoint_id,
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

    async def delete(
        self,
        user: User,
        endpoint_id: uuid.UUID,
        subscription_id: uuid.UUID,
    ) -> None:
        self._require_write(user)
        subscription = await self.repo.get_for_org(
            subscription_id,
            user.organization_id,
            endpoint_id=endpoint_id,
        )
        if subscription is None:
            raise NotFoundError("Subscription not found")
        await self.repo.delete(subscription)
