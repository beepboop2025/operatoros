"""
Shared FastAPI dependencies: authentication, role gating, Redis, rate limiting.
"""

from __future__ import annotations

import asyncio
import time
from typing import List
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db
from app.middleware.auth import verify_token
from app.models.user import User
from app.schemas.auth import TokenPayload

# ── Security scheme ──────────────────────────────────────────────────────────

_bearer_scheme = HTTPBearer(auto_error=True)

# ── Redis ────────────────────────────────────────────────────────────────────

_redis_pool: aioredis.Redis | None = None
_redis_lock: asyncio.Lock = asyncio.Lock()


async def get_redis(
    settings: Settings = Depends(get_settings),
) -> aioredis.Redis:
    """Return a shared async Redis connection (lazily initialised)."""
    global _redis_pool
    if _redis_pool is None:
        async with _redis_lock:
            # Double-checked locking: re-check after acquiring the lock
            if _redis_pool is None:
                _redis_pool = aioredis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    max_connections=20,
                )
    return _redis_pool


# ── Current user ─────────────────────────────────────────────────────────────


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode the JWT, look up the user, and return the ORM instance."""
    payload: TokenPayload = verify_token(credentials.credentials)

    result = await db.execute(select(User).where(User.id == payload.sub))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive account",
        )
    return user


# ── Role gating ──────────────────────────────────────────────────────────────


def require_role(allowed_roles: List[str]):
    """
    Return a dependency that enforces role-based access.

    Usage::

        @router.get("/admin-only", dependencies=[Depends(require_role(["admin"]))])
        async def admin_view(): ...
    """

    async def _check_role(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role.value not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role.value}' is not permitted for this action",
            )
        return current_user

    return _check_role


# ── Rate limiter ─────────────────────────────────────────────────────────────


class RateLimiter:
    """
    Per-user sliding-window rate limiter backed by Redis.

    Parameters
    ----------
    max_requests : int
        Maximum number of requests allowed within *window_seconds*.
    window_seconds : int
        Length of the sliding window in seconds.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def __call__(
        self,
        request: Request,
        current_user: User = Depends(get_current_user),
        redis_conn: aioredis.Redis = Depends(get_redis),
    ) -> None:
        key = f"rate_limit:{current_user.id}:{request.url.path}"
        now = time.time()
        window_start = now - self.window_seconds

        # Check count BEFORE adding the current request
        pipe = redis_conn.pipeline()
        pipe.zremrangebyscore(key, "-inf", window_start)
        pipe.zcard(key)
        results = await pipe.execute()

        request_count: int = results[1]

        if request_count >= self.max_requests:
            # Find the oldest entry to compute when the window will free a slot
            oldest = await redis_conn.zrange(key, 0, 0, withscores=True)
            if oldest:
                retry_after = int(oldest[0][1] + self.window_seconds - now)
            else:
                retry_after = self.window_seconds
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(max(retry_after, 1))},
            )

        # Only add the request after confirming we're within limits
        pipe2 = redis_conn.pipeline()
        pipe2.zadd(key, {str(now): now})
        pipe2.expire(key, self.window_seconds + 1)
        await pipe2.execute()
