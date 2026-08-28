import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.api.app.core.config import settings
from apps.api.app.core.database import AsyncSessionLocal
from apps.api.app.core.rate_limiter import DistributedRateLimiter
from apps.api.app.main import app
from apps.api.app.modules.background_jobs.infrastructure.orm import WorkerHeartbeatORM
from workers.job_runner import WORKER_ID, update_worker_heartbeat

client = TestClient(app)


def test_liveness_endpoint():
    res = client.get("/health/live")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "live"
    assert "environment" in data


def test_readiness_endpoint():
    res = client.get("/health/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"


def test_prometheus_metrics_endpoint():
    res = client.get("/health/metrics")
    assert res.status_code == 200
    assert "# TYPE api_requests_total counter" in res.text


def test_request_correlation_id_middleware():
    custom_req_id = "test_corr_12345"
    res = client.get("/health/live", headers={"X-Request-ID": custom_req_id})
    assert res.status_code == 200
    assert res.headers.get("X-Request-ID") == custom_req_id

    # Auto-generation test
    res2 = client.get("/health/live")
    assert res2.status_code == 200
    assert res2.headers.get("X-Request-ID").startswith("req_")


def test_security_headers_middleware():
    res = client.get("/health/live")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert res.headers.get("Content-Security-Policy") == "default-src 'self'"


def test_distributed_rate_limiter():
    limiter = DistributedRateLimiter()
    key = "test_client_ip:/api/v1/auth/login"
    
    # Send requests up to limit 3
    is_limited, rem, retry = limiter.is_rate_limited(key, max_requests=3, window_seconds=60)
    assert is_limited is False
    
    is_limited, rem, retry = limiter.is_rate_limited(key, max_requests=3, window_seconds=60)
    assert is_limited is False

    is_limited, rem, retry = limiter.is_rate_limited(key, max_requests=3, window_seconds=60)
    assert is_limited is False

    # 4th request should trigger rate limit
    is_limited, rem, retry = limiter.is_rate_limited(key, max_requests=3, window_seconds=60)
    assert is_limited is True
    assert retry > 0


@pytest.mark.asyncio
async def test_worker_heartbeat_registration_and_update():
    await update_worker_heartbeat(active_jobs=2, status_str="ACTIVE")

    async with AsyncSessionLocal() as db_session:
        res = await db_session.execute(select(WorkerHeartbeatORM).where(WorkerHeartbeatORM.worker_id == WORKER_ID))
        hb = res.scalar_one_or_none()
        assert hb is not None
        assert hb.status == "ACTIVE"
        assert hb.active_jobs_count == 2


def test_fail_fast_production_config_validation():
    # Insecure secret key check
    test_settings = settings.model_copy()
    test_settings.ENVIRONMENT = "production"
    test_settings.SECRET_KEY = "short"

    with pytest.raises(ValueError, match="Insecure SECRET_KEY"):
        test_settings.validate_production_configuration()

    # Wildcard origin check
    test_settings2 = settings.model_copy()
    test_settings2.ENVIRONMENT = "production"
    test_settings2.SECRET_KEY = "valid_production_secret_key_32_chars_long_and_secure"
    test_settings2.DATABASE_URL = "postgresql+asyncpg://interviewiq:prod_pass@localhost:5433/db"
    test_settings2.ALLOWED_ORIGINS = ["*"]

    with pytest.raises(ValueError, match=r"Wildcard '\*' ALLOWED_ORIGINS forbidden"):
        test_settings2.validate_production_configuration()
