# ADR 003: Unified AIProvider Abstraction Layer with Google Gemini

## Status
Accepted

## Context
InterviewIQ relies heavily on generative AI for resume parsing, RAG vector embeddings, dynamic adaptive question generation, structured answer evaluation, and final candidate report synthesis. Directly sprinkling vendor-specific Gemini SDK calls throughout API handlers or business services creates vendor lock-in, testing difficulty, and inconsistent error/retry handling.

## Decision
We establish an abstract `AIProvider` contract in the core platform domain (`apps/api/app/core/ai/provider.py`). The primary concrete implementation is `GeminiAIProvider` using the official `google-genai` SDK.

The `AIProvider` interface exposes strongly typed methods returning Pydantic schemas:
- `analyze_resume(file_bytes: bytes) -> CandidateProfileSchema`
- `generate_question(context: QuestionContext) -> InterviewQuestionSchema`
- `evaluate_answer(submission: AnswerSubmissionContext) -> EvaluationResultSchema`
- `generate_report(session_summary: SessionSummaryContext) -> InterviewReportSchema`
- `generate_embeddings(text_chunks: list[str]) -> list[list[float]]`

All AI operations enforce timeout handling (30s max), exponential backoff retries (3 attempts), structured output enforcement, and execution tracing.

## Consequences

### Positive
- **Zero Vendor Lock-in**: The application core depends on `AIProvider` interface. Swapping or adding fallback LLM providers requires changing only the infrastructure adapter.
- **Mockability in Unit Tests**: Fast, deterministic unit testing using a mock AI provider without external network calls.
- **Centralized Tracing & Resilience**: Metrics, latency logging, rate limits, and fallback strategies are implemented once in the provider layer.

### Negative / Trade-offs
- Writing typed abstract wrappers for every AI capability requires upfront boilerplate; however, this is necessary for production-grade reliability.
