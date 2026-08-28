# Asynchronous AI Answer Evaluation Architecture

## 1. Overview
Answer evaluation is performed asynchronously by `ProcessAnswerEvaluationWorkerTask` to decouple long LLM latency from HTTP request threads.

```
Worker Task Claims ANSWER_EVALUATION Job (SELECT ... FOR UPDATE SKIP LOCKED)
       ↓
Load Question, Turn, Snapshot & Blueprint Provenance
       ↓
Invoke Gemini AIProvider with Pydantic AnswerEvaluationOutput Validation
       ↓
Execute Deterministic Adaptive Decision Engine
       ↓
Atomic Persistence:
  - AnswerEvaluationORM (evaluation_version = 1)
  - AdaptiveDecisionORM
  - Turn State Update ('EVALUATED')
  - BackgroundJobORM ('COMPLETED')
  - Audit Logs ('answer.evaluated', 'interview.adaptation_decided')
```

## 2. Pydantic Output Validation
Every Gemini response must conform strictly to `AnswerEvaluationOutput`:
- `overall_score`: [0.0, 10.0]
- `score_technical_accuracy`: [0.0, 10.0]
- `score_depth`: [0.0, 10.0]
- `score_clarity`: [0.0, 10.0]
- `key_strengths`: List[str]
- `missing_elements`: List[str]
- `feedback_text`: str
