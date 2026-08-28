import logging
from typing import Optional

from redis.asyncio import Redis, from_url

from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import DomainException

logger = logging.getLogger("interviewiq.rate_limiter")


class RedisRateLimiter:
    """Redis-backed rate limiter with fail-open fallback logging."""

    def __init__(self, redis_url: str = settings.REDIS_URL):
        self.redis_url = redis_url
        self._redis: Optional[Redis] = None

    async def _get_client(self) -> Optional[Redis]:
        if self._redis is None:
            try:
                self._redis = from_url(self.redis_url, encoding="utf-8", decode_responses=True)
            except Exception as e:
                logger.warning(f"Redis rate limiter connection failed: {e}. Failing open.")
                return None
        return self._redis

    async def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> None:
        client = await self._get_client()
        if not client:
            return # Fail-open for local dev if Redis is unavailable

        try:
            redis_key = f"rate_limit:{key}"
            current = await client.incr(redis_key)
            if current == 1:
                await client.expire(redis_key, window_seconds)
            
            if current > max_requests:
                raise DomainException("Too many requests. Please try again later.", code="RATE_LIMIT_EXCEEDED")
        except DomainException:
            raise
        except Exception as e:
            logger.warning(f"Rate limiting check failed on Redis: {e}. Failing open.")


default_rate_limiter = RedisRateLimiter()
