"""Organization management service."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.enums import UserRole
from app.models.organization import Organization
from app.models.user import User
from app.repositories.organization import OrganizationRepository
from app.schemas.organization import OrganizationUpdateRequest


class OrganizationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = OrganizationRepository(session)

    async def get_mine(self, user: User) -> Organization:
        org = await self.repo.get_by_id(user.organization_id)
        if org is None:
            raise NotFoundError("Organization not found")
        return org

    async def update_mine(self, user: User, data: OrganizationUpdateRequest) -> Organization:
        if user.role != UserRole.OWNER.value:
            raise ForbiddenError("Only owners can update the organization")
        org = await self.get_mine(user)
        if data.name is not None:
            org.name = data.name.strip()
        if data.slug is not None and data.slug != org.slug:
            conflict = await self.repo.get_by_slug(data.slug)
            if conflict is not None and conflict.id != org.id:
                raise ConflictError("Organization slug already exists")
            org.slug = data.slug
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError("Organization slug already exists") from exc
        return org
