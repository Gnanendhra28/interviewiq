# ADR 041: Recruiter Command Center Query Architecture

## Context
Recruiter dashboard operational metrics, candidate pipeline search, and review queues must deliver real-time authoritative metrics without separate eventually-consistent datastores.

## Decision
1. Calculate dashboard metrics directly via SQL database aggregations (`COUNT()`, `GROUP BY`).
2. Paginate pipeline queries at the SQL level (`OFFSET`, `LIMIT`).
3. Enforce multi-tenant scoping (`organization_id = ctx.organization_id`) across all SQL queries and JOINs.

## Consequences
- Guaranteed real-time consistency with authoritative database state.
- Zero risk of eventual-consistency drift or out-of-sync cache invalidation bugs.
