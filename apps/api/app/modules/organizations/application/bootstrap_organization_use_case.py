from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.identity.infrastructure.orm import UserORM
from apps.api.app.modules.organizations.infrastructure.orm import (
    OrganizationMembershipORM,
    OrganizationORM,
    RoleORM,
)


class BootstrapOrganizationUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, user: UserORM, name: str, slug: str, ip_address: str = None) -> Dict[str, Any]:
        normalized_slug = slug.strip().lower()
        if not normalized_slug:
            raise DomainException("Organization slug cannot be empty", code="INVALID_ORGANIZATION_SLUG")

        # 1. Validate slug uniqueness
        existing_res = await self.db.execute(
            select(OrganizationORM).where(OrganizationORM.slug == normalized_slug)
        )
        if existing_res.scalar_one_or_none():
            raise DomainException("Organization slug is already in use", code="ORGANIZATION_SLUG_EXISTS")

        # 2. Fetch ORGANIZATION_ADMIN role
        role_res = await self.db.execute(select(RoleORM).where(RoleORM.name == "ORGANIZATION_ADMIN"))
        org_admin_role = role_res.scalar_one_or_none()
        if not org_admin_role:
            raise DomainException("System role ORGANIZATION_ADMIN not found", code="ROLE_NOT_FOUND")

        # 3. Transactionally create Organization + Membership
        org = OrganizationORM(
            name=name.strip(),
            slug=normalized_slug,
            account_status="ACTIVE",
        )
        self.db.add(org)
        await self.db.flush()

        membership = OrganizationMembershipORM(
            organization_id=org.id,
            user_id=user.id,
            role_id=org_admin_role.id,
            status="ACTIVE",
        )
        self.db.add(membership)

        # 4. Audit logging
        audit = AuditLogORM(
            organization_id=org.id,
            actor_user_id=user.id,
            actor_type="USER",
            action="organization.created",
            resource_type="Organization",
            resource_id=org.id,
            ip_address=ip_address,
            metadata_json={"name": org.name, "slug": org.slug},
        )
        self.db.add(audit)
        await self.db.commit()

        return {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "account_status": org.account_status,
            "role": "ORGANIZATION_ADMIN",
            "created_at": org.created_at.isoformat(),
        }
