# InterviewIQ: Adaptive AI Technical Interview Platform

InterviewIQ is a production-grade, AI-powered adaptive technical interview platform designed as a **Modular Monolith**.

## Architecture Overview

- **Frontend**: Next.js 14+ (TypeScript, Tailwind CSS, TanStack Query)
- **Backend**: FastAPI (Python 3.11+, Pydantic v2, SQLAlchemy 2.0, Asyncpg)
- **Persistence**: PostgreSQL + pgvector
- **Caching & Background Jobs**: Redis + Async Worker Process
- **AI Engine**: Google Gemini API via abstract `AIProvider` interface
- **Storage**: Abstract `StorageProvider` (Local FS for dev, GCS for prod)

## Documentation

Full architectural specifications and Architecture Decision Records (ADRs) are located in `docs/`:
- [System Overview](file:///Users/gnanendhrajoy/.gemini/antigravity/scratch/interviewiq/docs/architecture/system-overview.md)
- [Domain Boundaries](file:///Users/gnanendhrajoy/.gemini/antigravity/scratch/interviewiq/docs/architecture/domain-boundaries.md)
- [Data Flow Specification](file:///Users/gnanendhrajoy/.gemini/antigravity/scratch/interviewiq/docs/architecture/data-flow.md)
- [RAG Architecture](file:///Users/gnanendhrajoy/.gemini/antigravity/scratch/interviewiq/docs/architecture/rag-architecture.md)
- [Interview Lifecycle State Machine](file:///Users/gnanendhrajoy/.gemini/antigravity/scratch/interviewiq/docs/architecture/interview-lifecycle.md)
- [ADR 001: Modular Monolith](file:///Users/gnanendhrajoy/.gemini/antigravity/scratch/interviewiq/docs/adr/001-modular-monolith.md)
- [ADR 002: PostgreSQL + pgvector](file:///Users/gnanendhrajoy/.gemini/antigravity/scratch/interviewiq/docs/adr/002-postgresql-pgvector.md)
- [ADR 003: Gemini AI Provider Abstraction](file:///Users/gnanendhrajoy/.gemini/antigravity/scratch/interviewiq/docs/adr/003-gemini-ai-provider.md)
- [ADR 004: Background Processing](file:///Users/gnanendhrajoy/.gemini/antigravity/scratch/interviewiq/docs/adr/004-background-processing.md)
- [ADR 005: Authentication & Authorization](file:///Users/gnanendhrajoy/.gemini/antigravity/scratch/interviewiq/docs/adr/005-authentication-and-authorization.md)

## Quick Start (Docker Compose)

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Start services
make up

# 3. Access applications
# Web Frontend: http://localhost:3000
# API Documentation: http://localhost:8000/docs
```

## Running Tests

```bash
make test
```
