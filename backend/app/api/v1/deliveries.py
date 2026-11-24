"""Delivery listing, detail, attempts, dead-letter, and replay APIs."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Query, status

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.core.logging import get_logger
from app.schemas.common import PageResponse
from app.schemas.delivery import (
    DeliveryAttemptResponse,
    DeliveryReplayResponse,
    DeliveryResponse,
)
from app.services.delivery_management import DeliveryManagementService
from app.utils.pagination import PaginationParams

logger = get_logger(__name__)

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


@router.get("", response_model=PageResponse[DeliveryResponse])
async def list_deliveries(
    user: CurrentUser,
    session: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    event_id: uuid.UUID | None = None,
    endpoint_id: uuid.UUID | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> PageResponse[DeliveryResponse]:
    result = await DeliveryManagementService(session).list_deliveries(
        user,
        PaginationParams(page=page, page_size=page_size),
        status=status_filter,
        event_id=event_id,
        endpoint_id=endpoint_id,
        created_from=created_from,
        created_to=created_to,
    )
    return PageResponse(
        items=[DeliveryResponse.model_validate(i) for i in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )


@router.get("/dead-letter", response_model=PageResponse[DeliveryResponse])
async def list_dead_letter(
    user: CurrentUser,
    session: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PageResponse[DeliveryResponse]:
    result = await DeliveryManagementService(session).list_deliveries(
        user,
        PaginationParams(page=page, page_size=page_size),
        dead_letter_only=True,
    )
    return PageResponse(
        items=[DeliveryResponse.model_validate(i) for i in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )


@router.get("/{delivery_id}", response_model=DeliveryResponse)
async def get_delivery(
    delivery_id: uuid.UUID,
    user: CurrentUser,
    session: DbSession,
) -> DeliveryResponse:
    delivery = await DeliveryManagementService(session).get_delivery(user, delivery_id)
    return DeliveryResponse.model_validate(delivery)


@router.get(
    "/{delivery_id}/attempts",
    response_model=list[DeliveryAttemptResponse],
)
async def list_attempts(
    delivery_id: uuid.UUID,
    user: CurrentUser,
    session: DbSession,
) -> list[DeliveryAttemptResponse]:
    attempts = await DeliveryManagementService(session).list_attempts(user, delivery_id)
    return [DeliveryAttemptResponse.model_validate(a) for a in attempts]


@router.post(
    "/{delivery_id}/replay",
    response_model=DeliveryReplayResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def replay_delivery(
    delivery_id: uuid.UUID,
    user: CurrentUser,
    session: DbSession,
    settings: AppSettings,
) -> DeliveryReplayResponse:
    service = DeliveryManagementService(session, settings)
    delivery = await service.replay(user, delivery_id)
    # Commit before broker publish; Beat recovers PENDING if enqueue fails.
    await session.commit()
    result = service.enqueue_replay(delivery.id)
    if result["failed"]:
        logger.error(
            "replay_enqueue_failed",
            delivery_id=str(delivery.id),
            queued=result["queued"],
            failed=result["failed"],
        )
    return DeliveryReplayResponse(delivery=DeliveryResponse.model_validate(delivery))
