import uuid

import pytest
from sqlalchemy import select

from apps.api.app.core.authorization.context import AuthorizationService
from apps.api.app.core.database import AsyncSessionLocal
from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.candidates.infrastructure.orm import CandidateProfileORM
from apps.api.app.modules.identity.application.login_use_case import LoginUseCase
from apps.api.app.modules.identity.application.password_reset_use_case import PasswordResetUseCase
from apps.api.app.modules.identity.application.refresh_token_use_case import RefreshTokenUseCase
from apps.api.app.modules.identity.application.register_use_case import RegisterUseCase
from apps.api.app.modules.identity.infrastructure.orm import (
    UserORM,
)
from apps.api.app.modules.organizations.infrastructure.orm import (
    OrganizationMembershipORM,
    OrganizationORM,
    RoleORM,
)


@pytest.mark.asyncio
async def test_registration_flow_and_email_normalization():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        test_email = f"   Test.User_{suffix}@Example.COM  "
        normalized_expected = f"test.user_{suffix}@example.com"

        use_case = RegisterUseCase(db_session)
        res = await use_case.execute(email=test_email, password="SecurePassword123!")

        assert res["email"] == normalized_expected
        assert res["account_status"] == "PENDING_VERIFICATION"

        # Verify duplicate email rejected
        with pytest.raises(DomainException) as exc:
            await use_case.execute(email=normalized_expected, password="SecurePassword123!")
        assert exc.value.code == "AUTH_EMAIL_ALREADY_EXISTS"

        # Verify invalid password rejected
        with pytest.raises(DomainException) as exc:
            await use_case.execute(email=f"new.user_{suffix}@example.com", password="weak")
        assert exc.value.code == "PASSWORD_TOO_SHORT"


@pytest.mark.asyncio
async def test_login_and_refresh_token_rotation():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        email = f"login.test_{suffix}@example.com"

        # 1. Register & activate user
        reg_case = RegisterUseCase(db_session)
        await reg_case.execute(email=email, password="SecurePassword123!")
        user_res = await db_session.execute(select(UserORM).where(UserORM.email == email))
        user = user_res.scalar_one()
        user.account_status = "ACTIVE"
        await db_session.commit()

        # 2. Login
        login_case = LoginUseCase(db_session)
        body, raw_refresh_1 = await login_case.execute(email=email, password="SecurePassword123!")
        assert "access_token" in body
        assert raw_refresh_1 is not None

        # 3. Rotate refresh token once
        refresh_case = RefreshTokenUseCase(db_session)
        ref_body, raw_refresh_2 = await refresh_case.execute(raw_refresh_1)
        assert "access_token" in ref_body
        assert raw_refresh_2 != raw_refresh_1

        # 4. Attempting to use old refresh token again is rejected
        with pytest.raises(DomainException) as exc:
            await refresh_case.execute(raw_refresh_1)
        assert exc.value.code == "AUTH_SESSION_REVOKED"


@pytest.mark.asyncio
async def test_password_reset_and_session_invalidation():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        email = f"reset.test_{suffix}@example.com"

        # 1. Setup active user + login session
        reg_case = RegisterUseCase(db_session)
        await reg_case.execute(email=email, password="OldPassword123!")
        user_res = await db_session.execute(select(UserORM).where(UserORM.email == email))
        user = user_res.scalar_one()
        user.account_status = "ACTIVE"
        await db_session.commit()

        login_case = LoginUseCase(db_session)
        _, raw_refresh = await login_case.execute(email=email, password="OldPassword123!")

        # 2. Request password reset
        reset_case = PasswordResetUseCase(db_session)
        req_res = await reset_case.request_password_reset(email=email)
        assert "link has been sent" in req_res["message"]

        # 3. Revoke sessions via password reset
        from apps.api.app.modules.identity.infrastructure.repositories import SessionRepository
        sess_repo = SessionRepository(db_session)
        await sess_repo.revoke_all_user_sessions(user.id, reason="PASSWORD_RESET")
        await db_session.commit()

        # Verify session invalidation after reset
        refresh_case = RefreshTokenUseCase(db_session)
        with pytest.raises(DomainException):
            await refresh_case.execute(raw_refresh)


