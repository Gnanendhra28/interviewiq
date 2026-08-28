# ADR 032: AI Answer Evaluation Versioning & Provenance

## Context
AI answer evaluation outputs must be audit-traceable, version-controlled, and immutable to prevent silent score updates.

## Decision
1. `AnswerEvaluationORM` records are immutable and versioned (`UNIQUE(answer_id, evaluation_version)`).
2. Re-evaluating an answer creates a new version (`evaluation_version = 2`), preserving historical evaluation records intact.
3. Every evaluation record stores AI provider (`gemini`), model (`gemini-2.5-flash`), prompt version (`v1`), and latency metadata.
4. Gemini structured output must be validated against `AnswerEvaluationOutput` Pydantic schema before persistence.

## Consequences
- 100% auditability for candidate score calculations.
- Structural protection against malformed LLM evaluation outputs.
