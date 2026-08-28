# ADR 001: Adoption of Modular Monolith Architecture

## Status
Accepted

## Context
InterviewIQ is designed as a production-grade enterprise SaaS platform. We need an architectural style that allows rapid initial development, maintains strict domain boundaries, supports high developer velocity, and avoids the operational complexity, network latency overhead, and distributed transaction challenges of early microservices.

## Decision
We will build InterviewIQ as a **Modular Monolith** in Python (FastAPI).

The codebase will be organized into logical, self-contained modules (`apps/api/app/modules/<module_name>`). Each module will strictly enforce clean architecture layering:
- `api/`
- `application/`
- `domain/`
- `infrastructure/`

Modules will interact only through public application service interfaces or in-memory domain events. Direct database queries across module boundaries are strictly forbidden.

## Consequences

### Positive
- Simplified deployment pipeline (single container artifact).
- Zero network latency for inter-module service calls.
- Transactional consistency guarantees across related domain operations.
- Clear upgrade path: individual modules can be extracted into microservices if specific scaling bottlenecks emerge later.

### Negative / Trade-offs
- Requires discipline and linting to prevent developers from bypassing module boundaries.
- Monolithic deployment artifact requires restarting the entire API application on deployments.
