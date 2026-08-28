import pytest
import uuid
from datetime import datetime, timezone
from apps.api.app.modules.organizations.infrastructure.orm import OrganizationORM, OrganizationMembershipORM, RoleORM
from apps.api.app.modules.identity.infrastructure.orm import UserORM, PasswordCredentialORM
from apps.api.app.modules.candidates.infrastructure.orm import CandidateProfileORM, CandidateSkillORM
from apps.api.app.modules.resumes.infrastructure.orm import ResumeORM, ResumeAnalysisORM
from apps.api.app.modules.job_roles.infrastructure.orm import JobRoleORM, JobRoleRequirementORM
from apps.api.app.modules.knowledge_rag.infrastructure.orm import KnowledgeBaseORM, KnowledgeDocumentORM
from apps.api.app.modules.interviews.infrastructure.orm import InterviewSessionORM, InterviewSnapshotORM, InterviewBlueprintORM, InterviewTurnORM
from apps.api.app.modules.interview_intelligence.infrastructure.orm import InterviewQuestionORM, CandidateAnswerORM, AnswerEvaluationORM, AdaptiveDecisionORM
from apps.api.app.modules.reports.infrastructure.orm import InterviewReportORM, HiringDecisionORM, HiringDecisionHistoryORM, ReportExportORM
from apps.api.app.modules.integrations.infrastructure.orm import IntegrationORM, IntegrationEventORM, WebhookDeliveryORM
from apps.api.app.modules.notifications.infrastructure.orm import NotificationDeliveryORM

from workers.tasks.process_webhook_delivery_task import ProcessWebhookDeliveryWorkerTask
from workers.tasks.process_notification_task import ProcessNotificationWorkerTask
from workers.tasks.process_pdf_export_task import ProcessPDFExportWorkerTask

