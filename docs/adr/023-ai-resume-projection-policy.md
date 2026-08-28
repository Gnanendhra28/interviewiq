# ADR 023: AI Candidate Data Projection & Provenance Policy

## Status
Approved

## Context
AI-extracted resume intelligence must be projected into candidate profiles without silently overwriting human-entered information.

## Decision
1. Candidate profile components track source provenance (`MANUAL` vs `RESUME_AI`).
2. Candidate skills with `source = 'MANUAL'` are protected and never overwritten by AI analysis output.
3. AI-derived skills are stored with `source = 'RESUME_AI'` and provenance evidence.
4. Projection logic executes through `ApplyResumeProjectionUseCase` after Pydantic schema validation.

## Consequences
- Protects user-entered data integrity.
- Provides complete transparency regarding data origin.
