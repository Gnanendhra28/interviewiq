import uuid

import pytest

from apps.api.app.modules.interviews.infrastructure.orm import (
    InterviewSessionORM,
    InterviewSessionStatus,
    InterviewStateHistoryORM,
)


@pytest.mark.asyncio
async def test_interview_session_orm_instantiation():
    session_id = uuid.uuid4()
    org_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    role_id = uuid.uuid4()

    session = InterviewSessionORM(
        id=session_id,
        organization_id=org_id,
        candidate_profile_id=candidate_id,
        job_role_id=role_id,
        status=InterviewSessionStatus.CREATED,
        version_number=1
    )

    assert session.id == session_id
    assert session.status == InterviewSessionStatus.CREATED
    assert session.version_number == 1


@pytest.mark.asyncio
async def test_interview_state_history_orm():
    session_id = uuid.uuid4()
    history = InterviewStateHistoryORM(
        interview_session_id=session_id,
        previous_status="CREATED",
        new_status="RESUME_PENDING",
        transition_reason="Resume PDF uploaded by candidate",
        actor_type="CANDIDATE"
    )

    assert history.previous_status == "CREATED"
    assert history.new_status == "RESUME_PENDING"
    assert history.actor_type == "CANDIDATE"
