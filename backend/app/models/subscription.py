"""Endpoint ↔ event type subscription with same-org enforcement."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base, utc_now
from app.models.enums import SubscriptionStatus

if TYPE_CHECKING:
    from app.models.endpoint import WebhookEndpoint
    from app.models.event_type import EventType
    from app.models.organization import Organization


class EndpointSubscription(Base):
    __tablename__ = "endpoint_subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "endpoint_id",
            "event_type_id",
            name="uq_endpoint_subscriptions_endpoint_event_type",
        ),
        ForeignKeyConstraint(
            ["endpoint_id", "organization_id"],
            ["webhook_endpoints.id", "webhook_endpoints.organization_id"],
            name="fk_endpoint_subscriptions_endpoint_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["event_type_id", "organization_id"],
            ["event_types.id", "event_types.organization_id"],
            name="fk_endpoint_subscriptions_event_type_org",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endpoint_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    event_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SubscriptionStatus.ACTIVE.value,
        server_default=SubscriptionStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    organization: Mapped[Organization] = relationship(
        back_populates="subscriptions",
        overlaps="endpoint,event_type,subscriptions",
    )
    endpoint: Mapped[WebhookEndpoint] = relationship(
        back_populates="subscriptions",
        overlaps="organization,event_type,subscriptions",
    )
    event_type: Mapped[EventType] = relationship(
        back_populates="subscriptions",
        overlaps="endpoint,organization,subscriptions",
    )

    @validates("status")
    def _validate_status(self, _key: str, value: str) -> str:
        allowed = {s.value for s in SubscriptionStatus}
        if value not in allowed:
            raise ValueError(f"Invalid subscription status: {value}")
        return value
