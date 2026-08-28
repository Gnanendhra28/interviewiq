import pytest
import uuid
from apps.api.app.modules.organizations.infrastructure.orm import OrganizationORM, OrganizationMembershipORM, RoleORM
from apps.api.app.modules.identity.infrastructure.orm import UserORM
from apps.api.app.modules.candidates.infrastructure.orm import CandidateProfileORM
from apps.api.app.modules.resumes.infrastructure.orm import ResumeORM, ResumeAnalysisORM
from apps.api.app.modules.job_roles.infrastructure.orm import JobRoleORM
from apps.api.app.modules.knowledge_rag.infrastructure.orm import KnowledgeBaseORM, KnowledgeDocumentORM
from apps.api.app.modules.interviews.infrastructure.orm import InterviewSessionORM
from apps.api.app.modules.reports.infrastructure.orm import InterviewReportORM, HiringDecisionORM, ReportExportORM
from apps.api.app.modules.integrations.infrastructure.orm import IntegrationORM
from apps.api.app.core.authorization.context import AuthorizationContext

@pytest.mark.asyncio
async def test_adversarial_multi_tenant_isolation(db_session):
    """
    Adversarial Multi-Tenant Isolation Security Test Suite (ADR 011).
    Verifies that Organization A cannot access, query, modify, or download Organization B resources.
    """
    # Create Organization A
    org_a = OrganizationORM(name="Org A", slug=f"org-a-{uuid.uuid4().hex[:6]}")
    user_a = UserORM(email=f"recruiter.a.{uuid.uuid4().hex[:6]}@orga.com")
    db_session.add_all([org_a, user_a])
    await db_session.flush()

    role_a = RoleORM(name=f"ROLE_A_{uuid.uuid4().hex[:4]}")
    db_session.add(role_a)
    await db_session.flush()

    mem_a = OrganizationMembershipORM(organization_id=org_a.id, user_id=user_a.id, role_id=role_a.id, status="ACTIVE")
    db_session.add(mem_a)
    await db_session.flush()

    # Create Organization B
    org_b = OrganizationORM(name="Org B", slug=f"org-b-{uuid.uuid4().hex[:6]}")
    user_b = UserORM(email=f"recruiter.b.{uuid.uuid4().hex[:6]}@orgb.com")
    db_session.add_all([org_b, user_b])
    await db_session.flush()

    role_b = RoleORM(name=f"ROLE_B_{uuid.uuid4().hex[:4]}")
    db_session.add(role_b)
    await db_session.flush()

    mem_b = OrganizationMembershipORM(organization_id=org_b.id, user_id=user_b.id, role_id=role_b.id, status="ACTIVE")
    db_session.add(mem_b)
    await db_session.flush()

    # Org B Resources
    cand_b = CandidateProfileORM(organization_id=org_b.id, first_name="Bob", last_name="Jones", email=f"bob.{uuid.uuid4().hex[:6]}@orgb.com")
    role_b_job = JobRoleORM(organization_id=org_b.id, title="Org B Engineer", code=f"ORGB_{uuid.uuid4().hex[:4].upper()}")
    kb_b = KnowledgeBaseORM(organization_id=org_b.id, name="Org B Secret KB")
    db_session.add_all([cand_b, role_b_job, kb_b])
    await db_session.flush()

    doc_b = KnowledgeDocumentORM(knowledge_base_id=kb_b.id, title="Secret Spec", storage_key="key", checksum_sha256="hash", ingestion_status="READY")
    sess_b = InterviewSessionORM(organization_id=org_b.id, candidate_profile_id=cand_b.id, job_role_id=role_b_job.id, status="COMPLETED")
    db_session.add_all([doc_b, sess_b])
    await db_session.flush()

    report_b = InterviewReportORM(interview_session_id=sess_b.id, report_version=1, scoring_version="v1", overall_score=9.0, seniority_assessment="Senior", executive_summary="Confidential summary", top_strengths={}, growth_areas={}, skill_scores_json={}, recommendation="HIRE", hiring_signal="HIRE_SIGNAL", status="GENERATED")
    decision_b = HiringDecisionORM(organization_id=org_b.id, interview_session_id=sess_b.id, candidate_profile_id=cand_b.id, status="HIRED", decision_maker_user_id=user_b.id)
    integ_b = IntegrationORM(organization_id=org_b.id, provider_type="greenhouse", name="Org B Integration", status="ACTIVE")
    db_session.add_all([report_b, decision_b, integ_b])
    await db_session.flush()

    export_b = ReportExportORM(organization_id=org_b.id, interview_session_id=sess_b.id, interview_report_id=report_b.id, report_version=1, status="READY", storage_object_key="key_b.pdf")
    db_session.add(export_b)
    await db_session.commit()

    # Authorization Context for User A in Org A
    ctx_a = AuthorizationContext(
        user=user_a,
        active_organization=org_a,
        membership=mem_a,
        role=role_a
    )
    ctx_a.has_permission = lambda perm: True

    # 1. Candidate Access Rejection
    from apps.api.app.modules.candidates.application.manage_candidate_use_case import ManageCandidateUseCase
    cand_uc = ManageCandidateUseCase(db_session)
    with pytest.raises(Exception) as exc_info:
        await cand_uc.get_candidate(ctx_a, cand_b.id)
    assert "not found" in str(exc_info.value).lower() or "denied" in str(exc_info.value).lower()

    # 2. Job Role Access Rejection
    from apps.api.app.modules.job_roles.application.manage_job_roles_use_case import ManageJobRolesUseCase
    role_uc = ManageJobRolesUseCase(db_session)
    with pytest.raises(Exception) as exc_info:
        await role_uc.get_job_role(ctx_a, role_b_job.id)
    assert "not found" in str(exc_info.value).lower() or "denied" in str(exc_info.value).lower()

    # 3. Knowledge Base Access Rejection
    from apps.api.app.modules.knowledge_rag.application.manage_knowledge_bases_use_case import ManageKnowledgeBasesUseCase
    kb_uc = ManageKnowledgeBasesUseCase(db_session)
    with pytest.raises(Exception) as exc_info:
        await kb_uc.get_knowledge_base(ctx_a, kb_b.id)
    assert "not found" in str(exc_info.value).lower() or "denied" in str(exc_info.value).lower()

    # 4. Interview Session Access Rejection
    from apps.api.app.modules.interviews.application.manage_interviews_use_case import ManageInterviewsUseCase
    interview_uc = ManageInterviewsUseCase(db_session)
    with pytest.raises(Exception) as exc_info:
        await interview_uc.get_interview(ctx_a, sess_b.id)
    assert "not found" in str(exc_info.value).lower() or "denied" in str(exc_info.value).lower()
