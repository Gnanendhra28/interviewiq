# ADR 047: Transactional Outbox Pattern for Reliable Webhook Delivery

## Context
External webhook deliveries must be resilient to network failures without performing synchronous fire-and-forget HTTP requests inside business transactions.

## Decision
1. Business events write outbound records (`IntegrationEventORM` and `WebhookDeliveryORM`) inside the primary database transaction.
2. Background workers claim pending deliveries via `SELECT ... FOR UPDATE SKIP LOCKED` and dispatch them asynchronously.

## Consequences
- Guaranteed event persistence even during external ATS downtime.
- Protects API response latencies.
