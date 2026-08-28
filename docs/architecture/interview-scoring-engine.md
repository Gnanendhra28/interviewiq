# Deterministic Interview Scoring Engine Architecture

## 1. Overview
The **Interview Scoring Engine** (`InterviewScoringEngine`) computes numerical candidate evaluation scores and sub-dimension metrics deterministically from persisted `AnswerEvaluationORM` records (ADR 035).

## 2. Formulas & Weightings
- **Technical Competency Score**: Mean of `score_technical_accuracy` across evaluated questions.
- **Reasoning Score**: Mean of `score_depth` and `reasoning_quality_score`.
- **Communication Score**: Mean of `score_clarity`.
- **Completeness Score**: Mean of `completeness_score`.
- **Requirement Coverage Score**: $(\text{Assessed Requirements} / \text{Total Requirements}) \times 10.0$.
- **Overall Score**:
  $$\text{Overall} = 0.40 \cdot \text{Technical} + 0.25 \cdot \text{Reasoning} + 0.15 \cdot \text{Communication} + 0.20 \cdot \text{Coverage}$$
  Bounded within $[0.0, 10.0]$.

## 3. Hiring Signal Rules
- `STRONG_HIRE_SIGNAL`: Overall score $\ge 8.5$ and Coverage score $\ge 7.5$.
- `HIRE_SIGNAL`: Overall score $\ge 7.0$ and Coverage score $\ge 5.0$.
- `MIXED_SIGNAL`: Overall score $\ge 5.5$.
- `NO_HIRE_SIGNAL`: Overall score $< 5.5$.
- `INSUFFICIENT_EVIDENCE`: Fewer than 3 evaluated turns.
