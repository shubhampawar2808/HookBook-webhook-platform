"""Organization (tenant) model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base, TimestampMixin
from app.models.enums import OrganizationStatus

if TYPE_CHECKING:
    from app.models.api_key import APIKey
    from app.models.endpoint import WebhookEndpoint
    from app.models.event import Event
    from app.models.event_type import EventType
    from app.models.subscription import EndpointSubscription
    from app.models.user import User


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"
    __table_args__ = (UniqueConstraint("slug", name="uq_organizations_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=OrganizationStatus.ACTIVE.value,
        server_default=OrganizationStatus.ACTIVE.value,
    )

    users: Mapped[list[User]] = relationship(back_populates="organization")
    api_keys: Mapped[list[APIKey]] = relationship(back_populates="organization")
    endpoints: Mapped[list[WebhookEndpoint]] = relationship(back_populates="organization")
    event_types: Mapped[list[EventType]] = relationship(back_populates="organization")
    events: Mapped[list[Event]] = relationship(
        back_populates="organization", overlaps="event_type,events"
    )
    subscriptions: Mapped[list[EndpointSubscription]] = relationship(
        back_populates="organization",
        overlaps="endpoint,event_type,subscriptions",
    )

    @validates("status")
    def _validate_status(self, _key: str, value: str) -> str:
        allowed = {s.value for s in OrganizationStatus}
        if value not in allowed:
            raise ValueError(f"Invalid organization status: {value}")
        return value

    @property
    def is_active(self) -> bool:
        return self.status == OrganizationStatus.ACTIVE.value
