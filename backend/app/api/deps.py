"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import (
    hash_api_key,
    is_api_key_authorization,
    parse_bearer_token,
)
from app.db.session import get_db
from app.models.api_key import APIKey
from app.models.enums import APIKeyStatus, OrganizationStatus, UserRole, UserStatus
from app.models.user import User
from app.repositories.api_key import APIKeyRepository
from app.repositories.user import UserRepository

DbSession = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


async def get_current_user(
    session: DbSession,
    settings: AppSettings,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Authenticate a human operator via JWT Bearer token."""
    if is_api_key_authorization(authorization):
        raise UnauthorizedError("JWT access token required")

    token = parse_bearer_token(authorization)
    if not token:
        raise UnauthorizedError("Not authenticated")

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "org", "role", "jti", "typ"]},
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc

    if payload.get("typ") != "access":
        raise UnauthorizedError("Invalid token type")

    try:
        user_id = uuid.UUID(str(payload["sub"]))
        org_id = uuid.UUID(str(payload["org"]))
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Invalid token claims") from exc

    user = await UserRepository(session).get_by_id(user_id)
    if user is None or user.organization_id != org_id:
        raise UnauthorizedError("Invalid credentials")
    if user.status != UserStatus.ACTIVE.value:
        raise UnauthorizedError("User is disabled")
    if user.organization is None:
        raise UnauthorizedError("Invalid credentials")
    if user.organization.status == OrganizationStatus.SUSPENDED.value:
        raise UnauthorizedError("Organization is suspended")
    return user


async def get_current_api_key(
    session: DbSession,
    settings: AppSettings,
    authorization: Annotated[str | None, Header()] = None,
) -> APIKey:
    """Authenticate a machine client via API key Bearer token."""
    token = parse_bearer_token(authorization)
    if not token or not is_api_key_authorization(authorization):
        raise UnauthorizedError("API key required")

    key_hash = hash_api_key(token, settings)
    api_key = await APIKeyRepository(session).get_by_hash(key_hash)
    if api_key is None:
        raise UnauthorizedError("Invalid API key")

    now = datetime.now(UTC)
    if api_key.status == APIKeyStatus.REVOKED.value or api_key.revoked_at is not None:
        raise UnauthorizedError("API key revoked")
    if api_key.expires_at is not None and api_key.expires_at <= now:
        api_key.status = APIKeyStatus.EXPIRED.value
        await session.flush()
        raise UnauthorizedError("API key expired")
    if api_key.status != APIKeyStatus.ACTIVE.value:
        raise UnauthorizedError("API key inactive")
    if (
        api_key.organization is None
        or api_key.organization.status == OrganizationStatus.SUSPENDED.value
    ):
        raise UnauthorizedError("Organization is suspended")

    # Throttle last_used_at writes
    interval = settings.API_KEY_LAST_USED_MIN_INTERVAL_SECONDS
    if api_key.last_used_at is None or (now - api_key.last_used_at).total_seconds() >= interval:
        api_key.last_used_at = now
        await session.flush()

    return api_key


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAPIKey = Annotated[APIKey, Depends(get_current_api_key)]


def require_roles(*roles: UserRole):
    """Dependency factory enforcing explicit role membership."""

    allowed = {role.value for role in roles}

    async def _checker(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise ForbiddenError("Insufficient permissions")
        return user

    return _checker
