# ADR 022: Immutable Resume Analysis Versioning

## Status
Approved

## Context
Resume intelligence analysis output must preserve full provenance and version history when prompts, schemas, or LLM models evolve.

## Decision
1. `ResumeAnalysisORM` records are immutable systems of record.
2. Historical analysis records are never updated in place.
3. Every analysis record stores `prompt_version` and `schema_version` alongside model metadata.
4. Reprocessing a resume generates a new versioned `ResumeAnalysisORM` entry.

## Consequences
- Guarantees full auditability and reproducible intelligence analysis.
- Enables safe prompt and model upgrades without corrupting historical evaluation records.
