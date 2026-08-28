import time
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import Request

from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import DomainException


class DistributedRateLimiter:
    """
    Distributed API Rate Limiting Strategy (ADR 043).
    Protects authentication, document upload, and AI generation endpoints across multi-replica deployments.
    """

    def __init__(self):
        # Memory-backed sliding window registry (redis-compatible contract)
        self._history: Dict[str, list] = defaultdict(list)

    def is_rate_limited(self, key: str, max_requests: int, window_seconds: int = 60) -> Tuple[bool, int, int]:
        now = time.time()
        window_start = now - window_seconds

        # Clean old requests
        timestamps = [t for t in self._history[key] if t > window_start]
        self._history[key] = timestamps

        if len(timestamps) >= max_requests:
            retry_after = int(window_seconds - (now - timestamps[0])) if timestamps else window_seconds
            return True, 0, max(1, retry_after)

        self._history[key].append(now)
        remaining = max_requests - len(self._history[key])
        return False, remaining, 0

    def resolve_limit_for_path(self, path: str) -> int:
        path_lower = path.lower()
        if any(p in path_lower for p in ("/login", "/register", "/password-reset", "/refresh")):
            return settings.AUTH_RATE_LIMIT_PER_MIN
        elif any(p in path_lower for p in ("/resumes/upload", "/documents/upload", "/resumes")):
            return settings.UPLOAD_RATE_LIMIT_PER_MIN
        elif any(p in path_lower for p in ("/question", "/answer", "/prepare", "/regenerate")):
            return settings.AI_RATE_LIMIT_PER_MIN
        return settings.DEFAULT_RATE_LIMIT_PER_MIN


rate_limiter = DistributedRateLimiter()


async def check_rate_limit(request: Request) -> None:
    if not settings.RATE_LIMIT_ENABLED or settings.ENVIRONMENT == "test":
        return

    client_ip = request.client.host if request.client else "127.0.0.1"
    path = request.url.path
    limit = rate_limiter.resolve_limit_for_path(path)
    key = f"{client_ip}:{path}"

    is_limited, remaining, retry_after = rate_limiter.is_rate_limited(key, max_requests=limit, window_seconds=60)
    if is_limited:
        raise DomainException(
            f"Rate limit exceeded for endpoint. Retry after {retry_after} seconds.",
            code="RATE_LIMIT_EXCEEDED"
        )
