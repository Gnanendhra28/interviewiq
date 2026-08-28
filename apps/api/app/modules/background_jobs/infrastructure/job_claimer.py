import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.logging import logger
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM


class JobClaimer:
    """
    Production-grade reliable database job claimer with explicit worker lease ownership semantics.
    Uses PostgreSQL SELECT ... FOR UPDATE SKIP LOCKED to prevent double-claiming across worker replicas.
    Implements worker identity tracking (claimed_by) and lease expiration (lease_expires_at) to prevent
    stalled workers from overwriting active claims (ADR 024).
    """

    @staticmethod
    async def claim_next_job(
        db: AsyncSession,
        job_type: str = "RESUME_PARSING",
        worker_id: Optional[uuid.UUID] = None,
        lease_duration_seconds: int = 600
    ) -> Optional[BackgroundJobORM]:
        claimed_worker_id = worker_id or uuid.uuid4()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=lease_duration_seconds)

        # Atomic claim using SKIP LOCKED
        stmt = (
            select(BackgroundJobORM)
            .where(
                BackgroundJobORM.job_type == job_type,
                BackgroundJobORM.status == "QUEUED"
            )
            .order_by(BackgroundJobORM.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()

        if not job:
            return None

        # Transition job to RUNNING with worker identity lease
        job.status = "RUNNING"
        job.claimed_by = claimed_worker_id
        job.lease_expires_at = expires_at
        job.started_at = now
        job.attempts += 1

        await db.commit()
        logger.info(f"[JOB CLAIMER] Worker {claimed_worker_id} claimed job {job.id} (type: {job.job_type}, attempt {job.attempts}/{job.max_attempts}, lease expires: {expires_at.isoformat()})")
        return job

    @staticmethod
    async def recover_stale_jobs(db: AsyncSession, lease_timeout_minutes: int = 10) -> int:
        now = datetime.now(timezone.utc)
        threshold = now - timedelta(minutes=lease_timeout_minutes)

        # Find jobs running with expired leases or stale start times
        stmt = select(BackgroundJobORM).where(
            BackgroundJobORM.status == "RUNNING",
            (
                (BackgroundJobORM.lease_expires_at.isnot(None) & (BackgroundJobORM.lease_expires_at < now)) |
                (BackgroundJobORM.lease_expires_at.is_(None) & (BackgroundJobORM.started_at < threshold))
            )
        )
        res = await db.execute(stmt)
        stale_jobs = res.scalars().all()
        recovered_count = 0

        for job in stale_jobs:
            job.claimed_by = None
            job.lease_expires_at = None
            if job.attempts < job.max_attempts:
                logger.warning(f"[STALE JOB RECOVERY] Resetting crashed job {job.id} back to QUEUED (attempts: {job.attempts})")
                job.status = "QUEUED"
            else:
                logger.error(f"[STALE JOB RECOVERY] Terminal failure for crashed job {job.id} (max attempts reached)")
                job.status = "FAILED"
                job.error_message = "Worker crash recovery: lease timeout exceeded"
                job.completed_at = now
            recovered_count += 1

        if recovered_count > 0:
            await db.commit()

        return recovered_count
