"""Registered Celery tasks."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from app.workers.celery_app import celery_app


def _run(coro):
    return asyncio.run(coro)


@celery_app.task(name="hookforge.health_check", bind=True)
def health_check_task(self) -> dict[str, str]:
    """Minimal task used to verify Celery worker registration and broker connectivity."""
    return {
        "status": "ok",
        "task_id": self.request.id or "",
        "checked_at": datetime.now(UTC).isoformat(),
    }


@celery_app.task(
    name="hookforge.process_webhook_delivery",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_webhook_delivery(self, delivery_id: str) -> dict[str, str]:
    """Process one webhook delivery using PostgreSQL as source of truth."""

    async def _inner() -> dict[str, str]:
        from app.db.worker_session import worker_session
        from app.services.delivery_processor import DeliveryProcessor

        async with worker_session() as session:
            status = await DeliveryProcessor(session).process(uuid.UUID(delivery_id))
            return {"delivery_id": delivery_id, "status": status}

    return _run(_inner())


@celery_app.task(name="hookforge.recover_deliveries", bind=True)
def recover_deliveries(self) -> dict[str, int]:
    """Find due/stale/unenqueued deliveries and re-dispatch Celery jobs."""

    async def _inner() -> dict[str, int]:
        from app.db.worker_session import worker_session
        from app.services.delivery_recovery import DeliveryRecoveryService

        async with worker_session() as session:
            return await DeliveryRecoveryService(session).recover_and_enqueue()

    return _run(_inner())
