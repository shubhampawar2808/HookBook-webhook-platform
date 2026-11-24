"""Delivery management schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class DeliveryResponse(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    event_id: uuid.UUID
    endpoint_id: uuid.UUID
    status: str
    attempt_count: int
    max_attempts: int
    next_attempt_at: datetime | None
    last_attempt_at: datetime | None
    last_http_status: int | None
    last_error: str | None
    response_summary: str | None
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
    delivered_at: datetime | None
    replay_count: int
    last_replayed_at: datetime | None


class DeliveryAttemptResponse(ORMModel):
    id: uuid.UUID
    delivery_id: uuid.UUID
    attempt_number: int
    started_at: datetime
    completed_at: datetime | None
    http_status: int | None
    response_summary: str | None
    error_type: str | None
    error_message: str | None
    duration_ms: int | None
    outcome: str


class DeliveryReplayResponse(BaseModel):
    delivery: DeliveryResponse
    message: str = Field(default="Delivery queued for replay")
