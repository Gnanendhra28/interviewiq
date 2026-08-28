# ADR 004: Asynchronous Background Job Worker Architecture via Redis

## Status
Accepted

## Context
Operations such as multi-page resume PDF parsing, PDF text extraction, high-dimensional vector embedding generation for entire knowledge bases, and multi-criteria interview report synthesis require significant compute and time (2s to 30s+). Performing these operations inside synchronous FastAPI HTTP request handlers blocks worker threads, causes client timeouts, and degrades UX.

## Decision
We decouple long-running operations using an **Asynchronous Worker Process** (`workers/`) powered by **Redis** as the message broker.

HTTP API handlers enqueue job records in PostgreSQL (status: `QUEUED`) and push job payloads to Redis queues. Dedicated Python worker processes pull jobs from Redis, execute the workflow using application services, persist the result in PostgreSQL, and update job status to `COMPLETED` or `FAILED`.

## Job Pipeline Workflows

1. **Resume Processing**: `POST /api/v1/resumes/upload` -> Queue -> Extract PDF & LLM Analysis -> Update Candidate Profile.
2. **Knowledge Ingestion**: Upload KB PDF -> Queue -> Chunking & Gemini Vector Embedding -> Store in pgvector.
3. **Report Generation**: Interview Completed -> Queue -> Synthesize Competency Matrix & Report -> Store Report Record.

## Consequences

### Positive
- **API Responsiveness**: Immediate sub-100ms HTTP responses for file uploads and job submissions.
- **Fault Tolerance & Retries**: Failed jobs are automatically retried with exponential backoff without crashing web servers.
- **Resource Control**: Background worker concurrency can be scaled independently from HTTP API instances.

### Negative / Trade-offs
- Requires candidates/frontend to poll job status or listen to WebSocket/SSE updates for completion.
