# ADR 039: Human Hiring Decision Authority & AI Separation

## Context
Automated AI scoring and recommendation systems must operate strictly as decision support tools and cannot autonomously hire, shortlist, or reject job candidates.

## Decision
1. Human hiring decisions (`SHORTLISTED`, `HIRED`, `REJECTED`, `ON_HOLD`) are governed exclusively by human recruiters and organization administrators.
2. AI scoring engines and LLMs produce qualitative synthesis and decision signals (`STRONG_HIRE_SIGNAL`, `HIRE_SIGNAL`, etc.) but are forbidden from writing to `HiringDecisionORM`.
3. Candidate context access to decision APIs is denied with `403 Forbidden`.

## Consequences
- Responsible, compliant AI governance aligned with anti-discrimination employment policies.
- Clear separation between AI analytical evidence and human authority.
