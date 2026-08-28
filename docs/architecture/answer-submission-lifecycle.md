# Answer Submission Lifecycle Architecture

## 1. Overview
The **Answer Submission Lifecycle** manages secure, candidate-grounded response ingestion, database-enforced immutability, submission idempotency protection (ADR 031), and durable background evaluation task handoff.

```
Candidate Answer Submission (POST /api/v1/interviews/{id}/questions/{q_id}/answer)
       ↓
Validate Organization Scope, Active IN_PROGRESS State & Candidate Identity
       ↓
Database Unique Constraint Check (uq_candidate_answer_idempotency)
       ↓
Persist Immutable CandidateAnswerORM (submission_status = 'SUBMITTED')
       ↓
Update InterviewTurnORM (turn_status = 'ANSWER_SUBMITTED')
       ↓
Enqueue Background Job (job_type = 'ANSWER_EVALUATION', status = 'QUEUED')
       ↓
Emit Audit Log Event ('answer.submitted')
       ↓
Return Immediate Stable HTTP 201 Response
```

## 2. Security & Immutability Rules
- **Candidate Ownership**: Candidate users can only submit answers to interview sessions where `session.candidate_profile_id == user.candidate_profile_id`.
- **Session State Rule**: Answer submissions are rejected if `interview_session.status != 'IN_PROGRESS'`.
- **Immutability Enforcement**: `before_update` SQLAlchemy event listener on `CandidateAnswerORM` blocks any field mutations. Answer revisions must create a new attempt or version.
