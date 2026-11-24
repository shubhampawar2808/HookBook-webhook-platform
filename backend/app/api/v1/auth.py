"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequest,
    session: DbSession,
    settings: AppSettings,
) -> TokenResponse:
    service = AuthService(session, settings)
    _org, _user, token = await service.register(body)
    return token


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: DbSession,
    settings: AppSettings,
) -> TokenResponse:
    return await AuthService(session, settings).login(body)


@router.get("/me", response_model=CurrentUserResponse)
async def me(user: CurrentUser) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        organization_id=user.organization_id,
        organization_name=user.organization.name,
    )
