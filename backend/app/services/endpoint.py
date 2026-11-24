"""Webhook endpoint service — tenant-scoped."""

from __future__ import annotations

import secrets
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.secret_box import seal_endpoint_secret
from app.models.endpoint import WebhookEndpoint
from app.models.enums import EndpointStatus, UserRole
from app.models.user import User
from app.repositories.endpoint import EndpointRepository
from app.schemas.endpoint import EndpointCreateRequest, EndpointUpdateRequest
from app.utils.pagination import Page, PaginationParams


class EndpointService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repo = EndpointRepository(session)

    def _require_write(self, user: User) -> None:
        if user.role not in {
            UserRole.OWNER.value,
            UserRole.ADMIN.value,
            UserRole.MEMBER.value,
        }:
            raise ForbiddenError("Insufficient permissions")
        # Members may create/update operational endpoints; deletes require admin+
        if user.role == UserRole.MEMBER.value:
            return

    def _require_delete(self, user: User) -> None:
        if user.role not in {UserRole.OWNER.value, UserRole.ADMIN.value}:
            raise ForbiddenError("Insufficient permissions to delete endpoints")

    async def create(self, user: User, data: EndpointCreateRequest) -> WebhookEndpoint:
        self._require_write(user)
        signing_secret = secrets.token_urlsafe(32)
        endpoint = WebhookEndpoint(
            organization_id=user.organization_id,
            name=data.name.strip(),
            url=data.url,
            description=data.description,
            signing_secret=seal_endpoint_secret(signing_secret, self.settings),
            status=EndpointStatus.ACTIVE.value,
            created_by=user.id,
        )
        created = await self.repo.add(endpoint)
        # Attach once for create response; never persisted into API list schemas
        created._plaintext_signing_secret = signing_secret  # type: ignore[attr-defined]
        return created

    async def list(self, user: User, pagination: PaginationParams) -> Page[WebhookEndpoint]:
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

    async def get(self, user: User, endpoint_id: uuid.UUID) -> WebhookEndpoint:
        endpoint = await self.repo.get_for_org(endpoint_id, user.organization_id)
        if endpoint is None:
            raise NotFoundError("Endpoint not found")
        return endpoint

    async def update(
        self, user: User, endpoint_id: uuid.UUID, data: EndpointUpdateRequest
    ) -> WebhookEndpoint:
        self._require_write(user)
        endpoint = await self.get(user, endpoint_id)
        if data.name is not None:
            endpoint.name = data.name.strip()
        if data.url is not None:
            endpoint.url = data.url
        if data.description is not None:
            endpoint.description = data.description
        if data.status is not None:
            endpoint.status = data.status
        await self.session.flush()
        return endpoint

    async def delete(self, user: User, endpoint_id: uuid.UUID) -> None:
        self._require_delete(user)
        endpoint = await self.get(user, endpoint_id)
        await self.repo.delete(endpoint)
