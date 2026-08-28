# Hiring Decision Workflow Architecture

## 1. Overview
The **Hiring Decision Workflow** manages human hiring decisions (`PENDING_REVIEW`, `SHORTLISTED`, `HIRED`, `REJECTED`, `ON_HOLD`) while enforcing strict separation between AI decision-support signals and human decision authority (ADR 039).

```
Recruiter / Admin Action (POST /api/v1/interviews/{id}/decision)
       ↓
Validate Recruiter Scope & Role Authority (Candidate Denial)
       ↓
Update / Persist HiringDecisionORM (System of Record)
       ↓
Append Immutable HiringDecisionHistoryORM Record (ADR 040)
  - previous_status, new_status, actor_user_id, rationale_text, timestamp
       ↓
Emit Audit Log ('interview.human_decision_recorded')
```

## 2. Immutability & Auditability
- Decision history records (`HiringDecisionHistoryORM`) are append-only.
- `before_update` and `before_delete` listeners prevent history record modification or deletion.
