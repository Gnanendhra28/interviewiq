# AI Resume Analysis Architecture & Gemini Integration

## 1. Provider Abstraction & Model Strategy

All LLM calls execute through `AIProvider` / `GeminiProvider` (`apps/api/app/core/ai/gemini_provider.py`). The worker process never invokes Gemini SDKs directly.

Configuration defaults to:
- `AI_PROVIDER`: `gemini`
- `GEMINI_MODEL`: `gemini-2.5-flash`

---

## 2. Prompt Versioning & Schema Validation

Every AI analysis enforces:
- **Versioned Prompts**: Prompts are centrally defined in `apps/api/app/modules/resumes/domain/prompts.py` (`PROMPT_VERSION = "v1"`).
- **Strict Pydantic Validation**: Responses are validated against `ResumeAnalysisOutput` (`apps/api/app/modules/resumes/domain/schemas.py`).
- **Immutable Persistence**: Analysis output is persisted in `ResumeAnalysisORM` with `prompt_version` and `schema_version` metadata.

---

## 3. Reprocessing Architecture

Reprocessing a resume with a new model or updated prompt creates a new versioned `ResumeAnalysisORM` record (`v2`, `v3`). Historical analysis records are preserved permanently.
