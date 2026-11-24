"""Webhook deliveries, attempts, endpoint secrets, subscription status.

Revision ID: 0003_webhook_deliveries
Revises: 0002_domain_tables
Create Date: 2026-03-24 14:00:00.000000

"""

from __future__ import annotations

import secrets
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_webhook_deliveries"
down_revision: Union[str, None] = "0002_domain_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "webhook_endpoints",
        sa.Column("signing_secret", sa.String(length=128), nullable=True),
    )
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM webhook_endpoints")).fetchall()
    for row in rows:
        conn.execute(
            sa.text(
                "UPDATE webhook_endpoints SET signing_secret = :secret WHERE id = :id"
            ),
            {"secret": secrets.token_urlsafe(32), "id": row[0]},
        )
    op.alter_column("webhook_endpoints", "signing_secret", nullable=False)

    op.add_column(
        "endpoint_subscriptions",
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="active",
            nullable=False,
        ),
    )

    op.create_unique_constraint(
        "uq_events_id_organization_id", "events", ["id", "organization_id"]
    )

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("endpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_http_status", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.String(length=1024), nullable=True),
        sa.Column("response_summary", sa.String(length=1024), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enqueued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replay_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_replayed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["endpoint_id", "organization_id"],
            ["webhook_endpoints.id", "webhook_endpoints.organization_id"],
            name="fk_webhook_deliveries_endpoint_org",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "organization_id"],
            ["events.id", "events.organization_id"],
            name="fk_webhook_deliveries_event_org",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_webhook_deliveries_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_webhook_deliveries")),
        sa.UniqueConstraint(
            "event_id",
            "endpoint_id",
            name="uq_webhook_deliveries_event_id_endpoint_id",
        ),
        sa.UniqueConstraint(
            "id",
            "organization_id",
            name="uq_webhook_deliveries_id_organization_id",
        ),
    )
    op.create_index(
        op.f("ix_webhook_deliveries_endpoint_id"),
        "webhook_deliveries",
        ["endpoint_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_webhook_deliveries_event_id"),
        "webhook_deliveries",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_webhook_deliveries_idempotency_key"),
        "webhook_deliveries",
        ["idempotency_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_webhook_deliveries_next_attempt_at"),
        "webhook_deliveries",
        ["next_attempt_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_webhook_deliveries_organization_id"),
        "webhook_deliveries",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_webhook_deliveries_status"),
        "webhook_deliveries",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_webhook_deliveries_status_next_attempt",
        "webhook_deliveries",
        ["status", "next_attempt_at"],
        unique=False,
    )

    op.create_table(
        "webhook_delivery_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("delivery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("response_summary", sa.String(length=1024), nullable=True),
        sa.Column("error_type", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["delivery_id", "organization_id"],
            ["webhook_deliveries.id", "webhook_deliveries.organization_id"],
            name="fk_webhook_delivery_attempts_delivery_org",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_webhook_delivery_attempts_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_webhook_delivery_attempts")),
        sa.UniqueConstraint(
            "delivery_id",
            "attempt_number",
            name="uq_webhook_delivery_attempts_delivery_attempt",
        ),
    )
    op.create_index(
        op.f("ix_webhook_delivery_attempts_delivery_id"),
        "webhook_delivery_attempts",
        ["delivery_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_webhook_delivery_attempts_organization_id"),
        "webhook_delivery_attempts",
        ["organization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("webhook_delivery_attempts")
    op.drop_table("webhook_deliveries")
    op.drop_constraint("uq_events_id_organization_id", "events", type_="unique")
    op.drop_column("endpoint_subscriptions", "status")
    op.drop_column("webhook_endpoints", "signing_secret")
