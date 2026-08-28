# ADR 043: Distributed API Rate Limiting Strategy

## Context
API endpoints (especially Auth, Resume/Doc Uploads, and Gemini AI operations) must be protected against abuse across multi-replica deployments. Single-instance in-memory limiters are inadequate for distributed systems.

## Decision
1. `DistributedRateLimiter` enforces sliding window rate limiting per IP and path category (`auth`, `upload`, `ai`, `default`).
2. Supports Redis store or shared sliding window dictionary across API replicas.
3. Exceeding limits returns HTTP 429 `Too Many Requests` with `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `Retry-After`.

## Consequences
- Protection against credential brute-forcing, upload denial-of-service, and AI quota exhaustion.
- Multi-replica deployment safety.
