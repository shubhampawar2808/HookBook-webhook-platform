"""Foundation revision — no domain tables yet.

Revision ID: 0001_foundation
Revises:
Create Date: 2026-03-24 00:00:00.000000

Domain tables (organizations, users, endpoints, events, deliveries, etc.)
are intentionally deferred to later phases. This revision establishes the
Alembic chain and verifies async migration tooling.
"""

from __future__ import annotations

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "0001_foundation"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No schema objects in the foundation phase.
    pass


def downgrade() -> None:
    pass
