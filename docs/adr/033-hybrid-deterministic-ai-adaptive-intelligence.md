# ADR 033: Hybrid Deterministic + AI Adaptive Intelligence

## Context
Interview difficulty adaptation and topic selection must not rely purely on unconstrained LLM outputs, which could introduce extreme difficulty spikes or ignore blueprint topic weights.

## Decision
1. Adaptive interview decisions (`AdaptiveDecisionORM`) use a hybrid model combining LLM performance signals with deterministic backend rules.
2. Difficulty transitions are capped at $\pm 1$ step per turn (`EASY` $\leftrightarrow$ `MEDIUM` $\leftrightarrow$ `HARD` $\leftrightarrow$ `EXPERT`).
3. High score ($\ge 8.0$) increases difficulty; low score ($< 5.0$) decreases difficulty.
4. Next topic selection strictly prioritizes unassessed required skills from `InterviewBlueprintORM.topic_weights_json`.
5. Session transitions to `COMPLETING` when target turns (e.g. 10 questions) are evaluated.

## Consequences
- Predictable, standardized candidate assessment experience.
- Complete blueprint topic coverage compliance.
