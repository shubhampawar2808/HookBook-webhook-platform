"""Event type endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import PageResponse
from app.schemas.event_type import EventTypeCreateRequest, EventTypeResponse
from app.services.event_type import EventTypeService
from app.utils.pagination import PaginationParams

router = APIRouter(prefix="/event-types", tags=["event-types"])


@router.post(
    "",
    response_model=EventTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_event_type(
    body: EventTypeCreateRequest,
    user: CurrentUser,
    session: DbSession,
) -> EventTypeResponse:
    item = await EventTypeService(session).create(user, body)
    return EventTypeResponse.model_validate(item)


@router.get("", response_model=PageResponse[EventTypeResponse])
async def list_event_types(
    user: CurrentUser,
    session: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PageResponse[EventTypeResponse]:
    result = await EventTypeService(session).list(
        user, PaginationParams(page=page, page_size=page_size)
    )
    return PageResponse(
        items=[EventTypeResponse.model_validate(i) for i in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )


@router.get("/{event_type_id}", response_model=EventTypeResponse)
async def get_event_type(
    event_type_id: uuid.UUID,
    user: CurrentUser,
    session: DbSession,
) -> EventTypeResponse:
    item = await EventTypeService(session).get(user, event_type_id)
    return EventTypeResponse.model_validate(item)
