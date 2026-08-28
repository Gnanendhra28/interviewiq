import os

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.config import settings
from apps.api.app.core.database import get_db_session
from apps.api.app.core.dependencies import get_active_org_context, get_db
from apps.api.app.core.metrics import metrics_collector
from apps.api.app.modules.background_jobs.infrastructure.orm import (
    BackgroundJobORM,
    WorkerHeartbeatORM,
)

health_router = APIRouter(prefix="/health", tags=["Health & Observability"])


@health_router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """Liveness probe: verifies process is running without external service dependencies."""
    return {"status": "live", "environment": settings.ENVIRONMENT}


@health_router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(response: Response):
    """Readiness probe: verifies PostgreSQL connectivity and local storage paths."""
    errors = []

    # 1. Verify PostgreSQL Database Connectivity
    try:
        async for db in get_db_session():
            await db.execute(text("SELECT 1"))
            break
    except Exception as e:
        errors.append(f"PostgreSQL connection error: {str(e)}")

    # 2. Verify Storage Location
    if settings.STORAGE_PROVIDER == "local":
        if not os.path.exists(settings.STORAGE_LOCAL_PATH):
            try:
                os.makedirs(settings.STORAGE_LOCAL_PATH, exist_ok=True)
            except Exception as e:
                errors.append(f"Storage path creation failed: {str(e)}")

    if errors:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unhealthy", "errors": errors}

    return {"status": "ready", "environment": settings.ENVIRONMENT}


@health_router.get("/metrics", response_class=PlainTextResponse)
async def metrics_endpoint():
    """Prometheus-compatible scraping endpoint."""
    return metrics_collector.export_metrics_prometheus()


@health_router.get("/operational", status_code=status.HTTP_200_OK)
async def operational_health(
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    """Authenticated operational administrative status check (ADR 044)."""
    # Active Workers & Heartbeats
    hb_res = await db.execute(select(WorkerHeartbeatORM).order_by(WorkerHeartbeatORM.last_heartbeat_at.desc()))
    workers = [
        {
            "worker_id": str(w.worker_id),
            "status": w.status,
            "last_heartbeat_at": w.last_heartbeat_at.isoformat(),
            "active_jobs_count": w.active_jobs_count
        } for w in hb_res.scalars().all()
    ]

    # Queue Depths by Job Type
    q_res = await db.execute(
        select(BackgroundJobORM.job_type, BackgroundJobORM.status, func.count(BackgroundJobORM.id))
        .group_by(BackgroundJobORM.job_type, BackgroundJobORM.status)
    )
    queue_depths = {}
    for jtype, jstatus, count in q_res.all():
        if jtype not in queue_depths:
            queue_depths[jtype] = {}
        queue_depths[jtype][jstatus] = count

    return {
        "database_status": "CONNECTED",
        "active_workers_count": len(workers),
        "workers": workers,
        "queue_depths": queue_depths
    }
