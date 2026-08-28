# Monitoring & Metrics Guide

## 1. Metrics Endpoints
- `GET /health/live`: Liveness probe (process alive).
- `GET /health/ready`: Readiness probe (PostgreSQL & storage readiness).
- `GET /health/metrics`: Prometheus metric scrape endpoint.
- `GET /health/operational`: Authenticated admin status (worker heartbeats, queue depths).

## 2. Key Prometheus Metrics
- `api_requests_total`: Total HTTP requests partitioned by status class.
- `api_errors_total`: Total 4xx/5xx HTTP error responses.
- `job_completed_total`: Background job processing completions by job type.
- `ai_requests_total`: Total AI Provider inference calls.

## 3. Recommended Alerts
- **Alert 1: High API 5xx Error Rate**: `rate(api_errors_total[5m]) / rate(api_requests_total[5m]) > 0.05` for $> 2 \text{ mins}$.
- **Alert 2: Stale Background Worker**: No heartbeat in `WorkerHeartbeatORM` within 5 minutes.
- **Alert 3: Queue Depth Accumulation**: `QUEUED` jobs $> 100$ for $> 15 \text{ mins}$.
