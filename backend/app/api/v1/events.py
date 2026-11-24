"""Event publishing — API-key authenticated with async delivery dispatch."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import AppSettings, CurrentAPIKey, DbSession
from app.core.logging import get_logger
from app.schemas.event import EventPublishRequest, EventResponse
from app.services.delivery_dispatch import enqueue_delivery_jobs
from app.services.event import EventService

router = APIRouter(prefix="/events", tags=["events"])
logger = get_logger(__name__)


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Publish an event",
    description=(
        "Persists an event and creates delivery records for matching active subscriptions. "
        "HTTP webhook delivery is performed asynchronously by Celery workers."
    ),
)
async def publish_event(
    body: EventPublishRequest,
    api_key: CurrentAPIKey,
    session: DbSession,
    settings: AppSettings,
) -> EventResponse:
    event, delivery_ids = await EventService(session, settings).publish(api_key, body)
    if delivery_ids:
        # Commit before broker publish so workers never race an uncommitted row.
        # If Redis/broker fails after commit, rows stay PENDING (enqueued_at NULL)
        # and Celery Beat recovery re-dispatches them.
        await session.commit()
        result = enqueue_delivery_jobs([str(i) for i in delivery_ids])
        if result["failed"]:
            logger.error(
                "post_commit_enqueue_failed",
                queued=result["queued"],
                failed=result["failed"],
                event_id=str(event.id),
            )
        delivery_status = "accepted"
    else:
        delivery_status = "none"

    response = EventResponse.model_validate(event)
    response.delivery = delivery_status
    response.delivery_count = len(delivery_ids)
    return response
