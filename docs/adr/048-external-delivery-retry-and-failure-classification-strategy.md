# ADR 048: External Delivery Retry & Failure Classification Strategy

## Context
Webhook delivery errors must distinguish transient network errors from permanent configuration failures.

## Decision
1. Transient failures (HTTP 429, 5xx, timeouts) use exponential backoff retries up to 5 attempts.
2. Permanent failures transition to `DEAD_LETTER` state for recruiter review.
3. External delivery failures NEVER roll back or invalidate internal `HiringDecisionORM` state.

## Consequences
- Prevents infinite retry loops.
- Preserves internal hiring authority system of record.
