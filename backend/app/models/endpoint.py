"""Webhook endpoint destination model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, ForeignKeyConstraint, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base, TimestampMixin
from app.models.enums import EndpointStatus

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.subscription import EndpointSubscription


class WebhookEndpoint(Base, TimestampMixin):
    __tablename__ = "webhook_endpoints"
    __table_args__ = (
        UniqueConstraint("id", "organization_id", name="uq_webhook_endpoints_id_organization_id"),
        ForeignKeyConstraint(
            ["created_by", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_webhook_endpoints_created_by_org",
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
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    signing_secret: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=EndpointStatus.ACTIVE.value,
        server_default=EndpointStatus.ACTIVE.value,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="endpoints")
    subscriptions: Mapped[list[EndpointSubscription]] = relationship(
        back_populates="endpoint", cascade="all, delete-orphan"
    )

    @validates("status")
    def _validate_status(self, _key: str, value: str) -> str:
        allowed = {s.value for s in EndpointStatus}
        if value not in allowed:
            raise ValueError(f"Invalid endpoint status: {value}")
        return value
