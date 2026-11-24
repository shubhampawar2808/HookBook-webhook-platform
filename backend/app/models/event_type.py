"""Event type taxonomy within an organization."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.organization import Organization
    from app.models.subscription import EndpointSubscription


class EventType(Base):
    __tablename__ = "event_types"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_event_types_organization_id_name"),
        UniqueConstraint("id", "organization_id", name="uq_event_types_id_organization_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    organization: Mapped[Organization] = relationship(back_populates="event_types")
    events: Mapped[list[Event]] = relationship(
        back_populates="event_type", overlaps="organization,events"
    )
    subscriptions: Mapped[list[EndpointSubscription]] = relationship(
        back_populates="event_type",
        overlaps="endpoint,organization,subscriptions",
    )
