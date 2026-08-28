# Interview Report Generation Architecture

## 1. Overview
Interview report generation combines deterministic numerical scoring with qualitative LLM synthesis via Gemini `AIProvider`.

## 2. Qualitative Synthesis Validation
Gemini structured output is parsed into `InterviewReportSynthesisOutput`:
- `executive_summary`: High-level executive performance synthesis.
- `seniority_assessment`: Assessed technical seniority level.
- `top_strengths`: List of demonstrated candidate technical strengths.
- `growth_areas`: Primary technical areas for candidate growth.
- `recommendation`: Qualitative recommendation (`STRONG_HIRE`, `HIRE`, `BORDERLINE`, `NO_HIRE`).

## 3. Versioning Strategy (ADR 036)
`InterviewReportORM` is immutable. Regenerating a report creates version 2 (`report_version = 2`) backed by unique constraint `UNIQUE(interview_session_id, report_version)`.
