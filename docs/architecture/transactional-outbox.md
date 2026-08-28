# Transactional Outbox Webhook Engine

## 1. Overview
InterviewIQ uses a **Transactional Outbox Pattern** (ADR 047) to guarantee reliable, asynchronous event delivery to external systems without fire-and-forget HTTP risks.

```text
Business Event Occurs (e.g. Hiring Decision Recorded)
                 ↓
Persist Business State + IntegrationEventORM (Single DB Transaction)
                 ↓
Background Worker Claims Delivery (SELECT ... FOR UPDATE SKIP LOCKED)
                 ↓
Execute Webhook Delivery & Persist DeliveryAttemptHistoryORM
```

## 2. Delivery Lifecycle & States
- `PENDING`: Created in database.
- `PROCESSING`: Claimed by background worker task (`ProcessWebhookDeliveryWorkerTask`).
- `DELIVERED`: Successfully acknowledged by provider.
- `RETRYING`: Transient error occurred; scheduled for exponential backoff retry.
- `DEAD_LETTER`: Max attempts reached (5/5); escalated for recruiter/admin inspection.
