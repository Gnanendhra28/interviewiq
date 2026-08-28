# AI Provenance & Controlled Candidate Data Projection

## 1. Provenance Model

InterviewIQ distinguishes candidate profile data sources using explicit provenance attributes:
- `MANUAL`: Data created or edited by recruiters or candidate users.
- `RESUME_AI`: Intelligence derived from automated resume parsing.

Extracted skills, work experience, and education store source evidence text snippets referencing originating document locations.

---

## 2. Projection Rules & Non-Overwrite Policy

`ApplyResumeProjectionUseCase` applies candidate profile updates according to strict rules:
1. **Preserve Manual Provenance**: Existing skills with `source = 'MANUAL'` are never overwritten or mutated by AI analysis output.
2. **AI Skill Merging**: AI-derived skills (`source = 'RESUME_AI'`) update proficiency or experience years without duplicating records.
3. **Auditability**: Every projection event emits a `candidate.projected_from_resume` audit record.
