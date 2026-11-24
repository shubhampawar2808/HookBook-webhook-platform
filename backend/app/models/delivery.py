"""Webhook delivery and attempt history models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base, TimestampMixin, utc_now
from app.models.enums import AttemptOutcome, DeliveryStatus

if TYPE_CHECKING:
    from app.models.endpoint import WebhookEndpoint
    from app.models.event import Event
    from app.models.organization import Organization


class WebhookDelivery(Base, TimestampMixin):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "endpoint_id",
            name="uq_webhook_deliveries_event_id_endpoint_id",
        ),
        UniqueConstraint("id", "organization_id", name="uq_webhook_deliveries_id_organization_id"),
        ForeignKeyConstraint(
            ["event_id", "organization_id"],
            ["events.id", "events.organization_id"],
            name="fk_webhook_deliveries_event_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["endpoint_id", "organization_id"],
            ["webhook_endpoints.id", "webhook_endpoints.organization_id"],
            name="fk_webhook_deliveries_endpoint_org",
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
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    endpoint_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=DeliveryStatus.PENDING.value,
        server_default=DeliveryStatus.PENDING.value,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    response_summary: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enqueued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replay_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_replayed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    organization: Mapped[Organization] = relationship(viewonly=True)
    event: Mapped[Event] = relationship(
        primaryjoin="and_(WebhookDelivery.event_id==Event.id, "
        "WebhookDelivery.organization_id==Event.organization_id)",
        foreign_keys="[WebhookDelivery.event_id, WebhookDelivery.organization_id]",
        viewonly=True,
    )
    endpoint: Mapped[WebhookEndpoint] = relationship(
        primaryjoin="and_(WebhookDelivery.endpoint_id==WebhookEndpoint.id, "
        "WebhookDelivery.organization_id==WebhookEndpoint.organization_id)",
        foreign_keys="[WebhookDelivery.endpoint_id, WebhookDelivery.organization_id]",
        viewonly=True,
    )
    attempts: Mapped[list[WebhookDeliveryAttempt]] = relationship(
        back_populates="delivery",
        cascade="all, delete-orphan",
        order_by="WebhookDeliveryAttempt.attempt_number",
    )

    @validates("status")
    def _validate_status(self, _key: str, value: str) -> str:
        allowed = {s.value for s in DeliveryStatus}
        if value not in allowed:
            raise ValueError(f"Invalid delivery status: {value}")
        return value


class WebhookDeliveryAttempt(Base):
    __tablename__ = "webhook_delivery_attempts"
    __table_args__ = (
        UniqueConstraint(
            "delivery_id",
            "attempt_number",
            name="uq_webhook_delivery_attempts_delivery_attempt",
        ),
        ForeignKeyConstraint(
            ["delivery_id", "organization_id"],
            ["webhook_deliveries.id", "webhook_deliveries.organization_id"],
            name="fk_webhook_delivery_attempts_delivery_org",
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
    delivery_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_summary: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)

    delivery: Mapped[WebhookDelivery] = relationship(back_populates="attempts")

    @validates("outcome")
    def _validate_outcome(self, _key: str, value: str) -> str:
        allowed = {o.value for o in AttemptOutcome}
        if value not in allowed:
            raise ValueError(f"Invalid attempt outcome: {value}")
        return value
