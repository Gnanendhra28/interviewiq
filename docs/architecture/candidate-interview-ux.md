# Candidate Interview UX Architecture

## 1. Overview
The candidate interface (`app/candidate/interview/[id]/page.tsx`) provides a focused, simple, distraction-free environment for answering technical adaptive questions.

## 2. Idempotency & Safety
- **Idempotency Key**: Automatically generates a unique `idempotency_key` per turn to prevent duplicate answer submissions.
- **Submission Protection**: Disables submit button during request flight.
- **Privacy Boundary**: Recruiter-only metrics (overall scores, requirement scorecards, hiring signals, decision support) are hidden from candidate views.
