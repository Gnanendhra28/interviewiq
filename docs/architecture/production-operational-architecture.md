# Production Operational Architecture

## 1. Overview
The **Production Operational Architecture** equips InterviewIQ with fail-fast configuration validation, request correlation tracing, security headers, distributed API rate limiting, worker heartbeat operational tracking, and central safe error handling.

```
Incoming Request
       ↓
SecurityHeadersMiddleware (nosniff, HSTS, CSP, X-Frame-Options)
       ↓
RequestCorrelationMiddleware (Assigns/propagates X-Request-ID)
       ↓
DistributedRateLimiter Check (429 Too Many Requests if exceeded)
       ↓
FastAPI Application Services & Domain Handlers
       ↓
Database / Storage Execution
       ↓
Central Error Handler (Returns safe JSON error + request_id; hides tracebacks)
```

## 2. Worker Operational Topology
- API process and background worker processes share PostgreSQL for durable job claiming (`SELECT ... FOR UPDATE SKIP LOCKED`).
- Workers emit heartbeats (`WorkerHeartbeatORM`) on every poll step.
- Dead or crashed worker leases automatically expire after 10 minutes, allowing healthy workers to safely recover stuck jobs.
