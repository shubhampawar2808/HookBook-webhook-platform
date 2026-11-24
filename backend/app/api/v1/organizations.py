"""Organization endpoints — always scoped to the authenticated tenant."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.organization import OrganizationResponse, OrganizationUpdateRequest
from app.services.organization import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/me", response_model=OrganizationResponse)
async def get_my_organization(user: CurrentUser, session: DbSession) -> OrganizationResponse:
    org = await OrganizationService(session).get_mine(user)
    return OrganizationResponse.model_validate(org)


@router.patch("/me", response_model=OrganizationResponse)
async def update_my_organization(
    body: OrganizationUpdateRequest,
    user: CurrentUser,
    session: DbSession,
) -> OrganizationResponse:
    org = await OrganizationService(session).update_mine(user, body)
    return OrganizationResponse.model_validate(org)
