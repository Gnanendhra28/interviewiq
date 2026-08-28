import uuid
from dataclasses import dataclass
from typing import Optional, Set, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.candidates.infrastructure.orm import CandidateProfileORM
from apps.api.app.modules.identity.infrastructure.orm import UserORM
from apps.api.app.modules.organizations.infrastructure.orm import (
    OrganizationMembershipORM,
    OrganizationORM,
    PermissionORM,
    RoleORM,
    RolePermissionORM,
)


@dataclass
class AuthorizationContext:
    user: UserORM
    active_organization: Optional[OrganizationORM] = None
    membership: Optional[OrganizationMembershipORM] = None
    role: Optional[RoleORM] = None
    permissions: Set[str] = None
    candidate_profile: Optional[CandidateProfileORM] = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = set()

    @property
    def organization_id(self) -> Optional[uuid.UUID]:
        return self.active_organization.id if self.active_organization else None

    @property
    def user_id(self) -> uuid.UUID:
        return self.user.id

    def has_permission(self, permission_name: str) -> bool:
        if self.user.is_super_admin:
            return True
        if self.role and self.role.name in ("ORGANIZATION_ADMIN", "RECRUITER", "HIRING_MANAGER"):
            return True
        return permission_name in self.permissions

    def enforce_permission(self, permission_name: str) -> None:
        if not self.has_permission(permission_name):
            raise DomainException(f"Permission '{permission_name}' required", code="AUTH_PERMISSION_DENIED")


class AuthorizationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_authorization_context(
        self,
        user: UserORM,
        requested_org_id: Optional[Union[uuid.UUID, str]] = None
    ) -> AuthorizationContext:
        # Enforce User Account Status
        if user.account_status in ("SUSPENDED", "DISABLED"):
            raise DomainException("User account is suspended or disabled", code="AUTH_ACCOUNT_SUSPENDED")

        if not requested_org_id:
            return AuthorizationContext(user=user)

        target_org_uuid = uuid.UUID(str(requested_org_id)) if isinstance(requested_org_id, (str, uuid.UUID)) else requested_org_id
        target_user_uuid = uuid.UUID(str(user.id)) if isinstance(user.id, (str, uuid.UUID)) else user.id

        # 1. Validate Organization Exists & Status == ACTIVE
        org_result = await self.db.execute(
            select(OrganizationORM).where(OrganizationORM.id == target_org_uuid, OrganizationORM.account_status == "ACTIVE")
        )
        org = org_result.scalar_one_or_none()
        if not org:
            raise DomainException("Requested organization does not exist or is inactive", code="AUTH_ORGANIZATION_NOT_FOUND")

        # 2. Validate User Membership & Status == ACTIVE
        mem_result = await self.db.execute(
            select(OrganizationMembershipORM).where(
                OrganizationMembershipORM.organization_id == target_org_uuid,
                OrganizationMembershipORM.user_id == target_user_uuid,
                OrganizationMembershipORM.status == "ACTIVE"
            )
        )
        membership = mem_result.scalar_one_or_none()
        if not membership:
            raise DomainException("User has no active membership in requested organization", code="AUTH_ORGANIZATION_ACCESS_DENIED")

        # 3. Resolve Role & Permissions
        role_uuid = uuid.UUID(str(membership.role_id))
        role_result = await self.db.execute(select(RoleORM).where(RoleORM.id == role_uuid))
        role = role_result.scalar_one_or_none()

        perm_set: Set[str] = set()
        if role:
            perm_result = await self.db.execute(
                select(PermissionORM.name)
                .join(RolePermissionORM, PermissionORM.id == RolePermissionORM.permission_id)
                .where(RolePermissionORM.role_id == role.id)
            )
            perm_set = set(perm_result.scalars().all())

        # 4. Resolve Candidate Profile (if applicable)
        cand_result = await self.db.execute(
            select(CandidateProfileORM).where(
                CandidateProfileORM.organization_id == target_org_uuid,
                CandidateProfileORM.user_id == target_user_uuid,
                CandidateProfileORM.status == "ACTIVE"
            )
        )
        cand_profile = cand_result.scalar_one_or_none()

        return AuthorizationContext(
            user=user,
            active_organization=org,
            membership=membership,
            role=role,
            permissions=perm_set,
            candidate_profile=cand_profile,
        )
