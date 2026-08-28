# ADR 046: Integration Provider Abstraction & Multi-Tenant Security

## Context
Integration with third-party ATS platforms (Greenhouse, Lever, Workday) must be organization-scoped and protected against credential leaks.

## Decision
1. All ATS integrations implement `IntegrationProvider` (`base.py`).
2. Integration credentials are encrypted/masked and NEVER returned in API GET responses or written to system logs.
3. Every integration query requires an active organization context.

## Consequences
- Clean separation of third-party integration logic from core domain use cases.
- Prevents cross-tenant credential leakage.
