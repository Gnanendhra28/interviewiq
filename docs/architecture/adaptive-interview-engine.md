# Hybrid Deterministic + AI Adaptive Intelligence Architecture

## 1. Overview
The **Adaptive Decision Engine** determines difficulty transitions and next topic selection based on candidate performance signals while enforcing strict backend guardrails (ADR 033).

## 2. Difficulty Progression Policy
Normalized levels: `EASY` $\leftrightarrow$ `MEDIUM` $\leftrightarrow$ `HARD` $\leftrightarrow$ `EXPERT`.
- **Score $\ge 8.0$**: Increase difficulty by 1 step (e.g. `MEDIUM` $\rightarrow$ `HARD`).
- **Score $< 5.0$**: Decrease difficulty by 1 step (e.g. `HARD` $\rightarrow$ `MEDIUM`).
- **Score between 5.0 and 7.9**: Maintain current difficulty level.
- **Maximum Jump**: 1 level transition per turn. Direct jumps (e.g. `EASY` $\rightarrow$ `EXPERT`) are strictly rejected.

## 3. Topic Coverage & Completion Boundary
- Topics are prioritized according to `InterviewBlueprintORM.topic_weights_json`.
- When all blueprint target turns (e.g. 10 questions) are evaluated, `is_completion_decision` is set to `True` and `InterviewSessionORM.status` transitions to `COMPLETING`.
