"""
Response caching layer for AnemiaLens.

Provides:
- In-memory TTL cache (always available)
- Redis-backed cache (when REDIS_URL is configured)
- Automatic fallback: Redis -> in-memory
- Cache key generation from request path + query params
- Configurable per-endpoint TTLs
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from typing import Any

from app.config import settings

log = logging.getLogger("anemialens.cache")


# ---------------------------------------------------------------------------
# In-memory LRU cache with TTL
# ---------------------------------------------------------------------------


class _MemoryCache:
    """Thread-safe in-memory LRU cache with per-entry TTL."""

    def __init__(self, maxsize: int = 256):
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._maxsize = maxsize
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            if key in self._cache:
                value, expires_at = self._cache[key]
                if time.time() < expires_at:
                    # Move to end (most recently used)
                    self._cache.move_to_end(key)
                    return value
                else:
                    del self._cache[key]
            return None

    async def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        async with self._lock:
            expires_at = time.time() + ttl_seconds
            if key in self._cache:
                self._cache.move_to_end(key)
            elif len(self._cache) >= self._maxsize:
                self._cache.popitem(last=False)
            self._cache[key] = (value, expires_at)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()

    async def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count of removed entries."""
        async with self._lock:
            now = time.time()
            expired = [k for k, (_, exp) in self._cache.items() if now >= exp]
            for k in expired:
                del self._cache[k]
            return len(expired)


# ---------------------------------------------------------------------------
# Redis cache (optional)
# ---------------------------------------------------------------------------


class _RedisCache:
    """Async Redis-backed cache."""

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._client: Any | None = None
        self._available = False

    async def _ensure_client(self) -> Any | None:
        if self._client is not None or self._available is False:
            return self._client

        try:
            import redis.asyncio as redis

            self._client = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=True,
            )
            await self._client.ping()
            self._available = True
            log.info("Redis cache connected: %s", self._redis_url[:30])
            return self._client
        except Exception as exc:
            log.warning("Redis cache unavailable (fallback to memory): %s", exc)
            self._available = False
            self._client = None
            return None

    async def get(self, key: str) -> Any | None:
        client = await self._ensure_client()
        if client is None:
            return None
        try:
            raw = await client.get(key)
            if raw is not None:
                return json.loads(raw)
            return None
        except Exception as exc:
            log.warning("Redis GET error: %s", exc)
            self._available = False
            return None

    async def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        client = await self._ensure_client()
        if client is None:
            return
        try:
            await client.setex(key, int(ttl_seconds), json.dumps(value, ensure_ascii=False, default=str))
        except Exception as exc:
            log.warning("Redis SET error: %s", exc)
            self._available = False

    async def delete(self, key: str) -> bool:
        client = await self._ensure_client()
        if client is None:
            return False
        try:
            return await client.delete(key) > 0
        except Exception as exc:
            log.warning("Redis DELETE error: %s", exc)
            self._available = False
            return False

    async def clear(self) -> None:
        client = await self._ensure_client()
        if client:
            try:
                await client.flushdb()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Unified cache facade (Redis + memory fallback)
# ---------------------------------------------------------------------------


class ResponseCache:
    """
    Unified cache interface. Tries Redis first, falls back to in-memory.

    Usage:
        cache = ResponseCache()
        await cache.get(key)
        await cache.set(key, value, ttl=60)
    """

    def __init__(self, ttl_default: float = 60.0, maxsize: int = 256):
        redis_url = getattr(settings, "redis_url", None) or ""
        self._redis = _RedisCache(redis_url) if redis_url else None
        self._memory = _MemoryCache(maxsize=maxsize)
        self._ttl_default = ttl_default
        self._hits = 0
        self._misses = 0

    @staticmethod
    def make_key(path: str, query_params: dict | None = None, user_id: int | None = None) -> str:
        """Generate a deterministic cache key from request components."""
        parts = [path]
        if query_params:
            parts.append(json.dumps(query_params, sort_keys=True))
        if user_id is not None:
            parts.append(f"user:{user_id}")
        raw = "|".join(parts)
        return f"anemialens:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"

    async def get(self, key: str) -> Any | None:
        # Try Redis first (if available)
        if self._redis:
            value = await self._redis.get(key)
            if value is not None:
                self._hits += 1
                return value

        # Fallback to memory
        value = await self._memory.get(key)
        if value is not None:
            self._hits += 1
        else:
            self._misses += 1
        return value

    async def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        ttl = ttl_seconds or self._ttl_default
        # Write to both
        if self._redis:
            await self._redis.set(key, value, ttl)
        await self._memory.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        results = []
        if self._redis:
            results.append(await self._redis.delete(key))
        results.append(await self._memory.delete(key))
        return any(results)

    async def clear(self) -> None:
        if self._redis:
            await self._redis.clear()
        await self._memory.clear()
        self._hits = 0
        self._misses = 0

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def get_stats(self) -> dict:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 3),
            "redis_available": self._redis is not None,
        }


# ---------------------------------------------------------------------------
# Global cache instance
# ---------------------------------------------------------------------------

response_cache = ResponseCache(
    ttl_default=getattr(settings, "cache_ttl_default", 60.0),
    maxsize=getattr(settings, "cache_maxsize", 256),
)


# ---------------------------------------------------------------------------
# Cache cleanup background task
# ---------------------------------------------------------------------------


async def cache_cleanup_loop() -> None:
    """Run periodically to clean up expired entries."""
    while True:
        await asyncio.sleep(120)
        try:
            removed = await response_cache._memory.cleanup_expired()
            if removed:
                log.info("Cache cleanup: removed %d expired entries", removed)
        except Exception as exc:
            log.warning("Cache cleanup error: %s", exc)
