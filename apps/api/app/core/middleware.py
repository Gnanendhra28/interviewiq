import time
import uuid
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from apps.api.app.core.config import settings
from apps.api.app.core.metrics import metrics_collector

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_current_request_id() -> str:
    return request_id_ctx.get()


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """
    Structured Logging & Correlation ID Middleware (ADR 042).
    Reads incoming X-Request-ID or auto-generates req_<uuid4>, propagating it across request context.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        req_id = request.headers.get("X-Request-ID")
        if not req_id or not req_id.strip():
            req_id = f"req_{uuid.uuid4().hex[:12]}"
        
        token = request_id_ctx.set(req_id)
        start_time = time.time()

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Record Prometheus metrics
            path_tmpl = request.url.path
            metrics_collector.record_api_request(
                method=request.method,
                path_template=path_tmpl,
                status_code=response.status_code,
                duration_ms=duration_ms
            )

            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_ctx.reset(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Production Security Hardening Headers Middleware.
    Enforces X-Content-Type-Options, Referrer-Policy, X-Frame-Options, and HSTS.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        if settings.ENVIRONMENT in ("production", "staging"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
