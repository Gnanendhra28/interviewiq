import uuid
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.authorization.permissions import Permissions
from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.organizations.infrastructure.orm import OrganizationMembershipORM, RoleORM


class ManageMembershipUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_member_role(
        self,
        ctx: AuthorizationContext,
        membership_id: uuid.UUID,
        new_role_name: str,
        ip_address: str = None
    ) -> Dict[str, Any]:
        if not ctx.has_permission(Permissions.ROLE_ASSIGN):
            raise DomainException("Permission role:assign required", code="AUTH_PERMISSION_DENIED")

        org_id = ctx.active_organization.id

        # 1. Fetch Target Membership
        mem_res = await self.db.execute(
            select(OrganizationMembershipORM).where(
                OrganizationMembershipORM.id == membership_id,
                OrganizationMembershipORM.organization_id == org_id
            )
        )
        mem = mem_res.scalar_one_or_none()
        if not mem:
            raise DomainException("Organization membership not found", code="MEMBERSHIP_NOT_FOUND")

        # 2. Privilege Escalation Prevention
        if new_role_name == "ORGANIZATION_ADMIN" and ctx.role and ctx.role.name != "ORGANIZATION_ADMIN" and not ctx.user.is_super_admin:
            raise DomainException("Privilege escalation: Only organization admins can assign administrator privileges", code="PRIVILEGE_ESCALATION_DENIED")

        # 3. Resolve New Role
        role_res = await self.db.execute(select(RoleORM).where(RoleORM.name == new_role_name))
        new_role = role_res.scalar_one_or_none()
        if not new_role:
            raise DomainException(f"Role {new_role_name} does not exist", code="ROLE_NOT_FOUND")

        old_role_res = await self.db.execute(select(RoleORM).where(RoleORM.id == mem.role_id))
        old_role = old_role_res.scalar_one_or_none()

        mem.role_id = new_role.id

        audit = AuditLogORM(
            organization_id=org_id,
            actor_user_id=ctx.user.id,
            actor_type="USER",
            action="membership.role_assigned",
            resource_type="OrganizationMembership",
            resource_id=mem.id,
            ip_address=ip_address,
            metadata_json={
                "target_user_id": str(mem.user_id),
                "old_role": old_role.name if old_role else None,
                "new_role": new_role.name
            },
        )
        self.db.add(audit)
        await self.db.commit()

        return {
            "membership_id": str(mem.id),
            "user_id": str(mem.user_id),
            "new_role": new_role.name,
            "status": mem.status,
        }

    async def update_member_status(
        self,
        ctx: AuthorizationContext,
        membership_id: uuid.UUID,
        new_status: str,
        ip_address: str = None
    ) -> Dict[str, Any]:
        if not ctx.has_permission(Permissions.MEMBER_MANAGE):
            raise DomainException("Permission member:manage required", code="AUTH_PERMISSION_DENIED")

        if new_status not in ("ACTIVE", "SUSPENDED", "REVOKED"):
            raise DomainException("Invalid membership status", code="INVALID_STATUS")

        org_id = ctx.active_organization.id

        mem_res = await self.db.execute(
            select(OrganizationMembershipORM).where(
                OrganizationMembershipORM.id == membership_id,
                OrganizationMembershipORM.organization_id == org_id
            )
        )
        mem = mem_res.scalar_one_or_none()
        if not mem:
            raise DomainException("Organization membership not found", code="MEMBERSHIP_NOT_FOUND")

        # Prevent self-suspension/revocation if last active admin
        if mem.user_id == ctx.user.id and new_status in ("SUSPENDED", "REVOKED"):
            admin_count = await self.db.execute(
                select(OrganizationMembershipORM)
                .join(RoleORM, OrganizationMembershipORM.role_id == RoleORM.id)
                .where(
                    OrganizationMembershipORM.organization_id == org_id,
                    RoleORM.name == "ORGANIZATION_ADMIN",
                    OrganizationMembershipORM.status == "ACTIVE"
                )
            )
            if len(admin_count.scalars().all()) <= 1:
                raise DomainException("Cannot revoke or suspend the sole active administrator of an organization", code="LAST_ADMIN_PROTECTION")

        old_status = mem.status
        mem.status = new_status

        audit = AuditLogORM(
            organization_id=org_id,
            actor_user_id=ctx.user.id,
            actor_type="USER",
            action=f"membership.{new_status.lower()}",
            resource_type="OrganizationMembership",
            resource_id=mem.id,
            ip_address=ip_address,
            metadata_json={"target_user_id": str(mem.user_id), "old_status": old_status, "new_status": new_status},
        )
        self.db.add(audit)
        await self.db.commit()

        return {
            "membership_id": str(mem.id),
            "user_id": str(mem.user_id),
            "status": mem.status,
        }
