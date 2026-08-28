# InterviewIQ Data Flow Specification

This document details the end-to-end data processing pipelines across the InterviewIQ system, from candidate onboarding to final report synthesis.

## End-to-End Interview Data Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor Candidate
    participant Web as Web Frontend (Next.js)
    participant API as API Layer (FastAPI)
    participant Worker as Background Worker (Redis)
    participant Storage as Storage Provider (Local/GCS)
    participant DB as PostgreSQL + pgvector
    participant AI as AI Provider (Gemini)

    Candidate->>Web: 1. Upload Resume PDF
    Web->>API: 2. POST /api/v1/resumes/upload
    API->>Storage: 3. Store raw PDF file
    API->>DB: 4. Create Resume record (status: RESUME_PENDING)
    API->>Worker: 5. Dispatch async resume processing job
    API-->>Web: 6. Return Resume ID & job status

    Worker->>Storage: 7. Fetch raw PDF file
    Worker->>AI: 8. Call AIProvider.analyze_resume(file_bytes)
    AI-->>Worker: 9. Return structured CandidateProfile JSON
    Worker->>DB: 10. Persist CandidateProfile & set Resume status (PROFILE_READY)

    Candidate->>Web: 11. Select Job Role & Request Interview Start
    Web->>API: 12. POST /api/v1/interviews/start
    API->>DB: 13. Create InterviewSession (state: IN_PROGRESS)

    loop Interview Question & Answer Cycle
        API->>AI: 14. Query RAG vector chunks & generate adaptive question
        AI-->>API: 15. Return structured InterviewQuestion JSON
        API->>DB: 16. Persist Question & Traceability Metadata
        API-->>Web: 17. Render Question to Candidate
        Candidate->>Web: 18. Submit Answer
        Web->>API: 19. POST /api/v1/interviews/{id}/answers
        API->>AI: 20. Call AIProvider.evaluate_answer(...)
        AI-->>API: 21. Return EvaluationResult JSON & Adaptive Next Action
        API->>DB: 22. Persist Evaluation & Update Adaptive State
    end

    API->>Worker: 23. Dispatch Final Report synthesis job
    Worker->>AI: 24. Call AIProvider.generate_report(...)
    Worker->>DB: 25. Store Final InterviewReport & transition state to COMPLETED
    Web->>API: 26. GET /api/v1/interviews/{id}/report
    API-->>Web: 27. Return detailed report
```

## Data Traceability Guarantees

Every generated question preserves explicit traceability context stored in `interview_questions.traceability_metadata`:

```json
{
  "question_id": "q_8f7b2a",
  "interview_session_id": "ses_9918a",
  "resume_signals": ["5 years Python", "FastAPI microservices", "Postgres optimization"],
  "target_role": "Senior Backend Engineer",
  "selected_topic": "Database Indexing & Query Optimization",
  "retrieved_chunks": [
    {
      "chunk_id": "chk_1042",
      "document_id": "doc_pg_perf",
      "similarity_score": 0.892,
      "section": "B-Tree vs GIN Indexes"
    }
  ],
  "difficulty": "HARD",
  "generation_strategy": "SCENARIO_BASED_DEBUGGING"
}
```
