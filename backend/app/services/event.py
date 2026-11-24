"""Event publishing service with delivery dispatch (Prompt 3)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.core.security import generate_public_event_id
from app.models.api_key import APIKey
from app.models.enums import EventStatus
from app.models.event import Event
from app.repositories.event import EventRepository
from app.repositories.event_type import EventTypeRepository
from app.schemas.event import EventPublishRequest
from app.services.delivery_dispatch import DeliveryDispatchService
from app.utils.validators import validate_event_type_name


class EventService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.events = EventRepository(session)
        self.event_types = EventTypeRepository(session)
        self.dispatch = DeliveryDispatchService(session, self.settings)

    async def publish(
        self, api_key: APIKey, data: EventPublishRequest
    ) -> tuple[Event, list[uuid.UUID]]:
        try:
            name = validate_event_type_name(data.event_type)
        except ValueError as exc:
            raise NotFoundError("Event type not found") from exc

        event_type = await self.event_types.get_by_name_for_org(name, api_key.organization_id)
        if event_type is None:
            raise NotFoundError("Event type not found")

        payload: dict[str, Any] = data.payload
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a JSON object")

        raw = json_size_check(payload, self.settings.DELIVERY_MAX_PAYLOAD_BYTES)

        event = Event(
            organization_id=api_key.organization_id,
            event_type_id=event_type.id,
            event_id=generate_public_event_id(),
            payload=payload,
            status=EventStatus.ACCEPTED.value,
        )
        event = await self.events.add(event)
        delivery_ids = await self.dispatch.create_deliveries_for_event(event)
        _ = raw
        return event, delivery_ids


def json_size_check(payload: dict[str, Any], max_bytes: int) -> bytes:
    import json

    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(raw) > max_bytes:
        from fastapi import status

        from app.core.exceptions import HookForgeError

        raise HookForgeError(
            "Event payload exceeds maximum allowed size",
            code="payload_too_large",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )
    return raw
