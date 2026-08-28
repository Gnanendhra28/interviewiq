# Recruiter Workflow UX Architecture

## 1. Overview
The recruiter portal provides end-to-end management from dashboard metrics to candidate pipeline, resume upload, job role versioning, grounded RAG knowledge bases, interview creation, report evaluation, and human hiring decisions.

## 2. Key Pages & Workflows
- `/recruiter/dashboard`: Operational KPIs, pipeline state counts, audit trail.
- `/recruiter/candidates`: Paginated candidate pipeline, search, signal/decision filters.
- `/recruiter/candidates/[id]`: Profile details, skill provenance badges (`MANUAL` vs `RESUME_AI`), resume upload with polling status, timeline, human decision form.
- `/recruiter/candidates/compare`: Side-by-side comparison matrix for up to 5 candidates.
- `/recruiter/interviews/[id]/report`: Detailed report review, requirement scorecards, decision support, human hiring decision form.
- `/recruiter/review-queue`: Actionable recruiter review queue.
