# Recruiter Decision Support Architecture

## 1. Overview
The **Recruiter Decision Support** capability (ADR 037) exposes hiring signals, requirement scorecards, and risk assessments exclusively to authorized recruiter and organization admin roles (`GET /api/v1/interviews/{id}/decision-support`).

## 2. Decision Support Privacy & Visibility Boundary
- Candidate users receive `403 Forbidden` when accessing decision support endpoints.
- Hiring signals (`STRONG_HIRE_SIGNAL`, `HIRE_SIGNAL`, `MIXED_SIGNAL`, `NO_HIRE_SIGNAL`, `INSUFFICIENT_EVIDENCE`) serve as non-autonomous recruiter decision support.
- Final hiring status updates (`HIRED`, `REJECTED`) are reserved for authorized human recruiters.
