import uuid
from datetime import date

import pytest
from sqlalchemy import select

from apps.api.app.core.authorization.context import AuthorizationService
from apps.api.app.core.database import AsyncSessionLocal
from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.candidates.application.candidate_linking_use_case import (
    CandidateLinkingUseCase,
)
from apps.api.app.modules.candidates.application.manage_candidate_use_case import (
    ManageCandidateUseCase,
)
from apps.api.app.modules.candidates.application.manage_experience_education_use_case import (
    ManageExperienceEducationUseCase,
)
from apps.api.app.modules.candidates.application.manage_skills_use_case import ManageSkillsUseCase
from apps.api.app.modules.candidates.infrastructure.orm import (
    CandidateInvitationORM,
)
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
from apps.api.app.modules.organizations.infrastructure.orm import (
    OrganizationInvitationORM,
)


@pytest.mark.asyncio
async def test_organization_bootstrap_and_admin_membership():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"admin_{suffix}@example.com", account_status="ACTIVE")
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"Acme Corp {suffix}", slug=f"acme-{suffix}")

        assert org_data["name"] == f"Acme Corp {suffix}"
        assert org_data["role"] == "ORGANIZATION_ADMIN"

        # Verify duplicate slug rejected
        with pytest.raises(DomainException) as exc:
            await bootstrap_case.execute(user=user, name="Duplicate", slug=f"acme-{suffix}")
        assert exc.value.code == "ORGANIZATION_SLUG_EXISTS"


@pytest.mark.asyncio
async def test_recruiter_invitation_acceptance_and_privilege_escalation():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]

        # 1. Setup Admin User & Org
        admin = UserORM(email=f"org.admin_{suffix}@example.com", account_status="ACTIVE")
        db_session.add(admin)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=admin, name=f"Invite Org {suffix}", slug=f"invite-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        admin_ctx = await auth_service.resolve_authorization_context(admin, requested_org_id=org_id)

        # 2. Admin invites Recruiter
        recruiter_email = f"recruiter_{suffix}@example.com"
        invite_case = InviteMemberUseCase(db_session)
        inv_res = await invite_case.execute(admin_ctx, target_email=recruiter_email, role_name="RECRUITER")
        assert inv_res["status"] == "PENDING"

        # Fetch invitation record to simulate token acceptance
        inv_orm = (await db_session.execute(
            select(OrganizationInvitationORM).where(OrganizationInvitationORM.id == uuid.UUID(inv_res["invitation_id"]))
        )).scalar_one()
        assert inv_orm.token_hash is not None

        # 3. Recruiter registers & accepts invitation
        recruiter_user = UserORM(email=recruiter_email, account_status="ACTIVE")
        db_session.add(recruiter_user)
        await db_session.commit()

        from apps.api.app.modules.identity.domain.token_generator import hash_token
        raw_token = "test_invite_token_" + suffix
        inv_orm.token_hash = hash_token(raw_token)
        await db_session.commit()

        accept_case = AcceptInvitationUseCase(db_session)
        accept_res = await accept_case.execute(user=recruiter_user, raw_token=raw_token)
        assert accept_res["status"] == "ACTIVE"

        # 4. Resolve Recruiter Context & Verify Privilege Escalation Prevention
        recruiter_ctx = await auth_service.resolve_authorization_context(recruiter_user, requested_org_id=org_id)
        assert recruiter_ctx.role.name == "RECRUITER"

        # Recruiter trying to assign ORGANIZATION_ADMIN privileges is rejected
        manage_mem_case = ManageMembershipUseCase(db_session)
        with pytest.raises(DomainException) as exc:
            await manage_mem_case.update_member_role(
                ctx=recruiter_ctx,
                membership_id=uuid.UUID(accept_res["membership_id"]),
                new_role_name="ORGANIZATION_ADMIN"
            )
        assert exc.value.code in ("PRIVILEGE_ESCALATION_DENIED", "AUTH_PERMISSION_DENIED")


