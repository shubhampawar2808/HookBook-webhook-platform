"""User model — belongs to exactly one organization."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base, TimestampMixin
from app.models.enums import UserRole, UserStatus

if TYPE_CHECKING:
    from app.models.organization import Organization


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_users_organization_id_email"),
        UniqueConstraint("id", "organization_id", name="uq_users_id_organization_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=UserStatus.ACTIVE.value,
        server_default=UserStatus.ACTIVE.value,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="users")

    @validates("role")
    def _validate_role(self, _key: str, value: str) -> str:
        allowed = {r.value for r in UserRole}
        if value not in allowed:
            raise ValueError(f"Invalid user role: {value}")
        return value

    @validates("status")
    def _validate_status(self, _key: str, value: str) -> str:
        allowed = {s.value for s in UserStatus}
        if value not in allowed:
            raise ValueError(f"Invalid user status: {value}")
        return value

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE.value
