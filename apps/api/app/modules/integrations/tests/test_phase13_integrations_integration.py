import uuid

import pytest

from apps.api.app.modules.candidates.infrastructure.orm import CandidateProfileORM
from apps.api.app.modules.integrations.infrastructure.orm import (
    IntegrationEventORM,
    IntegrationORM,
    WebhookDeliveryORM,
)
from apps.api.app.modules.integrations.infrastructure.providers.greenhouse import GreenhouseProvider
from apps.api.app.modules.integrations.infrastructure.providers.lever import LeverProvider
from apps.api.app.modules.integrations.infrastructure.providers.workday import WorkdayProvider
from apps.api.app.modules.interviews.infrastructure.orm import InterviewSessionORM
from apps.api.app.modules.job_roles.infrastructure.orm import JobRoleORM
from apps.api.app.modules.organizations.infrastructure.orm import OrganizationORM
from apps.api.app.modules.reports.infrastructure.orm import InterviewReportORM, ReportExportORM
from workers.tasks.process_notification_task import ProcessNotificationWorkerTask
from workers.tasks.process_pdf_export_task import ProcessPDFExportWorkerTask
from workers.tasks.process_webhook_delivery_task import ProcessWebhookDeliveryWorkerTask


@pytest.mark.asyncio
async def test_integration_provider_adapters():
    gh = GreenhouseProvider()
    assert await gh.validate_configuration({}, "secret123") is True
    res_gh = await gh.test_connection({}, "secret123")
    assert res_gh["status"] == "SUCCESS"

    lv = LeverProvider()
    res_lv = await lv.test_connection({}, "secret123")
    assert res_lv["status"] == "SUCCESS"

    wd = WorkdayProvider()
    res_wd = await wd.test_connection({}, "secret123")
    assert res_wd["status"] == "SUCCESS"

@pytest.mark.asyncio
async def test_webhook_outbox_delivery_worker(db_session):
    org_id = uuid.uuid4()
    integration = IntegrationORM(
        organization_id=org_id,
        provider_type="greenhouse",
        name="Test Greenhouse",
        status="ACTIVE",
        config_metadata_json={"env": "test"},
        encrypted_secret="secret123"
    )
    db_session.add(integration)
    await db_session.flush()

    event = IntegrationEventORM(
        organization_id=org_id,
        event_type="candidate.hiring_decision.updated",
        resource_type="candidate",
        resource_id=str(uuid.uuid4()),
        payload_json={"status": "HIRED", "candidate_profile_id": str(uuid.uuid4())}
    )
    db_session.add(event)
    await db_session.flush()

    delivery = WebhookDeliveryORM(
        organization_id=org_id,
        integration_id=integration.id,
        event_id=event.id,
        status="PENDING",
        max_attempts=5
    )
    db_session.add(delivery)
    await db_session.commit()

    worker_res = await ProcessWebhookDeliveryWorkerTask.execute(
        db_session, "worker_1", {"delivery_id": str(delivery.id)}
    )
    assert worker_res["status"] == "DELIVERED"

@pytest.mark.asyncio
async def test_notification_delivery_worker(db_session):
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()

    res = await ProcessNotificationWorkerTask.execute(
        db_session,
        "worker_1",
        {
            "organization_id": str(org_id),
            "user_id": str(user_id),
            "channel": "SLACK",
            "event_type": "interview.completed",
            "title": "Interview Completed",
            "message": "Candidate evaluation report is ready for review.",
            "webhook_url": "https://hooks.slack.com/services/mock"
        }
    )
    assert res["status"] == "DELIVERED"
    assert res["channel"] == "SLACK"

@pytest.mark.asyncio
async def test_pdf_report_generator_and_worker(db_session):
    org = OrganizationORM(
        name="PDF Test Org",
        slug=f"pdf-org-{uuid.uuid4().hex[:6]}"
    )
    db_session.add(org)
    await db_session.flush()

    cand = CandidateProfileORM(
        organization_id=org.id,
        first_name="Jane",
        last_name="Doe",
        email=f"jane.{uuid.uuid4().hex[:6]}@example.com"
    )
    db_session.add(cand)
    await db_session.flush()

    job_role = JobRoleORM(
        organization_id=org.id,
        title="Senior Architect",
        code=f"ARCH_{uuid.uuid4().hex[:4].upper()}"
    )
    db_session.add(job_role)
    await db_session.flush()

    sess = InterviewSessionORM(
        organization_id=org.id,
        candidate_profile_id=cand.id,
        job_role_id=job_role.id,
        status="COMPLETED"
    )
    db_session.add(sess)
    await db_session.flush()

    report = InterviewReportORM(
        interview_session_id=sess.id,
        report_version=1,
        scoring_version="v1",
        overall_score=8.5,
        technical_competency_score=8.5,
        reasoning_score=8.5,
        communication_score=8.5,
        completeness_score=8.5,
        requirement_coverage_score=8.5,
        seniority_assessment="Senior Architect",
        executive_summary="Excellent technical depth in system architecture and distributed databases.",
        top_strengths={"strengths": ["PostgreSQL", "System Architecture"]},
        growth_areas={"growth_areas": ["Kubernetes"]},
        skill_scores_json={"skills": []},
        recommendation="STRONG_HIRE",
        hiring_signal="STRONG_HIRE_SIGNAL",
        status="GENERATED"
    )
    db_session.add(report)
    await db_session.flush()

    export = ReportExportORM(
        organization_id=org.id,
        interview_session_id=sess.id,
        interview_report_id=report.id,
        report_version=1,
        status="QUEUED"
    )
    db_session.add(export)
    await db_session.commit()

    worker_res = await ProcessPDFExportWorkerTask.execute(
        db_session, "worker_1", {"export_id": str(export.id)}
    )
    assert worker_res["status"] == "READY"
    assert worker_res["file_size_bytes"] > 0
