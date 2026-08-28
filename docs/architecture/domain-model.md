# InterviewIQ Domain Model Specification

## Domain Architecture Overview

InterviewIQ's domain model represents an enterprise AI-powered adaptive technical interview platform organized into 12 consolidated bounded contexts. The system of record is PostgreSQL, enforcing strict relational integrity, multi-tenant organization boundaries, model-aware vector representations, and immutable state/analysis provenance.

```mermaid
erDiagram
    Organization ||--o{ UserMembership : "has"
    User ||--o{ UserMembership : "belongs_to"
    User ||--o1 PasswordCredential : "authenticated_by"
    User ||--o{ AuthSession : "maintains"
    
    Organization ||--o{ CandidateProfile : "owns"
    User ||--o| CandidateProfile : "links_to"
    CandidateProfile ||--o{ Resume : "submits"
    Resume ||--o{ ResumeAnalysis : "analyzed_by"
    
    Organization ||--o{ JobRole : "defines"
    JobRole ||--o{ JobRoleRequirement : "requires"
    
    Organization ||--o{ KnowledgeBase : "owns"
    KnowledgeBase ||--o{ KnowledgeDocument : "contains"
    KnowledgeDocument ||--o{ KnowledgeDocumentVersion : "versioned_as"
    KnowledgeDocumentVersion ||--o{ KnowledgeChunk : "split_into"
    KnowledgeChunk ||--o{ KnowledgeEmbedding : "embedded_in"
    
    Organization ||--o{ InterviewSession : "governs"
    CandidateProfile ||--o{ InterviewSession : "undergoes"
    JobRole ||--o{ InterviewSession : "targets"
    InterviewSession ||--o{ InterviewStateHistory : "logs"
    InterviewSession ||--o{ InterviewQuestion : "presents"
    
    InterviewQuestion ||--o{ CandidateAnswer : "answered_by"
    CandidateAnswer ||--o{ AnswerEvaluation : "evaluated_by"
    InterviewSession ||--o{ AdaptiveDecision : "adapts_via"
    InterviewSession ||--o| InterviewReport : "produces"
```

## Bounded Context Entity Summary

1. **Identity (`identity`)**: `User`, `PasswordCredential`, `AuthenticationSession`, `EmailVerification`, `PasswordReset`.
2. **Organizations (`organizations`)**: `Organization`, `Role`, `Permission`, `RolePermission`, `OrganizationMembership`, `OrganizationInvitation`.
3. **Candidates (`candidates`)**: `CandidateProfile`, `CandidateSkill`, `CandidateExperience`, `CandidateEducation`.
4. **Resumes (`resumes`)**: `Resume`, `ResumeAnalysis`.
5. **Job Roles (`job_roles`)**: `JobRole`, `JobRoleRequirement`.
6. **Knowledge & RAG (`knowledge_rag`)**: `KnowledgeBase`, `KnowledgeDocument`, `KnowledgeDocumentVersion`, `KnowledgeChunk`, `KnowledgeEmbedding`.
7. **Interviews (`interviews`)**: `InterviewSession`, `InterviewStateHistory`.
8. **Interview Intelligence (`interview_intelligence`)**: `InterviewQuestion`, `CandidateAnswer`, `AnswerEvaluation`, `AdaptiveDecision`.
9. **Reports (`reports`)**: `InterviewReport`.
10. **Background Jobs (`background_jobs`)**: `BackgroundJob`.
11. **Audit Logging (`audit_logging`)**: `AuditLog`.
12. **Shared Platform (`shared`)**: Base ORM contracts, UUID mixins, timestamp standards.
