"""Webhook endpoint and subscription routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import MessageResponse, PageResponse
from app.schemas.endpoint import (
    EndpointCreateRequest,
    EndpointCreateResponse,
    EndpointResponse,
    EndpointUpdateRequest,
)
from app.schemas.subscription import SubscriptionCreateRequest, SubscriptionResponse
from app.services.endpoint import EndpointService
from app.services.subscription import SubscriptionService
from app.utils.pagination import PaginationParams

router = APIRouter(prefix="/endpoints", tags=["endpoints"])


@router.post(
    "",
    response_model=EndpointCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_endpoint(
    body: EndpointCreateRequest,
    user: CurrentUser,
    session: DbSession,
) -> EndpointCreateResponse:
    endpoint = await EndpointService(session).create(user, body)
    secret = getattr(endpoint, "_plaintext_signing_secret", None)
    return EndpointCreateResponse(
        **EndpointResponse.model_validate(endpoint).model_dump(),
        signing_secret=secret or endpoint.signing_secret,
    )


@router.get("", response_model=PageResponse[EndpointResponse])
async def list_endpoints(
    user: CurrentUser,
    session: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PageResponse[EndpointResponse]:
    result = await EndpointService(session).list(
        user, PaginationParams(page=page, page_size=page_size)
    )
    return PageResponse(
        items=[EndpointResponse.model_validate(i) for i in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )


@router.get("/{endpoint_id}", response_model=EndpointResponse)
async def get_endpoint(
    endpoint_id: uuid.UUID,
    user: CurrentUser,
    session: DbSession,
) -> EndpointResponse:
    endpoint = await EndpointService(session).get(user, endpoint_id)
    return EndpointResponse.model_validate(endpoint)


@router.patch("/{endpoint_id}", response_model=EndpointResponse)
async def update_endpoint(
    endpoint_id: uuid.UUID,
    body: EndpointUpdateRequest,
    user: CurrentUser,
    session: DbSession,
) -> EndpointResponse:
    endpoint = await EndpointService(session).update(user, endpoint_id, body)
    return EndpointResponse.model_validate(endpoint)


@router.delete("/{endpoint_id}", response_model=MessageResponse)
async def delete_endpoint(
    endpoint_id: uuid.UUID,
    user: CurrentUser,
    session: DbSession,
) -> MessageResponse:
    await EndpointService(session).delete(user, endpoint_id)
    return MessageResponse(message="Endpoint deleted")


@router.post(
    "/{endpoint_id}/subscriptions",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription(
    endpoint_id: uuid.UUID,
    body: SubscriptionCreateRequest,
    user: CurrentUser,
    session: DbSession,
) -> SubscriptionResponse:
    sub = await SubscriptionService(session).create(user, endpoint_id, body)
    return SubscriptionResponse.model_validate(sub)


@router.get(
    "/{endpoint_id}/subscriptions",
    response_model=PageResponse[SubscriptionResponse],
)
async def list_subscriptions(
    endpoint_id: uuid.UUID,
    user: CurrentUser,
    session: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PageResponse[SubscriptionResponse]:
    result = await SubscriptionService(session).list_for_endpoint(
        user,
        endpoint_id,
        PaginationParams(page=page, page_size=page_size),
    )
    return PageResponse(
        items=[SubscriptionResponse.model_validate(i) for i in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )


@router.delete(
    "/{endpoint_id}/subscriptions/{subscription_id}",
    response_model=MessageResponse,
)
async def delete_subscription(
    endpoint_id: uuid.UUID,
    subscription_id: uuid.UUID,
    user: CurrentUser,
    session: DbSession,
) -> MessageResponse:
    await SubscriptionService(session).delete(user, endpoint_id, subscription_id)
    return MessageResponse(message="Subscription deleted")
