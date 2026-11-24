"""API key management endpoints (JWT auth)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.schemas.api_key import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyResponse,
)
from app.schemas.common import PageResponse
from app.services.api_key import APIKeyService
from app.utils.pagination import PaginationParams

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post(
    "",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    body: APIKeyCreateRequest,
    user: CurrentUser,
    session: DbSession,
    settings: AppSettings,
) -> APIKeyCreateResponse:
    key, raw = await APIKeyService(session, settings).create(user, body)
    return APIKeyCreateResponse(
        **APIKeyResponse.model_validate(key).model_dump(),
        api_key=raw,
    )


@router.get("", response_model=PageResponse[APIKeyResponse])
async def list_api_keys(
    user: CurrentUser,
    session: DbSession,
    settings: AppSettings,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PageResponse[APIKeyResponse]:
    result = await APIKeyService(session, settings).list_keys(
        user, PaginationParams(page=page, page_size=page_size)
    )
    return PageResponse(
        items=[APIKeyResponse.model_validate(i) for i in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )


@router.delete("/{key_id}", response_model=APIKeyResponse)
async def revoke_api_key(
    key_id: uuid.UUID,
    user: CurrentUser,
    session: DbSession,
    settings: AppSettings,
) -> APIKeyResponse:
    key = await APIKeyService(session, settings).revoke(user, key_id)
    return APIKeyResponse.model_validate(key)


@router.post(
    "/{key_id}/rotate",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def rotate_api_key(
    key_id: uuid.UUID,
    user: CurrentUser,
    session: DbSession,
    settings: AppSettings,
) -> APIKeyCreateResponse:
    key, raw = await APIKeyService(session, settings).rotate(user, key_id)
    return APIKeyCreateResponse(
        **APIKeyResponse.model_validate(key).model_dump(),
        api_key=raw,
    )
