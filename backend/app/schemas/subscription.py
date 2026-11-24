"""Subscription schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class SubscriptionCreateRequest(BaseModel):
    event_type_id: uuid.UUID


class SubscriptionResponse(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    endpoint_id: uuid.UUID
    event_type_id: uuid.UUID
    status: str
    created_at: datetime
