"""Webhook endpoint schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel
from app.utils.validators import validate_webhook_url


class EndpointCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    url: str = Field(..., min_length=8, max_length=2048)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("url")
    @classmethod
    def _url(cls, value: str) -> str:
        return validate_webhook_url(value)


class EndpointUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    url: str | None = Field(default=None, min_length=8, max_length=2048)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, pattern="^(active|disabled)$")

    @field_validator("url")
    @classmethod
    def _url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_webhook_url(value)


class EndpointResponse(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    url: str
    description: str | None
    status: str
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class EndpointCreateResponse(EndpointResponse):
    signing_secret: str = Field(
        ...,
        description="Endpoint signing secret. Shown only once at creation.",
    )
