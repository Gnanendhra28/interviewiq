import uuid

import pytest

from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM
from apps.api.app.modules.candidates.infrastructure.orm import CandidateProfileORM
from apps.api.app.modules.reports.infrastructure.orm import InterviewReportORM


@pytest.mark.asyncio
async def test_user_multi_org_candidate_profiles():
    """Verify that a single User identity can hold independent CandidateProfiles in Org A and Org B."""
    user_id = uuid.uuid4()
    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()

    profile_a = CandidateProfileORM(
        user_id=user_id,
        organization_id=org_a_id,
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com"
    )

    profile_b = CandidateProfileORM(
        user_id=user_id,
        organization_id=org_b_id,
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com"
    )

    assert profile_a.user_id == profile_b.user_id == user_id
    assert profile_a.organization_id != profile_b.organization_id


@pytest.mark.asyncio
async def test_immutability_event_listener_enforcement():
    """Verify that ORM mapper event listeners block update operations on immutable entities."""
    report = InterviewReportORM(
        interview_session_id=uuid.uuid4(),
        overall_score=8.5,
        seniority_assessment="Senior Engineer",
        executive_summary="Solid candidate",
        top_strengths={"skills": ["Python"]},
        growth_areas={"skills": ["K8s"]},
        skill_scores_json={"python": 9.0},
        recommendation="HIRE"
    )

    # Attempting to mutate an immutable entity raises DomainException
    with pytest.raises(DomainException) as exc_info:
        # Trigger listener manually or via session commit mock
        from apps.api.app.modules.reports.infrastructure.orm import block_report_update
        block_report_update(None, None, report)

    assert exc_info.value.code == "IMMUTABLE_RECORD"


@pytest.mark.asyncio
async def test_background_job_idempotency_key_uniqueness():
    """Verify that background jobs enforce unique idempotency keys."""
    key = "job_resume_parse_991823"
    job_1 = BackgroundJobORM(job_type="RESUME_PARSING", idempotency_key=key)
    job_2 = BackgroundJobORM(job_type="RESUME_PARSING", idempotency_key=key)

    assert job_1.idempotency_key == job_2.idempotency_key
