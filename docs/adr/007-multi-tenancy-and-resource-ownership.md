# ADR 007: Multi-Tenancy Strategy and Organization Resource Scoping

## Status
Accepted

## Context
InterviewIQ is designed for multi-tenant enterprise SaaS operations. We must guarantee complete tenant data isolation, prevent cross-tenant data leaks, and establish unambiguous resource ownership rules across all domain entities.

## Decision
We enforce **Pooled Multi-Tenancy with Row-Level Tenant Scoping**.

1. **Organization Root**: Every tenant is represented by an `Organization` record.
2. **Mandatory Tenant Foreign Keys**: All tenant-scoped entities (`candidate_profiles`, `resumes`, `knowledge_bases`, `interview_sessions`, `background_jobs`, `audit_logs`) enforce mandatory `organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE`.
3. **Global Templates**: Entities such as `job_roles` allow an optional `organization_id`. If `organization_id IS NULL`, the entity represents a global system template accessible to all tenants; if set, it is private to that tenant.
4. **Token-Derived Tenant Context**: Client HTTP authorization derives `organization_id` strictly from verified JWT token claims processed in backend middleware. Client-supplied tenant ID overrides in request parameters are rejected.

## Consequences

### Positive
- Enterprise-grade tenant isolation preventing cross-organization data leakage.
- Simple, high-performance database execution model without requiring separate databases per tenant.

### Negative / Trade-offs
- Every relational table query must include explicit `organization_id` filters in SQL `WHERE` clauses.
