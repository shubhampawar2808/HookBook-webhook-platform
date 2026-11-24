"""Persisted published event — delivery is Prompt 3."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base, utc_now
from app.models.enums import EventStatus

if TYPE_CHECKING:
    from app.models.event_type import EventType
    from app.models.organization import Organization


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_events_event_id"),
        UniqueConstraint("id", "organization_id", name="uq_events_id_organization_id"),
        ForeignKeyConstraint(
            ["event_type_id", "organization_id"],
            ["event_types.id", "event_types.organization_id"],
            name="fk_events_event_type_org",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=EventStatus.ACCEPTED.value,
        server_default=EventStatus.ACCEPTED.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    organization: Mapped[Organization] = relationship(
        back_populates="events", overlaps="event_type,events"
    )
    event_type: Mapped[EventType] = relationship(
        back_populates="events", overlaps="organization,events"
    )

    @validates("status")
    def _validate_status(self, _key: str, value: str) -> str:
        allowed = {s.value for s in EventStatus}
        if value not in allowed:
            raise ValueError(f"Invalid event status: {value}")
        return value
