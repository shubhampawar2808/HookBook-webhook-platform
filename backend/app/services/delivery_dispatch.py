"""Create delivery records for matching subscriptions and enqueue Celery jobs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.delivery import WebhookDelivery
from app.models.endpoint import WebhookEndpoint
from app.models.enums import DeliveryStatus, EndpointStatus, SubscriptionStatus
from app.models.event import Event
from app.models.subscription import EndpointSubscription

logger = get_logger(__name__)


def build_idempotency_key(event_id: uuid.UUID, endpoint_id: uuid.UUID) -> str:
    return f"del_{event_id.hex}_{endpoint_id.hex}"


class DeliveryDispatchService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()

    async def create_deliveries_for_event(self, event: Event) -> list[uuid.UUID]:
        """Idempotently create PENDING deliveries for active matching subscriptions."""
        stmt = (
            select(EndpointSubscription, WebhookEndpoint)
            .join(
                WebhookEndpoint,
                (WebhookEndpoint.id == EndpointSubscription.endpoint_id)
                & (WebhookEndpoint.organization_id == EndpointSubscription.organization_id),
            )
            .where(
                EndpointSubscription.organization_id == event.organization_id,
                EndpointSubscription.event_type_id == event.event_type_id,
                EndpointSubscription.status == SubscriptionStatus.ACTIVE.value,
                WebhookEndpoint.status == EndpointStatus.ACTIVE.value,
            )
        )
        rows = (await self.session.execute(stmt)).all()
        delivery_ids: list[uuid.UUID] = []
        now = datetime.now(UTC)

        for _subscription, endpoint in rows:
            delivery_id = uuid.uuid4()
            idem = build_idempotency_key(event.id, endpoint.id)
            insert_stmt = (
                insert(WebhookDelivery)
                .values(
                    id=delivery_id,
                    organization_id=event.organization_id,
                    event_id=event.id,
                    endpoint_id=endpoint.id,
                    status=DeliveryStatus.PENDING.value,
                    attempt_count=0,
                    max_attempts=self.settings.DELIVERY_MAX_ATTEMPTS,
                    next_attempt_at=now,
                    idempotency_key=idem,
                    created_at=now,
                    updated_at=now,
                    replay_count=0,
                )
                .on_conflict_do_nothing(constraint="uq_webhook_deliveries_event_id_endpoint_id")
                .returning(WebhookDelivery.id)
            )
            result = await self.session.execute(insert_stmt)
            created_id = result.scalar_one_or_none()
            if created_id is not None:
                delivery_ids.append(created_id)
            else:
                existing = await self.session.scalar(
                    select(WebhookDelivery.id).where(
                        WebhookDelivery.event_id == event.id,
                        WebhookDelivery.endpoint_id == endpoint.id,
                    )
                )
                if existing is not None:
                    delivery_ids.append(existing)

        await self.session.flush()
        logger.info(
            "deliveries_created",
            event_id=str(event.id),
            count=len(delivery_ids),
        )
        return delivery_ids


def enqueue_delivery_jobs(delivery_ids: list[str | uuid.UUID]) -> dict[str, int]:
    """Enqueue Celery jobs after DB commit. Returns counts of queued/failed.

    ``enqueued_at`` is intentionally NOT set here. It is set when a worker
    claims the row (PROCESSING). That keeps Beat recovery able to re-dispatch
    PENDING rows whose broker publish failed or whose Celery message was lost
    (``status=PENDING`` and ``enqueued_at IS NULL``).

    Callers must commit delivery rows before invoking this function.
    """
    from app.workers.tasks import process_webhook_delivery

    queued = 0
    failed = 0
    for delivery_id in delivery_ids:
        try:
            process_webhook_delivery.delay(str(delivery_id))
            queued += 1
        except Exception as exc:
            failed += 1
            logger.warning(
                "delivery_enqueue_failed",
                delivery_id=str(delivery_id),
                error=type(exc).__name__,
            )
    if failed:
        logger.error("delivery_enqueue_partial_failure", queued=queued, failed=failed)
    elif queued:
        logger.info("delivery_enqueue_ok", queued=queued)
    return {"queued": queued, "failed": failed}
