from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.authorization.permissions import Permissions
from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.identity.infrastructure.orm import UserORM
from apps.api.app.modules.organizations.infrastructure.orm import (
    OrganizationMembershipORM,
    OrganizationORM,
    RoleORM,
)


class ManageOrganizationUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_organization(self, ctx: AuthorizationContext) -> Dict[str, Any]:
        org = ctx.active_organization
        if not org:
            raise DomainException("No active organization context", code="AUTH_ORGANIZATION_REQUIRED")

        return {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "account_status": org.account_status,
            "created_at": org.created_at.isoformat(),
            "updated_at": org.updated_at.isoformat(),
        }

    async def update_organization(
        self,
        ctx: AuthorizationContext,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        ip_address: str = None
    ) -> Dict[str, Any]:
        if not ctx.has_permission(Permissions.ORGANIZATION_UPDATE):
            raise DomainException("Permission organization:update required", code="AUTH_PERMISSION_DENIED")

        org = ctx.active_organization
        changes = {}

        if name and name.strip() != org.name:
            changes["old_name"] = org.name
            org.name = name.strip()
            changes["new_name"] = org.name

        if slug and slug.strip().lower() != org.slug:
            new_slug = slug.strip().lower()
            existing_res = await self.db.execute(
                select(OrganizationORM).where(OrganizationORM.slug == new_slug, OrganizationORM.id != org.id)
            )
            if existing_res.scalar_one_or_none():
                raise DomainException("Organization slug is already in use", code="ORGANIZATION_SLUG_EXISTS")

            changes["old_slug"] = org.slug
            org.slug = new_slug
            changes["new_slug"] = org.slug

        if changes:
            audit = AuditLogORM(
                organization_id=org.id,
                actor_user_id=ctx.user.id,
                actor_type="USER",
                action="organization.updated",
                resource_type="Organization",
                resource_id=org.id,
                ip_address=ip_address,
                metadata_json=changes,
            )
            self.db.add(audit)
            await self.db.commit()

        return {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "account_status": org.account_status,
            "updated_at": org.updated_at.isoformat(),
        }

    async def list_members(self, ctx: AuthorizationContext) -> List[Dict[str, Any]]:
        if not ctx.has_permission(Permissions.MEMBER_READ):
            raise DomainException("Permission member:read required", code="AUTH_PERMISSION_DENIED")

        org_id = ctx.active_organization.id
        stmt = (
            select(OrganizationMembershipORM, UserORM, RoleORM)
            .join(UserORM, OrganizationMembershipORM.user_id == UserORM.id)
            .join(RoleORM, OrganizationMembershipORM.role_id == RoleORM.id)
            .where(OrganizationMembershipORM.organization_id == org_id)
        )
        res = await self.db.execute(stmt)
        rows = res.all()

        return [
            {
                "membership_id": str(mem.id),
                "user_id": str(user.id),
                "email": user.email,
                "role": role.name,
                "role_id": str(role.id),
                "status": mem.status,
                "joined_at": mem.created_at.isoformat(),
            }
            for mem, user, role in rows
        ]