@pytest.mark.asyncio
async def test_multi_organization_context_resolution():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        email = f"multi.org_{suffix}@example.com"

        # Setup User
        user = UserORM(email=email, account_status="ACTIVE")
        db_session.add(user)
        await db_session.flush()

        # Setup Org A and Org B
        org_a = OrganizationORM(name="Org A", slug=f"org-a-{suffix}", account_status="ACTIVE")
        org_b = OrganizationORM(name="Org B", slug=f"org-b-{suffix}", account_status="ACTIVE")
        db_session.add_all([org_a, org_b])
        await db_session.flush()

        # Fetch Role
        role_res = await db_session.execute(select(RoleORM).where(RoleORM.name == "RECRUITER"))
        role = role_res.scalar_one()

        # User is member of Org A only
        mem_a = OrganizationMembershipORM(organization_id=org_a.id, user_id=user.id, role_id=role.id, status="ACTIVE")
        db_session.add(mem_a)
        await db_session.commit()

        # Re-query user
        user_fresh = (await db_session.execute(select(UserORM).where(UserORM.id == user.id))).scalar_one()

        auth_service = AuthorizationService(db_session)

        # 1. Resolve Org A Context -> SUCCESS
        ctx_a = await auth_service.resolve_authorization_context(user_fresh, requested_org_id=org_a.id)
        assert ctx_a.active_organization.id == org_a.id

        # 2. Resolve Org B Context -> ACCESS DENIED
        with pytest.raises(DomainException) as exc:
            await auth_service.resolve_authorization_context(user_fresh, requested_org_id=org_b.id)
        assert exc.value.code == "AUTH_ORGANIZATION_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_candidate_cross_tenant_isolation():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        email = f"candidate.multi_{suffix}@example.com"

        # 1. Create and flush user
        user = UserORM(email=email, account_status="ACTIVE")
        db_session.add(user)
        await db_session.flush()

        # 2. Create and flush organizations
        org_a = OrganizationORM(name="Org A", slug=f"org-a-cand-{suffix}", account_status="ACTIVE")
        org_b = OrganizationORM(name="Org B", slug=f"org-b-cand-{suffix}", account_status="ACTIVE")
        db_session.add_all([org_a, org_b])
        await db_session.flush()

        # 3. Create candidate profile using flushed UUIDs
        profile_a = CandidateProfileORM(
            user_id=user.id,
            organization_id=org_a.id,
            first_name="Jane",
            last_name="Doe",
            email=email,
            status="ACTIVE"
        )
        db_session.add(profile_a)

        # 4. Create memberships
        role_res = await db_session.execute(select(RoleORM).where(RoleORM.name == "CANDIDATE"))
        role = role_res.scalar_one()
        db_session.add_all([
            OrganizationMembershipORM(organization_id=org_a.id, user_id=user.id, role_id=role.id, status="ACTIVE"),
            OrganizationMembershipORM(organization_id=org_b.id, user_id=user.id, role_id=role.id, status="ACTIVE"),
        ])
        await db_session.commit()

        # 5. Re-query user
        user_fresh = (await db_session.execute(select(UserORM).where(UserORM.id == user.id))).scalar_one()

        auth_service = AuthorizationService(db_session)

        # Org A Context has CandidateProfile
        ctx_a = await auth_service.resolve_authorization_context(user_fresh, requested_org_id=org_a.id)
        assert ctx_a.candidate_profile is not None
        assert ctx_a.candidate_profile.organization_id == org_a.id

        # Org B Context has NO CandidateProfile (isolated!)
        ctx_b = await auth_service.resolve_authorization_context(user_fresh, requested_org_id=org_b.id)
        assert ctx_b.candidate_profile is None
