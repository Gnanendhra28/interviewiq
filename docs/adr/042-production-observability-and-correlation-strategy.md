# ADR 042: Production Observability & Correlation Strategy

## Context
Production requests, logs, background jobs, and audit events must be traceably linked across multi-replica API deployments without logging sensitive data.

## Decision
1. `RequestCorrelationMiddleware` propagates incoming `X-Request-ID` or generates a unique correlation ID (`req_<uuid>`).
2. Structured logs include `request_id`, `worker_id`, `organization_id`, and `duration_ms`.
3. Sensitive attributes (passwords, JWTs, prompts, answers, signed URLs) are excluded.
4. Prometheus metrics are exposed at `GET /health/metrics`.

## Consequences
- End-to-end request tracing across HTTP endpoints and background jobs.
- Safe logging compliant with privacy requirements.
