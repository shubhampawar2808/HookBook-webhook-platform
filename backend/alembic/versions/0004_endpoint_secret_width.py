"""Widen webhook_endpoints.signing_secret for encrypted-at-rest values.

Revision ID: 0004_endpoint_secret_width
Revises: 0003_webhook_deliveries
Create Date: 2026-11-24 16:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_endpoint_secret_width"
down_revision: Union[str, None] = "0003_webhook_deliveries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "webhook_endpoints",
        "signing_secret",
        existing_type=sa.String(length=128),
        type_=sa.String(length=512),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "webhook_endpoints",
        "signing_secret",
        existing_type=sa.String(length=512),
        type_=sa.String(length=128),
        existing_nullable=False,
    )
