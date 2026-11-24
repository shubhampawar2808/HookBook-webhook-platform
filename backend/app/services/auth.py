"""Registration and login services."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    harden_login_password_check,
    hash_password,
)
from app.models.enums import OrganizationStatus, UserRole, UserStatus
from app.models.organization import Organization
from app.models.user import User
from app.repositories.organization import OrganizationRepository
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.orgs = OrganizationRepository(session)
        self.users = UserRepository(session)

    async def register(self, data: RegisterRequest) -> tuple[Organization, User, TokenResponse]:
        if not self.settings.ALLOW_PUBLIC_REGISTRATION:
            raise UnauthorizedError("Public registration is disabled")
        existing = await self.orgs.get_by_slug(data.organization_slug)
        if existing is not None:
            raise ConflictError("Organization slug already exists")

        organization = Organization(
            name=data.organization_name.strip(),
            slug=data.organization_slug,
            status=OrganizationStatus.ACTIVE.value,
        )
        user = User(
            organization=organization,
            email=str(data.email).lower(),
            password_hash=hash_password(data.password),
            full_name=data.full_name.strip(),
            role=UserRole.OWNER.value,
            status=UserStatus.ACTIVE.value,
        )
        try:
            await self.orgs.add(organization)
            await self.users.add(user)
            await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError("Organization or user already exists") from exc

        token, _jti, expires_at = create_access_token(
            settings=self.settings,
            user_id=user.id,
            organization_id=organization.id,
            role=user.role,
        )
        return organization, user, TokenResponse(access_token=token, expires_at=expires_at)

    async def login(self, data: LoginRequest) -> TokenResponse:
        # Generic failure message — do not reveal whether email/org exists
        invalid = UnauthorizedError("Invalid credentials")

        organization = await self.orgs.get_by_slug(data.organization_slug)
        if organization is None:
            harden_login_password_check(data.password, None)
            raise invalid
        if organization.status == OrganizationStatus.SUSPENDED.value:
            harden_login_password_check(data.password, None)
            raise invalid

        user = await self.users.get_by_org_email(organization.id, str(data.email).lower())
        password_hash = user.password_hash if user is not None else None
        if not harden_login_password_check(data.password, password_hash):
            raise invalid
        if user is None or not user.is_active:
            raise invalid

        user.last_login_at = datetime.now(UTC)
        await self.session.flush()

        token, _jti, expires_at = create_access_token(
            settings=self.settings,
            user_id=user.id,
            organization_id=organization.id,
            role=user.role,
        )
        return TokenResponse(access_token=token, expires_at=expires_at)
