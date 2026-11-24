"""Process a single webhook delivery with locking and attempt recording."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.delivery import WebhookDelivery, WebhookDeliveryAttempt
from app.models.enums import AttemptOutcome, DeliveryStatus, EndpointStatus
from app.models.event_type import EventType
from app.services.delivery_http import execute_delivery_http
from app.services.delivery_retry import next_attempt_time

logger = get_logger(__name__)


class DeliveryProcessor:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()

    async def process(self, delivery_id: uuid.UUID) -> str:
        result = await self.session.execute(
            select(WebhookDelivery)
            .where(WebhookDelivery.id == delivery_id)
            .options(
                selectinload(WebhookDelivery.event),
                selectinload(WebhookDelivery.endpoint),
            )
            .with_for_update(skip_locked=True)
        )
        delivery = result.scalar_one_or_none()
        if delivery is None:
            logger.info("delivery_skip_locked_or_missing", delivery_id=str(delivery_id))
            return "skipped"

        if delivery.status in {
            DeliveryStatus.SUCCEEDED.value,
            DeliveryStatus.FAILED.value,
            DeliveryStatus.DEAD_LETTER.value,
        }:
            return delivery.status

        if delivery.status not in {
            DeliveryStatus.PENDING.value,
            DeliveryStatus.RETRYING.value,
            DeliveryStatus.PROCESSING.value,
        }:
            return delivery.status

        now = datetime.now(UTC)
        if (
            delivery.status == DeliveryStatus.RETRYING.value
            and delivery.next_attempt_at
            and delivery.next_attempt_at > now
        ):
            return "not_due"

        endpoint = delivery.endpoint
        event = delivery.event
        if endpoint is None or event is None:
            delivery.status = DeliveryStatus.FAILED.value
            delivery.last_error = "Missing event or endpoint"
            return DeliveryStatus.FAILED.value

        if endpoint.status != EndpointStatus.ACTIVE.value:
            delivery.status = DeliveryStatus.FAILED.value
            delivery.last_error = "Endpoint is inactive"
            return DeliveryStatus.FAILED.value

        delivery.status = DeliveryStatus.PROCESSING.value
        delivery.processing_started_at = now
        if delivery.enqueued_at is None:
            delivery.enqueued_at = now
        await self.session.flush()

        event_type_name = await self.session.scalar(
            select(EventType.name).where(
                EventType.id == event.event_type_id,
                EventType.organization_id == event.organization_id,
            )
        )

        attempt_number = delivery.attempt_count + 1
        attempt = WebhookDeliveryAttempt(
            organization_id=delivery.organization_id,
            delivery_id=delivery.id,
            attempt_number=attempt_number,
            started_at=now,
            outcome=AttemptOutcome.RETRYABLE_FAILURE.value,
        )
        self.session.add(attempt)
        await self.session.flush()

        http_result = await execute_delivery_http(
            delivery=delivery,
            event=event,
            endpoint=endpoint,
            settings=self.settings,
            event_type_name=event_type_name,
        )

        completed = datetime.now(UTC)
        attempt.completed_at = completed
        attempt.http_status = http_result.http_status
        attempt.response_summary = http_result.response_summary
        attempt.error_type = http_result.error_type
        attempt.error_message = http_result.error_message
        attempt.duration_ms = http_result.duration_ms
        attempt.outcome = http_result.outcome

        delivery.attempt_count = attempt_number
        delivery.last_attempt_at = completed
        delivery.last_http_status = http_result.http_status
        delivery.last_error = http_result.error_message
        delivery.response_summary = http_result.response_summary
        delivery.processing_started_at = None

        if http_result.outcome == AttemptOutcome.SUCCESS.value:
            delivery.status = DeliveryStatus.SUCCEEDED.value
            delivery.delivered_at = completed
            delivery.next_attempt_at = None
            await self.session.flush()
            logger.info("delivery_succeeded", delivery_id=str(delivery.id))
            return DeliveryStatus.SUCCEEDED.value

        if http_result.outcome == AttemptOutcome.PERMANENT_FAILURE.value:
            delivery.status = DeliveryStatus.FAILED.value
            delivery.next_attempt_at = None
            await self.session.flush()
            logger.info("delivery_permanent_failure", delivery_id=str(delivery.id))
            return DeliveryStatus.FAILED.value

        if attempt_number >= delivery.max_attempts:
            delivery.status = DeliveryStatus.DEAD_LETTER.value
            delivery.next_attempt_at = None
            await self.session.flush()
            logger.info("delivery_dead_letter", delivery_id=str(delivery.id))
            return DeliveryStatus.DEAD_LETTER.value

        delivery.status = DeliveryStatus.RETRYING.value
        delivery.next_attempt_at = next_attempt_time(
            attempt_number + 1,
            base_delay=self.settings.DELIVERY_RETRY_BASE_DELAY_SECONDS,
            multiplier=self.settings.DELIVERY_RETRY_MULTIPLIER,
            max_delay=self.settings.DELIVERY_RETRY_MAX_DELAY_SECONDS,
            retry_after_seconds=http_result.retry_after_seconds,
        )
        await self.session.flush()
        logger.info(
            "delivery_scheduled_retry",
            delivery_id=str(delivery.id),
            next_attempt_at=delivery.next_attempt_at.isoformat(),
        )
        return DeliveryStatus.RETRYING.value
