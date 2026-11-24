"""Event publishing schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class EventPublishRequest(BaseModel):
    event_type: str = Field(
        ...,
        min_length=2,
        max_length=120,
        description="Event type name within the API key's organization",
    )
    payload: dict[str, Any] = Field(default_factory=dict)


class EventResponse(ORMModel):
    id: uuid.UUID
    event_id: str
    organization_id: uuid.UUID
    event_type_id: uuid.UUID
    payload: dict[str, Any]
    status: str
    created_at: datetime
    delivery: str = Field(
        default="accepted",
        description=(
            "Delivery dispatch status: accepted (records created; workers process async), "
            "none (no matching subscriptions), or enqueue_deferred (broker unavailable)."
        ),
    )
    delivery_count: int = 0
