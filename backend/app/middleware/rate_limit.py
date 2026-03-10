"""
Redis-backed rate-limiting middleware for FastAPI.

Supports per-user sliding-window limits with endpoint-category awareness.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

import redis.asyncio as aioredis
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.config import get_settings

logger = logging.getLogger("operatoros.rate_limit")

settings = get_settings()

# ── Category limits (max_requests, window_seconds) ──────────────────────────

CATEGORY_LIMITS: dict[str, tuple[int, int]] = {
    "queries": (30, 60),
    "compute": (60, 60),
    "general": (120, 60),
}

# Mapping from URL prefix to category
_PREFIX_CATEGORY: list[tuple[str, str]] = [
    ("/api/queries", "queries"),
    ("/api/compute", "compute"),
]


def _resolve_category(path: str) -> str:
    """Determine rate-limit category from the request path."""
    for prefix, category in _PREFIX_CATEGORY:
        if path.startswith(prefix):
            return category
    return "general"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that enforces per-user, per-category request limits.

    If Redis is unavailable the request is allowed through (fail-open)
    to avoid cascading failures.
    """

    def __init__(self, app, redis_url: str | None = None) -> None:
        super().__init__(app)
        self._redis_url = redis_url or settings.REDIS_URL
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
                max_connections=10,
            )
        return self._redis

    def _extract_user_id(self, request: Request) -> str | None:
        """
        Try to pull a user identifier from the request state or headers.

        This runs *after* authentication middleware has set ``request.state.user_id``.
        Falls back to IP-based limiting for unauthenticated endpoints.
        """
        user_id = getattr(request.state, "user_id", None)
        if user_id is not None:
            return str(user_id)
        # Fallback: use client IP for unauthenticated routes
        return request.client.host if request.client else None

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip rate limiting for health / docs / root
        if request.url.path in ("/api/health", "/docs", "/openapi.json", "/redoc", "/"):
            return await call_next(request)

        user_key = self._extract_user_id(request)
        if user_key is None:
            return await call_next(request)

        category = _resolve_category(request.url.path)
        max_requests, window_seconds = CATEGORY_LIMITS[category]

        try:
            redis_conn = await self._get_redis()
            key = f"rl:{category}:{request.method}:{user_key}"
            now = time.time()
            window_start = now - window_seconds

            pipe = redis_conn.pipeline()
            pipe.zremrangebyscore(key, "-inf", window_start)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window_seconds + 1)
            results = await pipe.execute()

            request_count: int = results[2]

            if request_count > max_requests:
                retry_after = int(window_seconds - (now - window_start))
                logger.warning(
                    "Rate limit exceeded: user=%s category=%s count=%d",
                    user_key,
                    category,
                    request_count,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded",
                        "category": category,
                        "limit": max_requests,
                        "window_seconds": window_seconds,
                    },
                    headers={"Retry-After": str(max(retry_after, 1))},
                )

            response = await call_next(request)

            # Attach informational headers
            response.headers["X-RateLimit-Limit"] = str(max_requests)
            response.headers["X-RateLimit-Remaining"] = str(
                max(max_requests - request_count, 0)
            )
            response.headers["X-RateLimit-Reset"] = str(int(now + window_seconds))
            return response

        except aioredis.RedisError as exc:
            # Fail open — let the request through when Redis is down
            logger.error("Rate-limit Redis error (fail-open): %s", exc)
            return await call_next(request)
