"""Recover stale / due / never-enqueued deliveries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.repositories.delivery import DeliveryRepository
from app.services.delivery_dispatch import enqueue_delivery_jobs

logger = get_logger(__name__)


class DeliveryRecoveryService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repo = DeliveryRepository(session)

    async def recover_and_enqueue(self) -> dict[str, int]:
        now = datetime.now(UTC)
        stale_before = now - timedelta(seconds=self.settings.DELIVERY_STALE_PROCESSING_SECONDS)
        stmt = self.repo.due_recoverable_query(now=now, stale_before=stale_before).limit(
            self.settings.DELIVERY_RECOVERY_BATCH_SIZE
        )
        result = await self.session.execute(stmt)
        ids = [row[0] for row in result.all()]
        if not ids:
            return {"found": 0, "queued": 0, "failed": 0}

        enqueue_result = enqueue_delivery_jobs(ids)
        logger.info(
            "delivery_recovery_batch",
            found=len(ids),
            queued=enqueue_result["queued"],
            failed=enqueue_result["failed"],
        )
        return {
            "found": len(ids),
            "queued": enqueue_result["queued"],
            "failed": enqueue_result["failed"],
        }
