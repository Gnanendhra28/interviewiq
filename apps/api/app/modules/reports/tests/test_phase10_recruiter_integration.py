import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from apps.api.app.core.authorization.context import AuthorizationService
from apps.api.app.core.database import AsyncSessionLocal
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM
from apps.api.app.modules.candidates.application.manage_candidate_use_case import (
    ManageCandidateUseCase,
)
from apps.api.app.modules.identity.infrastructure.orm import UserORM
from apps.api.app.modules.interviews.application.manage_interviews_use_case import (
    ManageInterviewsUseCase,
)
from apps.api.app.modules.job_roles.application.manage_job_roles_use_case import (
    ManageJobRolesUseCase,
)
from apps.api.app.modules.organizations.application.bootstrap_organization_use_case import (
    BootstrapOrganizationUseCase,
)
from apps.api.app.modules.reports.application.hiring_decision_use_case import HiringDecisionUseCase
from apps.api.app.modules.reports.application.manage_reports_use_case import ManageReportsUseCase
from apps.api.app.modules.reports.application.recruiter_command_center_use_case import (
    RecruiterCommandCenterUseCase,
)
from apps.api.app.modules.reports.infrastructure.orm import (
    HiringDecisionStatus,
)
from workers.tasks.process_interview_report_task import ProcessInterviewReportWorkerTask


@pytest.mark.asyncio
async def test_recruiter_dashboard_and_review_queue():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_p10_{suffix}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"P10 Org {suffix}", slug=f"p10-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        cand = await ManageCandidateUseCase(db_session).create_candidate(ctx, first_name="Jack", last_name="Dashboard", email=f"jack_{suffix}@example.com")
        cand_id = uuid.UUID(cand["id"])

        role = await ManageJobRolesUseCase(db_session).create_job_role(ctx, title="Backend Lead", code=f"BE_LEAD_{suffix}")
        role_id = uuid.UUID(role["id"])

        int_case = ManageInterviewsUseCase(db_session)
        interview = await int_case.create_interview(ctx, candidate_profile_id=cand_id, job_role_id=role_id)
        interview_id = uuid.UUID(interview["id"])
        await int_case.prepare_interview(ctx, interview_id)
        await int_case.start_interview(ctx, interview_id)

        rep_case = ManageReportsUseCase(db_session)
        await rep_case.complete_interview(ctx, interview_id)

        job_c = (await db_session.execute(
            select(BackgroundJobORM).where(BackgroundJobORM.resource_id == interview_id, BackgroundJobORM.job_type == "INTERVIEW_REPORT_GENERATION")
        )).scalar_one()
        job_c.status = "RUNNING"
        job_c.started_at = datetime.now(timezone.utc)
        await db_session.commit()

        await ProcessInterviewReportWorkerTask(db_session).execute_job(job_c)

        cmd_case = RecruiterCommandCenterUseCase(db_session)

        # 1. Test Dashboard Endpoint
        dash = await cmd_case.get_dashboard_metrics(ctx)
        assert dash["active_job_roles_count"] >= 1
        assert dash["active_candidates_count"] >= 1
        assert dash["completed_reports_count"] >= 1

        # 2. Test Review Queue Endpoint
        queue = await cmd_case.get_review_queue(ctx)
        assert queue["total_actionable_items"] >= 1
        assert queue["queue"][0]["queue_item_type"] == "REPORT_PENDING_DECISION"


@pytest.mark.asyncio
async def test_candidate_pipeline_and_timeline():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_pipe_{suffix}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"Pipe Org {suffix}", slug=f"pipe-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        cand = await ManageCandidateUseCase(db_session).create_candidate(ctx, first_name="Karen", last_name="Pipeline", email=f"karen_{suffix}@example.com")
        cand_id = uuid.UUID(cand["id"])

        cmd_case = RecruiterCommandCenterUseCase(db_session)

        # Candidate Pipeline
        pipeline = await cmd_case.get_candidate_pipeline(ctx, search_query="Karen")
        assert pipeline["count"] >= 1
        assert pipeline["candidates"][0]["full_name"] == "Karen Pipeline"

        # Candidate Timeline
        timeline = await cmd_case.get_candidate_timeline(ctx, cand_id)
        assert len(timeline) >= 1
        assert timeline[0]["event_type"] == "candidate.created"


@pytest.mark.asyncio
async def test_candidate_comparison():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_comp_{suffix}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"Comp Org {suffix}", slug=f"comp-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        cand1 = await ManageCandidateUseCase(db_session).create_candidate(ctx, first_name="Leo", last_name="Comp1", email=f"leo_{suffix}@example.com")
        cand2 = await ManageCandidateUseCase(db_session).create_candidate(ctx, first_name="Maya", last_name="Comp2", email=f"maya_{suffix}@example.com")

        cmd_case = RecruiterCommandCenterUseCase(db_session)
        comp = await cmd_case.compare_candidates(ctx, [uuid.UUID(cand1["id"]), uuid.UUID(cand2["id"])])

        assert comp["comparison_count"] == 2
        assert comp["candidates"][0]["candidate_id"] == cand1["id"]
        assert comp["candidates"][1]["candidate_id"] == cand2["id"]


@pytest.mark.asyncio
async def test_human_hiring_decision_workflow_and_immutable_history():
    async with AsyncSessionLocal() as db_session:
        suffix = uuid.uuid4().hex[:6]
        user = UserORM(email=f"recruiter_dec_{suffix}@example.com", account_status="ACTIVE", is_super_admin=True)
        db_session.add(user)
        await db_session.commit()

        bootstrap_case = BootstrapOrganizationUseCase(db_session)
        org_data = await bootstrap_case.execute(user=user, name=f"Dec Org {suffix}", slug=f"dec-org-{suffix}")
        org_id = uuid.UUID(org_data["id"])

        auth_service = AuthorizationService(db_session)
        ctx = await auth_service.resolve_authorization_context(user, requested_org_id=org_id)

        cand = await ManageCandidateUseCase(db_session).create_candidate(ctx, first_name="Nora", last_name="Decision", email=f"nora_{suffix}@example.com")
        role = await ManageJobRolesUseCase(db_session).create_job_role(ctx, title="Role Dec", code=f"DEC_{suffix}")

        int_case = ManageInterviewsUseCase(db_session)
        interview = await int_case.create_interview(ctx, candidate_profile_id=uuid.UUID(cand["id"]), job_role_id=uuid.UUID(role["id"]))
        interview_id = uuid.UUID(interview["id"])

        dec_case = HiringDecisionUseCase(db_session)

        # 1. Initial Human Decision: SHORTLISTED
        d1 = await dec_case.record_hiring_decision(ctx, interview_id, HiringDecisionStatus.SHORTLISTED, rationale_text="Strong resume background.")
        assert d1["status"] == "SHORTLISTED"

        # 2. Updated Human Decision: HIRED
        d2 = await dec_case.record_hiring_decision(ctx, interview_id, HiringDecisionStatus.HIRED, rationale_text="Outstanding interview performance.")
        assert d2["status"] == "HIRED"

        # 3. Verify Immutable Decision History
        history = await dec_case.get_hiring_decision_history(ctx, interview_id)
        assert len(history) == 2
        assert history[0]["new_status"] == "HIRED"
        assert history[0]["previous_status"] == "SHORTLISTED"
        assert history[1]["new_status"] == "SHORTLISTED"
        assert history[1]["previous_status"] == "PENDING_REVIEW"
