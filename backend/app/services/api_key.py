"""API key lifecycle service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.security import generate_api_key, hash_api_key
from app.models.api_key import APIKey
from app.models.enums import APIKeyStatus, UserRole
from app.models.user import User
from app.repositories.api_key import APIKeyRepository
from app.schemas.api_key import APIKeyCreateRequest
from app.utils.pagination import Page, PaginationParams


class APIKeyService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.repo = APIKeyRepository(session)

    def _require_manage(self, user: User) -> None:
        if user.role not in {UserRole.OWNER.value, UserRole.ADMIN.value}:
            raise ForbiddenError("Insufficient permissions to manage API keys")

    async def create(self, user: User, data: APIKeyCreateRequest) -> tuple[APIKey, str]:
        self._require_manage(user)
        raw_key, prefix, _ = generate_api_key()
        api_key = APIKey(
            organization_id=user.organization_id,
            name=data.name.strip(),
            key_prefix=prefix,
            key_hash=hash_api_key(raw_key, self.settings),
            status=APIKeyStatus.ACTIVE.value,
            expires_at=data.expires_at,
            created_by=user.id,
        )
        await self.repo.add(api_key)
        return api_key, raw_key

    async def list_keys(self, user: User, pagination: PaginationParams) -> Page[APIKey]:
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

    async def revoke(self, user: User, key_id: uuid.UUID) -> APIKey:
        self._require_manage(user)
        api_key = await self.repo.get_by_id_for_org(key_id, user.organization_id)
        if api_key is None:
            raise NotFoundError("API key not found")
        if api_key.status == APIKeyStatus.REVOKED.value:
            return api_key
        api_key.status = APIKeyStatus.REVOKED.value
        api_key.revoked_at = datetime.now(UTC)
        await self.session.flush()
        return api_key

    async def rotate(self, user: User, key_id: uuid.UUID) -> tuple[APIKey, str]:
        """Revoke an existing key and issue a replacement in one transaction."""
        self._require_manage(user)
        existing = await self.repo.get_by_id_for_org(key_id, user.organization_id)
        if existing is None:
            raise NotFoundError("API key not found")
        if existing.status != APIKeyStatus.REVOKED.value:
            existing.status = APIKeyStatus.REVOKED.value
            existing.revoked_at = datetime.now(UTC)

        raw_key, prefix, _ = generate_api_key()
        replacement = APIKey(
            organization_id=user.organization_id,
            name=f"{existing.name} (rotated)",
            key_prefix=prefix,
            key_hash=hash_api_key(raw_key, self.settings),
            status=APIKeyStatus.ACTIVE.value,
            expires_at=existing.expires_at,
            created_by=user.id,
        )
        await self.repo.add(replacement)
        return replacement, raw_key
