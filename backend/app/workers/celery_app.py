"""Celery application configuration for HookForge."""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "hookforge",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "recover-deliveries": {
            "task": "hookforge.recover_deliveries",
            "schedule": float(settings.DELIVERY_RECOVERY_INTERVAL_SECONDS),
        },
    },
)

celery_app.autodiscover_tasks(["app.workers"])

from app.workers import tasks as _tasks  # noqa: E402, F401
