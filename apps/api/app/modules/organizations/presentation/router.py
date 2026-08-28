import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.dependencies import get_active_org_context, get_current_user, get_db
from apps.api.app.modules.identity.infrastructure.orm import UserORM
from apps.api.app.modules.organizations.application.accept_invitation_use_case import (
    AcceptInvitationUseCase,
)
from apps.api.app.modules.organizations.application.bootstrap_organization_use_case import (
    BootstrapOrganizationUseCase,
)
from apps.api.app.modules.organizations.application.invite_member_use_case import (
    InviteMemberUseCase,
)
from apps.api.app.modules.organizations.application.manage_membership_use_case import (
    ManageMembershipUseCase,
)
from apps.api.app.modules.organizations.application.manage_organization_use_case import (
    ManageOrganizationUseCase,
)

org_router = APIRouter(prefix="/organizations", tags=["Organizations & Context"])
invitation_router = APIRouter(prefix="/organization-invitations", tags=["Organization Invitations"])


# --- Schemas ---

class BootstrapOrgRequest(BaseModel):
    name: str
    slug: str


class UpdateOrgRequest(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role_name: str


class AcceptOrgInvitationRequest(BaseModel):
    token: str


class UpdateMemberRoleRequest(BaseModel):
    role_name: str


class UpdateMemberStatusRequest(BaseModel):
    status: str


# --- Endpoints ---

@org_router.post("", status_code=status.HTTP_201_CREATED)
async def bootstrap_organization(
    req: BootstrapOrgRequest,
    request: Request,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request.client else None
    use_case = BootstrapOrganizationUseCase(db)
    return await use_case.execute(user=current_user, name=req.name, slug=req.slug, ip_address=ip_address)


@org_router.get("/{organization_id}", status_code=status.HTTP_200_OK)
async def get_organization(
    organization_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageOrganizationUseCase(db)
    return await use_case.get_organization(ctx)


@org_router.patch("/{organization_id}", status_code=status.HTTP_200_OK)
async def update_organization(
    organization_id: uuid.UUID,
    req: UpdateOrgRequest,
    request: Request,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request.client else None
    use_case = ManageOrganizationUseCase(db)
    return await use_case.update_organization(ctx, name=req.name, slug=req.slug, ip_address=ip_address)


@org_router.get("/{organization_id}/members", status_code=status.HTTP_200_OK)
async def list_members(
    organization_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageOrganizationUseCase(db)
    return await use_case.list_members(ctx)


@org_router.post("/{organization_id}/invitations", status_code=status.HTTP_201_CREATED)
async def invite_member(
    organization_id: uuid.UUID,
    req: InviteMemberRequest,
    request: Request,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request.client else None
    use_case = InviteMemberUseCase(db)
    return await use_case.execute(ctx, target_email=req.email, role_name=req.role_name, ip_address=ip_address)


@invitation_router.post("/accept", status_code=status.HTTP_200_OK)
async def accept_invitation(
    req: AcceptOrgInvitationRequest,
    request: Request,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request.client else None
    use_case = AcceptInvitationUseCase(db)
    return await use_case.execute(user=current_user, raw_token=req.token, ip_address=ip_address)


@org_router.patch("/{organization_id}/members/{membership_id}/role", status_code=status.HTTP_200_OK)
async def update_member_role(
    organization_id: uuid.UUID,
    membership_id: uuid.UUID,
    req: UpdateMemberRoleRequest,
    request: Request,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request.client else None
    use_case = ManageMembershipUseCase(db)
    return await use_case.update_member_role(ctx, membership_id=membership_id, new_role_name=req.role_name, ip_address=ip_address)


@org_router.post("/{organization_id}/members/{membership_id}/status", status_code=status.HTTP_200_OK)
async def update_member_status(
    organization_id: uuid.UUID,
    membership_id: uuid.UUID,
    req: UpdateMemberStatusRequest,
    request: Request,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ip_address = request.client.host if request.client else None
    use_case = ManageMembershipUseCase(db)
    return await use_case.update_member_status(ctx, membership_id=membership_id, new_status=req.status, ip_address=ip_address)
