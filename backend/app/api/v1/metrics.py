"""Minimal Prometheus text exposition for delivery operational signals."""

from __future__ import annotations

from fastapi import APIRouter, Response
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models.delivery import WebhookDelivery
from app.models.enums import DeliveryStatus

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics(user: CurrentUser, session: DbSession) -> Response:
    """Org-scoped delivery counters in Prometheus text format."""
    org_id = user.organization_id
    rows = (
        await session.execute(
            select(WebhookDelivery.status, func.count())
            .where(WebhookDelivery.organization_id == org_id)
            .group_by(WebhookDelivery.status)
        )
    ).all()
    counts = {status: int(count) for status, count in rows}
    lines = [
        "# HELP hookforge_deliveries_total Deliveries by status for the current organization",
        "# TYPE hookforge_deliveries_total gauge",
    ]
    for status in DeliveryStatus:
        value = counts.get(status.value, 0)
        lines.append(
            f'hookforge_deliveries_total{{status="{status.value}",'
            f'organization_id="{org_id}"}} {value}'
        )
    body = "\n".join(lines) + "\n"
    return Response(content=body, media_type="text/plain; version=0.0.4")
