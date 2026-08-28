import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from apps.api.app.modules.background_jobs.infrastructure.job_claimer import JobClaimer
from apps.api.app.modules.background_jobs.infrastructure.orm import (
    BackgroundJobORM,
)
from apps.api.app.modules.integrations.infrastructure.orm import (
    IntegrationEventORM,
    IntegrationORM,
    WebhookDeliveryORM,
)
from workers.tasks.process_webhook_delivery_task import ProcessWebhookDeliveryWorkerTask


@pytest.mark.asyncio
async def test_worker_skip_locked_claiming_concurrency(db_session):
    job1 = BackgroundJobORM(organization_id=None, job_type="RESUME_PARSING", payload_metadata={"resume_id": str(uuid.uuid4())}, idempotency_key=f"key_{uuid.uuid4().hex}", status="QUEUED")
    job2 = BackgroundJobORM(organization_id=None, job_type="RESUME_PARSING", payload_metadata={"resume_id": str(uuid.uuid4())}, idempotency_key=f"key_{uuid.uuid4().hex}", status="QUEUED")
    db_session.add_all([job1, job2])
    await db_session.commit()

    # Claim job using JobClaimer
    worker_1_uuid = uuid.uuid4()
    worker_2_uuid = uuid.uuid4()
    claimed_job_1 = await JobClaimer.claim_next_job(db_session, job_type="RESUME_PARSING", worker_id=worker_1_uuid)
    assert claimed_job_1 is not None
    assert claimed_job_1.status == "RUNNING"

    # Second claim should pick up job2, not job1
    claimed_job_2 = await JobClaimer.claim_next_job(db_session, job_type="RESUME_PARSING", worker_id=worker_2_uuid)
    assert claimed_job_2 is not None
    assert claimed_job_2.id != claimed_job_1.id
    assert claimed_job_2.status == "RUNNING"

@pytest.mark.asyncio
async def test_worker_stale_lease_recovery(db_session):
    crashed_worker_uuid = uuid.uuid4()
    crashed_job = BackgroundJobORM(
        organization_id=None,
        job_type="RESUME_PARSING",
        payload_metadata={"resume_id": str(uuid.uuid4())},
        idempotency_key=f"key_{uuid.uuid4().hex}",
        status="RUNNING",
        claimed_by=crashed_worker_uuid,
        lease_expires_at=datetime.now(timezone.utc) - timedelta(minutes=15) # Expired lease
    )
    db_session.add(crashed_job)
    await db_session.commit()

    # Run stale recovery
    recovered_count = await JobClaimer.recover_stale_jobs(db_session, lease_timeout_minutes=10)
    assert recovered_count >= 1

    # Re-fetch job; status should be reset to QUEUED
    await db_session.refresh(crashed_job)
    assert crashed_job.status == "QUEUED"
    assert crashed_job.claimed_by is None

@pytest.mark.asyncio
async def test_webhook_delivery_dead_letter_escalation(db_session):
    org_id = uuid.uuid4()
    integration = IntegrationORM(organization_id=org_id, provider_type="greenhouse", name="Failing Greenhouse Integration", status="ACTIVE")
    db_session.add(integration)
    await db_session.flush()

    event = IntegrationEventORM(organization_id=org_id, event_type="candidate.hired", resource_type="candidate", resource_id=str(uuid.uuid4()), payload_json={})
    db_session.add(event)
    await db_session.flush()

    delivery = WebhookDeliveryORM(organization_id=org_id, integration_id=integration.id, event_id=event.id, status="PENDING", attempts=4, max_attempts=5)
    db_session.add(delivery)
    await db_session.commit()

    with patch("apps.api.app.modules.integrations.infrastructure.providers.greenhouse.GreenhouseProvider.deliver_interview_report", side_effect=Exception("External ATS HTTP 500 Network Failure")):
        res = await ProcessWebhookDeliveryWorkerTask.execute(db_session, "worker_retry", {"delivery_id": str(delivery.id)})
    
    assert res["status"] == "RETRYING" or "error" in res

    await db_session.refresh(delivery)
    assert delivery.status == "DEAD_LETTER"
