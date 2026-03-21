"""
Redis caching layer — TTL-based caching with hit/miss metrics and
cache invalidation for write operations.

Usage:
    cache = CacheService(redis)
    result = await cache.get_or_set("tax:abc123", compute_fn, ttl=3600)
    await cache.invalidate("tax:abc123")
    metrics = cache.get_metrics()
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Callable, Coroutine, Optional

import redis.asyncio as aioredis

logger = logging.getLogger("operatoros.cache")

# ── TTL constants (seconds) ─────────────────────────────────────────────────

TTL_TAX_COMPUTATION = 3600       # 1 hour
TTL_CLIENT_LIST = 300            # 5 minutes
TTL_KNOWLEDGE_BASE = 86400       # 24 hours
TTL_DASHBOARD_STATS = 60         # 1 minute
TTL_COMPLIANCE_CALENDAR = 1800   # 30 minutes


class CacheService:
    """Redis-backed caching with metrics tracking."""

    _PREFIX = "oos:"  # OperatorOS namespace

    def __init__(self, redis_conn: aioredis.Redis) -> None:
        self.redis = redis_conn
        self._hits = 0
        self._misses = 0

    # ── Core operations ──────────────────────────────────────────────────

    async def get(self, key: str) -> Any | None:
        """Retrieve a cached value. Returns None on miss."""
        full_key = self._PREFIX + key
        try:
            raw = await self.redis.get(full_key)
            if raw is not None:
                self._hits += 1
                logger.debug("Cache HIT: %s", key)
                return json.loads(raw)
            self._misses += 1
            logger.debug("Cache MISS: %s", key)
            return None
        except Exception:
            logger.exception("Cache GET error for key: %s", key)
            self._misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Store a value with TTL."""
        full_key = self._PREFIX + key
        try:
            raw = json.dumps(value, default=str)
            await self.redis.setex(full_key, ttl, raw)
            logger.debug("Cache SET: %s (ttl=%ds)", key, ttl)
        except Exception:
            logger.exception("Cache SET error for key: %s", key)

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Coroutine[Any, Any, Any]],
        ttl: int = 300,
    ) -> Any:
        """Get from cache or compute via factory and cache the result."""
        cached = await self.get(key)
        if cached is not None:
            return cached

        result = await factory()
        await self.set(key, result, ttl)
        return result

    async def invalidate(self, key: str) -> None:
        """Delete a specific cache key."""
        full_key = self._PREFIX + key
        try:
            await self.redis.delete(full_key)
            logger.debug("Cache INVALIDATE: %s", key)
        except Exception:
            logger.exception("Cache invalidation error for key: %s", key)

    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern. Returns count deleted."""
        full_pattern = self._PREFIX + pattern
        count = 0
        try:
            async for key in self.redis.scan_iter(match=full_pattern, count=100):
                await self.redis.delete(key)
                count += 1
            logger.debug("Cache INVALIDATE pattern '%s': %d keys", pattern, count)
        except Exception:
            logger.exception("Cache pattern invalidation error: %s", pattern)
        return count

    # ── Metrics ──────────────────────────────────────────────────────────

    def get_metrics(self) -> dict:
        """Return cache hit/miss metrics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total": total,
            "hit_rate_percent": round(hit_rate, 2),
        }

    # ── Key builders ─────────────────────────────────────────────────────

    @staticmethod
    def tax_key(params: dict) -> str:
        """Build a deterministic cache key for tax computation params."""
        # Sort keys for determinism, then hash
        canonical = json.dumps(params, sort_keys=True, default=str)
        digest = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        return f"tax:{digest}"

    @staticmethod
    def client_list_key(page: int, size: int, search: str | None = None) -> str:
        """Build cache key for client list queries."""
        parts = [f"p{page}", f"s{size}"]
        if search:
            parts.append(f"q{hashlib.md5(search.encode()).hexdigest()[:8]}")
        return "clients:list:" + ":".join(parts)

    @staticmethod
    def knowledge_key(query: str) -> str:
        """Build cache key for knowledge base lookups."""
        digest = hashlib.sha256(query.encode()).hexdigest()[:16]
        return f"knowledge:{digest}"

    @staticmethod
    def dashboard_key(stat_type: str) -> str:
        """Build cache key for dashboard stats."""
        return f"dashboard:{stat_type}"
