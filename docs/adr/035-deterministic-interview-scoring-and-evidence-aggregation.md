# ADR 035: Deterministic Interview Scoring & Evidence Aggregation

## Context
Numerical scoring and job requirement scorecards in interview reports must be deterministic, reproducible, and decoupled from LLM non-determinism.

## Decision
1. `InterviewScoringEngine` computes overall and sub-dimension scores (`technical_competency_score`, `reasoning_score`, `communication_score`, `completeness_score`, `requirement_coverage_score`) using explicit weighted formulas over persisted `AnswerEvaluationORM` records.
2. Requirement scorecards categorize requirement coverage (`ASSESSED`, `PARTIALLY_ASSESSED`, `NOT_ASSESSED`).
3. LLMs generate qualitative synthesis text only and cannot alter numerical scores.

## Consequences
- 100% mathematical reproducibility for candidate report scores.
- Unassessed critical skills remain visible to recruiters.
