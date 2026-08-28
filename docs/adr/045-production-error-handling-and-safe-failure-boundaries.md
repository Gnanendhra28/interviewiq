# ADR 045: Production Error Handling & Safe Failure Boundaries

## Context
Production API errors must return consistent structured JSON containing request correlation IDs while strictly hiding stack traces, SQL queries, or internal credentials.

## Decision
1. All uncaught exceptions are trapped by FastAPI global exception handlers.
2. Production error response format:
```json
{
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "An internal server error occurred. Please contact support.",
    "request_id": "req_12345"
  }
}
```
3. Full tracebacks are logged internally with correlation IDs but NEVER returned over HTTP.

## Consequences
- Prevents technical information disclosure vulnerabilities.
- Simplifies production error troubleshooting via request ID lookup.