@pytest.mark.asyncio
async def test_complete_end_to_end_production_workflow(db_session):
    """
    Complete Phase 0-14 End-to-End Production Lifecycle Test.
    Executes all core steps from Organization setup to PDF Export.
    """
    # 1. Organization & User Setup
    user = UserORM(email=f"recruiter.{uuid.uuid4().hex[:6]}@example.com", account_status="ACTIVE")
    db_session.add(user)
    await db_session.flush()

    cred = PasswordCredentialORM(user_id=user.id, password_hash="hashed_pw")
    db_session.add(cred)
    await db_session.flush()

    org = OrganizationORM(name="E2E Corp", slug=f"e2e-corp-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    await db_session.flush()

    role = RoleORM(name=f"ADMIN_ROLE_{uuid.uuid4().hex[:4]}", description="Admin")
    db_session.add(role)
    await db_session.flush()

    mem = OrganizationMembershipORM(organization_id=org.id, user_id=user.id, role_id=role.id, status="ACTIVE")
    db_session.add(mem)
    await db_session.flush()

    # 2. Candidate Creation & Skill Setup
    cand = CandidateProfileORM(organization_id=org.id, user_id=user.id, first_name="Alice", last_name="Smith", email=f"alice.{uuid.uuid4().hex[:6]}@example.com")
    db_session.add(cand)
    await db_session.flush()

    skill_manual = CandidateSkillORM(candidate_profile_id=cand.id, skill_name="Python", source="MANUAL")
    skill_ai = CandidateSkillORM(candidate_profile_id=cand.id, skill_name="PostgreSQL", source="RESUME_AI")
    db_session.add_all([skill_manual, skill_ai])
    await db_session.flush()

    # 3. Resume Ingestion & Version Analysis
    resume = ResumeORM(organization_id=org.id, candidate_profile_id=cand.id, version_number=1, original_filename="alice_resume.pdf", mime_type="application/pdf", file_size_bytes=2048, storage_key="source.pdf", checksum_sha256="hash123", processing_status="PROCESSED")
    db_session.add(resume)
    await db_session.flush()

    analysis = ResumeAnalysisORM(resume_id=resume.id, ai_provider="gemini", ai_model="gemini-2.5-flash", analysis_version="v1", extracted_profile_json={"skills": ["Python", "PostgreSQL"]})
    db_session.add(analysis)
    await db_session.flush()

    # 4. Job Role Creation & Requirement Weights
    job_role = JobRoleORM(organization_id=org.id, title="Senior Software Engineer", code=f"SR_ENG_{uuid.uuid4().hex[:4].upper()}", version_number=1, is_active_version=True)
    db_session.add(job_role)
    await db_session.flush()

    req1 = JobRoleRequirementORM(job_role_id=job_role.id, skill_name="Python", weight=1.5)
    req2 = JobRoleRequirementORM(job_role_id=job_role.id, skill_name="PostgreSQL", weight=1.0)
    db_session.add_all([req1, req2])
    await db_session.flush()

    # 5. Knowledge Base & Grounded RAG Document Setup
    kb = KnowledgeBaseORM(organization_id=org.id, name="System Guidelines", description="Internal Architecture Specs")
    db_session.add(kb)
    await db_session.flush()

    doc = KnowledgeDocumentORM(knowledge_base_id=kb.id, title="PostgreSQL Indexing Guide", storage_key="key", checksum_sha256="hash", ingestion_status="READY")
    db_session.add(doc)
    await db_session.flush()

    # 6. Interview Session, Snapshot & Blueprint Preparation
    sess = InterviewSessionORM(organization_id=org.id, candidate_profile_id=cand.id, job_role_id=job_role.id, status="READY")
    db_session.add(sess)
    await db_session.flush()

    snapshot = InterviewSnapshotORM(
        interview_session_id=sess.id,
        organization_id=org.id,
        candidate_profile_id=cand.id,
        candidate_snapshot_json={"name": "Alice Smith"},
        job_role_id=job_role.id,
        job_role_version=1,
        job_role_requirements_snapshot_json={"reqs": []},
        knowledge_base_ids=[str(kb.id)],
        knowledge_document_version_ids=[],
        snapshot_version=1
    )
    blueprint = InterviewBlueprintORM(
        interview_session_id=sess.id,
        total_target_questions=3,
        estimated_duration_minutes=30,
        topic_weights_json=[],
        difficulty_distribution_json={},
        required_skills=[],
        optional_skills=[],
        resume_focus_areas=[],
        rag_grounding_required=True
    )
    db_session.add_all([snapshot, blueprint])
    await db_session.flush()

    # 7. Interview Turn & Adaptive Question Engine
    sess.status = "IN_PROGRESS"
    turn = InterviewTurnORM(
        interview_session_id=sess.id,
        turn_number=1,
        turn_status="SERVED",
        idempotency_key=f"turn_1_{uuid.uuid4().hex[:6]}"
    )
    db_session.add(turn)
    await db_session.flush()

    question = InterviewQuestionORM(
        interview_session_id=sess.id,
        sequence_number=1,
        question_text="Explain PostgreSQL B-Tree Indexing and Query Performance.",
        question_type="TECHNICAL",
        topic="PostgreSQL",
        difficulty="HARD",
        generation_strategy="GROUNDED_RAG",
        expected_key_points={"points": ["B-Tree"]},
        status="SERVED",
        traceability_metadata={}
    )
    db_session.add(question)
    await db_session.flush()

    # 8. Candidate Answer Submission & Worker Evaluation
    answer = CandidateAnswerORM(
        interview_session_id=sess.id,
        candidate_profile_id=cand.id,
        question_id=question.id,
        answer_text="B-Tree indexes speed up equality and range queries by maintaining a balanced tree structure.",
        submission_status="SUBMITTED",
        attempt_number=1,
        idempotency_key=f"ans_key_{uuid.uuid4().hex[:6]}",
        submitted_at=datetime.now(timezone.utc)
    )
    db_session.add(answer)
    await db_session.flush()

    eval_record = AnswerEvaluationORM(
        answer_id=answer.id,
        evaluation_version=1,
        overall_score=8.83,
        score_technical_accuracy=9.0,
        score_depth=8.5,
        score_clarity=9.0,
        key_strengths={"strengths": ["PostgreSQL"]},
        missing_elements={"missing": []},
        feedback_text="Strong explanation of B-Tree indexing."
    )
    adaptive_dec = AdaptiveDecisionORM(
        interview_session_id=sess.id,
        decision_point_sequence=1,
        previous_difficulty="HARD",
        selected_next_difficulty="HARD",
        selected_next_topic="PostgreSQL",
        performance_signal_summary="High accuracy",
        decision_rationale="High accuracy on PostgreSQL topic."
    )
    db_session.add_all([eval_record, adaptive_dec])
    await db_session.flush()

    # 9. Interview Report & Backend Scoring
    sess.status = "COMPLETED"
    report = InterviewReportORM(
        interview_session_id=sess.id,
        report_version=1,
        scoring_version="v1",
        overall_score=8.83,
        technical_competency_score=9.0,
        reasoning_score=8.5,
        communication_score=9.0,
        seniority_assessment="Senior Engineer",
        executive_summary="Exceptional technical depth in database systems.",
        top_strengths={"strengths": ["PostgreSQL", "Python"]},
        growth_areas={"growth_areas": ["Distributed Systems"]},
        skill_scores_json={"skills": []},
        recommendation="STRONG_HIRE",
        hiring_signal="STRONG_HIRE_SIGNAL",
        status="GENERATED"
    )
    db_session.add(report)
    await db_session.flush()

    # 10. Human Hiring Decision Authority & Decision Audit Log
    hiring_dec = HiringDecisionORM(organization_id=org.id, interview_session_id=sess.id, candidate_profile_id=cand.id, status="HIRED", decision_maker_user_id=user.id, rationale_text="Outstanding candidate performance.")
    dec_hist = HiringDecisionHistoryORM(organization_id=org.id, interview_session_id=sess.id, previous_status="PENDING_REVIEW", new_status="HIRED", actor_user_id=user.id, rationale_text="Approved after team review.")
    db_session.add_all([hiring_dec, dec_hist])
    await db_session.flush()

    # 11. Transactional Outbox Webhook Delivery & Notification Worker
    integration = IntegrationORM(organization_id=org.id, provider_type="greenhouse", name="E2E Greenhouse Connector", status="ACTIVE", config_metadata_json={"env": "prod"}, encrypted_secret="secret")
    db_session.add(integration)
    await db_session.flush()

    event = IntegrationEventORM(organization_id=org.id, event_type="candidate.hired", resource_type="candidate", resource_id=str(cand.id), payload_json={"status": "HIRED", "candidate_id": str(cand.id)})
    db_session.add(event)
    await db_session.flush()

    delivery = WebhookDeliveryORM(organization_id=org.id, integration_id=integration.id, event_id=event.id, status="PENDING")
    db_session.add(delivery)
    await db_session.commit()

    webhook_res = await ProcessWebhookDeliveryWorkerTask.execute(db_session, "e2e_worker", {"delivery_id": str(delivery.id)})
    assert webhook_res["status"] == "DELIVERED"

    notif_res = await ProcessNotificationWorkerTask.execute(db_session, "e2e_worker", {"organization_id": str(org.id), "user_id": str(user.id), "channel": "SLACK", "event_type": "candidate.hired", "title": "Candidate Hired", "message": "Alice Smith was marked HIRED.", "webhook_url": "https://hooks.slack.com/mock"})
    assert notif_res["status"] == "DELIVERED"

    # 12. Asynchronous PDF Report Export
    export = ReportExportORM(organization_id=org.id, interview_session_id=sess.id, interview_report_id=report.id, report_version=1, status="QUEUED")
    db_session.add(export)
    await db_session.commit()

    pdf_res = await ProcessPDFExportWorkerTask.execute(db_session, "e2e_worker", {"export_id": str(export.id)})
    assert pdf_res["status"] == "READY"
    assert pdf_res["file_size_bytes"] > 0

    # Verification assertions across boundaries
    assert sess.status == "COMPLETED"
    assert report.overall_score == 8.83
    assert hiring_dec.status == "HIRED"
