# ADR 037: Human-Centered Recruiter Decision Support

## Context
Automated hiring decision intelligence must assist human recruiters without operating as an autonomous decision system.

## Decision
1. System outputs hiring recommendations as decision support signals (`STRONG_HIRE_SIGNAL`, `HIRE_SIGNAL`, `MIXED_SIGNAL`, `NO_HIRE_SIGNAL`, `INSUFFICIENT_EVIDENCE`).
2. Decision support views (`GET /api/v1/interviews/{id}/decision-support`) are restricted exclusively to recruiter and admin roles. Candidate users receive `403 Forbidden`.
3. Final candidate hiring decisions (`HIRED`, `REJECTED`) remain under human recruiter control.

## Consequences
- Responsible AI governance compliant with enterprise human-in-the-loop policies.
- Role-scoped privacy protection for internal evaluation metrics.
