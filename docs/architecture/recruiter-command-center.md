# Recruiter Command Center Architecture

## 1. Overview
The **Recruiter Command Center** provides organization-scoped operational metrics, candidate pipeline status, pending hiring reviews, and recent activity directly from authoritative database state (ADR 041).

```
GET /api/v1/recruiter/dashboard
       ↓
AuthorizationContext Scope Enforcement (organization_id = ctx.organization_id)
       ↓
Authoritative PostgreSQL SQL Query Aggregations:
  - Active Job Roles Count (JobRoleORM)
  - Active Candidates Count (CandidateProfileORM)
  - Interview Status Grouping (InterviewSessionORM)
  - Completed Reports Count (InterviewReportORM)
  - Pending Reviews Count (HiringDecisionORM)
  - Audit Trail Activity Stream (AuditLogORM)
       ↓
Structured Dashboard Response JSON
```

## 2. Security & Isolation
- Access restricted exclusively to authorized organization recruiters and admins.
- Candidate users receive `403 Forbidden`.
