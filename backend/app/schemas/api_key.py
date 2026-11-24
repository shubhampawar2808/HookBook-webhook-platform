"""API key schemas — raw secret only on create/rotate responses."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class APIKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    expires_at: datetime | None = None


class APIKeyResponse(ORMModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    status: str
    last_used_at: datetime | None
    expires_at: datetime | None
    created_by: uuid.UUID
    created_at: datetime
    revoked_at: datetime | None


class APIKeyCreateResponse(APIKeyResponse):
    """Includes the raw key exactly once."""

    api_key: str = Field(
        ...,
        description="Full API key. Shown only once; store it securely.",
    )