@pytest.mark.asyncio
async def test_candidate_creation_skills_experience_education_and_archival():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]

        recruiter = UserORM(email=f"recruiter.cand_{suffix}@example.com", account_status="ACTIVE")
        db_session.add(recruiter)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=recruiter, name=f"Cand Org {suffix}", slug=f"cand-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        recruiter_ctx = await auth_service.resolve_authorization_context(recruiter, requested_org_id=org_id)

        # 1. Create Candidate Profile
        cand_case = ManageCandidateUseCase(db_session)
        candidate = await cand_case.create_candidate(
            recruiter_ctx,
            first_name="Alice",
            last_name="Smith",
            email=f"alice_{suffix}@example.com",
            headline="Senior Backend Engineer",
            summary="10 years of Python experience"
        )
        cand_id = uuid.UUID(candidate["id"])
        assert candidate["status"] == "ACTIVE"
        assert candidate["is_linked"] is False

        # 2. Add Skills
        skills_case = ManageSkillsUseCase(db_session)
        skill = await skills_case.add_skill(
            recruiter_ctx,
            candidate_id=cand_id,
            skill_name="Python",
            category="Programming Languages",
            years_experience=8.5,
            proficiency_level="EXPERT",
            source="MANUAL"
        )
        assert skill["skill_name"] == "Python"

        # 3. Add Experience & Education
        exp_edu_case = ManageExperienceEducationUseCase(db_session)
        exp = await exp_edu_case.add_experience(
            recruiter_ctx,
            candidate_id=cand_id,
            company_name="Tech Corp",
            job_title="Lead Developer",
            start_date=date(2020, 1, 1),
            is_current=True
        )
        assert exp["company_name"] == "Tech Corp"

        edu = await exp_edu_case.add_education(
            recruiter_ctx,
            candidate_id=cand_id,
            institution="MIT",
            degree="B.S.",
            field_of_study="Computer Science",
            end_year=2019
        )
        assert edu["institution"] == "MIT"

        # 4. Archive Candidate
        archive_res = await cand_case.archive_candidate(recruiter_ctx, candidate_id=cand_id)
        assert archive_res["status"] == "ARCHIVED"

        # Updating archived candidate is rejected
        with pytest.raises(DomainException) as exc:
            await cand_case.update_candidate(recruiter_ctx, candidate_id=cand_id, first_name="Alice Modified")
        assert exc.value.code == "CANDIDATE_ARCHIVED"


@pytest.mark.asyncio
async def test_candidate_identity_linking():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]

        recruiter = UserORM(email=f"recruiter.link_{suffix}@example.com", account_status="ACTIVE")
        db_session.add(recruiter)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=recruiter, name=f"Link Org {suffix}", slug=f"link-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        recruiter_ctx = await auth_service.resolve_authorization_context(recruiter, requested_org_id=org_id)

        # Recruiter creates candidate
        cand_email = f"cand_link_{suffix}@example.com"
        cand_case = ManageCandidateUseCase(db_session)
        candidate = await cand_case.create_candidate(recruiter_ctx, first_name="Bob", last_name="Jones", email=cand_email)
        cand_id = uuid.UUID(candidate["id"])

        # Issue Candidate Linking Invitation
        link_case = CandidateLinkingUseCase(db_session)
        inv_res = await link_case.create_candidate_invitation(recruiter_ctx, candidate_id=cand_id)
        assert inv_res["status"] == "PENDING"

        # Simulate raw token for testing
        from apps.api.app.modules.identity.domain.token_generator import hash_token
        raw_token = "cand_link_token_" + suffix
        inv_orm = (await db_session.execute(
            select(CandidateInvitationORM).where(CandidateInvitationORM.id == uuid.UUID(inv_res["invitation_id"]))
        )).scalar_one()
        inv_orm.token_hash = hash_token(raw_token)
        await db_session.commit()

        # Candidate user registers & accepts linking token
        cand_user = UserORM(email=cand_email, account_status="ACTIVE")
        db_session.add(cand_user)
        await db_session.commit()

        link_res = await link_case.accept_candidate_linking(user=cand_user, raw_token=raw_token)
        assert link_res["candidate_id"] == str(cand_id)

        # Verify profile is now linked
        updated_cand = await cand_case.get_candidate(recruiter_ctx, candidate_id=cand_id)
        assert updated_cand["is_linked"] is True
        assert updated_cand["user_id"] == str(cand_user.id)


@pytest.mark.asyncio
async def test_cross_tenant_candidate_isolation_enforcement():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]

        rec_a = UserORM(email=f"rec_a_{suffix}@example.com", account_status="ACTIVE")
        rec_b = UserORM(email=f"rec_b_{suffix}@example.com", account_status="ACTIVE")
        db_session.add_all([rec_a, rec_b])
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_a = await bootstrap_case.execute(user=rec_a, name=f"Org A {suffix}", slug=f"org-a-{suffix}")
        org_b = await bootstrap_case.execute(user=rec_b, name=f"Org B {suffix}", slug=f"org-b-{suffix}")

        auth_service = AuthorizationService(db_session)
        ctx_a = await auth_service.resolve_authorization_context(rec_a, requested_org_id=uuid.UUID(org_a["id"]))
        ctx_b = await auth_service.resolve_authorization_context(rec_b, requested_org_id=uuid.UUID(org_b["id"]))

        # Recruiter A creates candidate in Org A
        cand_case = ManageCandidateUseCase(db_session)
        cand_a = await cand_case.create_candidate(ctx_a, first_name="TenantA", last_name="User", email=f"cand_a_{suffix}@example.com")
        cand_a_id = uuid.UUID(cand_a["id"])

        # Recruiter B attempting to get candidate in Org A is denied / not found
        with pytest.raises(DomainException) as exc:
            await cand_case.get_candidate(ctx_b, candidate_id=cand_a_id)
        assert exc.value.code == "CANDIDATE_NOT_FOUND"

        # Candidate list in Org B does not include Org A candidate
        list_b = await cand_case.list_candidates(ctx_b)
        assert list_b["total"] == 0
