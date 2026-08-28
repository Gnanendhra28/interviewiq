# Local Development & Testing Guide

This document describes how to run and test **InterviewIQ** locally using Docker Compose, PostgreSQL with `pgvector`, Redis, FastAPI, and Next.js.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 16 with `pgvector` extension

## Quickstart

1. Clone the repository and initialize local environment:
   ```bash
   cp .env.example .env
   ```

2. Spin up local database and background services:
   ```bash
   docker compose up -d
   ```

3. Run database migrations:
   ```bash
   PYTHONPATH=. python3 -m alembic -c apps/api/alembic.ini upgrade head
   ```

4. Run FastAPI backend server:
   ```bash
   uvicorn apps.api.app.main:app --reload --port 8000
   ```

5. Run background worker process:
   ```bash
   python3 -m workers.main
   ```

6. Run Next.js web application:
   ```bash
   cd apps/web && npm run dev
   ```

## Running Automated Tests

Run the complete 88-test suite:
```bash
PYTHONPATH=. python3 -m pytest apps/api/app/modules/*/tests/*.py workers/tests/*.py tests/*/*.py -v
```

Run non-destructive production smoke tests:
```bash
PYTHONPATH=. python3 -m pytest tests/smoke/test_production_smoke.py -v
```
