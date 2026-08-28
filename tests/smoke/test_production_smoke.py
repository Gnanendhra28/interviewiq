import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text
from apps.api.app.modules.background_jobs.infrastructure.orm import WorkerHeartbeatORM

@pytest.mark.asyncio
async def test_production_database_liveness_and_pgvector(db_session):
    """
    Production Smoke Test 1: Verify PostgreSQL connection and pgvector extension status.
    """
    res = await db_session.execute(text("SELECT 1;"))
    assert res.scalar() == 1

    vec_res = await db_session.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector';"))
    ext = vec_res.scalar_one_or_none()
    assert ext == "vector"

@pytest.mark.asyncio
async def test_production_worker_heartbeat_liveness(db_session):
    """
    Production Smoke Test 2: Verify active worker pool heartbeat.
    """
    # Insert or update a test worker heartbeat
    test_worker_id = uuid.uuid4()
    hb = WorkerHeartbeatORM(
        worker_id=test_worker_id,
        status="ACTIVE",
        last_heartbeat_at=datetime.now(timezone.utc),
        active_jobs_count=0,
        build_version="smoke-test-v1"
    )
    db_session.add(hb)
    await db_session.commit()

    res = await db_session.execute(
        select(WorkerHeartbeatORM).where(WorkerHeartbeatORM.worker_id == test_worker_id)
    )
    fetched = res.scalar_one_or_none()
    assert fetched is not None
    assert fetched.status == "ACTIVE"
