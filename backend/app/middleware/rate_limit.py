"""
Enhanced rate limiting middleware for AnemiaLens.

Features:
- Sliding window log algorithm (more accurate than token bucket)
- Redis-backed rate limiting (when REDIS_URL is configured)
- In-memory fallback (always available)
- Per-endpoint and per-IP rate limiting
- Configurable windows and limits
- Automatic cleanup of expired entries
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import settings

log = logging.getLogger("anemialens.rate_limit")


# ---------------------------------------------------------------------------
# In-memory sliding window rate limiter
# ---------------------------------------------------------------------------


class _MemoryRateLimiter:
    """
    Sliding window log rate limiter using in-memory storage.

    Stores timestamps of recent requests per key.
    More accurate than token bucket for rate limiting.
    """

    def __init__(self, max_entries: int = 10000):
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._max_entries = max_entries
        self._lock = asyncio.Lock()
        self._last_cleanup = time.time()

    async def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        """
        Check if a request is allowed.
        Returns (allowed, retry_after_seconds).
        """
        now = time.time()
        cutoff = now - window_seconds

        async with self._lock:
            # Remove expired entries
            timestamps = self._windows[key]
            timestamps[:] = [ts for ts in timestamps if ts > cutoff]

            if len(timestamps) < max_requests:
                timestamps.append(now)
                return True, 0

            # Rate limited
            oldest = timestamps[0]
            retry_after = int(oldest + window_seconds - now) + 1
            return False, max(retry_after, 1)

    async def cleanup(self) -> int:
        """Remove expired entries. Returns count of cleaned keys."""
        async with self._lock:
            now = time.time()
            removed = 0
            for key in list(self._windows.keys()):
                self._windows[key] = [ts for ts in self._windows[key] if ts > now - 300]
                if not self._windows[key]:
                    del self._windows[key]
                    removed += 1
            return removed


# ---------------------------------------------------------------------------
# Redis-backed rate limiter
# ---------------------------------------------------------------------------


class _RedisRateLimiter:
    """Sliding window rate limiter using Redis sorted sets."""

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._client = None
        self._available = False

    async def _ensure_client(self):
        if self._client is not None or self._available is False:
            return self._client

        try:
            import redis.asyncio as redis

            self._client = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            await self._client.ping()
            self._available = True
            log.info("Redis rate limiter connected")
            return self._client
        except Exception as exc:
            log.warning("Redis rate limiter unavailable: %s", exc)
            self._available = False
            self._client = None
            return None

    async def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        client = await self._ensure_client()
        if client is None:
            return True, 0  # Fail open if Redis unavailable

        try:
            import time as _time

            now = _time.time()
            cutoff = now - window_seconds
            redis_key = f"ratelimit:{key}"

            # Use a pipeline for atomicity
            pipe = client.pipeline()
            # Remove old entries
            pipe.zremrangebyscore(redis_key, 0, cutoff)
            # Count current entries
            pipe.zcard(redis_key)
            results = await pipe.execute()

            current_count = results[1]

            if current_count < max_requests:
                # Add this request
                pipe2 = client.pipeline()
                pipe2.zadd(redis_key, {f"{now}:{id(self)}": now})
                pipe2.expire(redis_key, window_seconds + 1)
                await pipe2.execute()
                return True, 0

            # Rate limited
            oldest_entries = await client.zrange(redis_key, 0, 0, withscores=True)
            if oldest_entries:
                oldest_ts = oldest_entries[0][1]
                retry_after = int(oldest_ts + window_seconds - now) + 1
            else:
                retry_after = window_seconds

            return False, max(retry_after, 1)

        except Exception as exc:
            log.warning("Redis rate limit error: %s", exc)
            self._available = False
            return True, 0  # Fail open


# ---------------------------------------------------------------------------
# Unified rate limiter (Redis + memory fallback)
# ---------------------------------------------------------------------------


class UnifiedRateLimiter:
    """
    Unified rate limiter. Uses Redis if available, falls back to memory.
    """

    def __init__(self):
        redis_url = getattr(settings, "redis_url", None) or ""
        self._redis = _RedisRateLimiter(redis_url) if redis_url else None
        self._memory = _MemoryRateLimiter()

    async def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        # Try Redis first
        if self._redis:
            allowed, retry_after = await self._redis.is_allowed(key, max_requests, window_seconds)
            if not allowed:
                return False, retry_after

        # Also check memory limiter (defense in depth)
        return await self._memory.is_allowed(key, max_requests, window_seconds)

    async def cleanup(self) -> None:
        await self._memory.cleanup()


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

# Endpoint-specific rate limit configurations (requests per window)
_ENDPOINT_LIMITS = {
    "/api/analyze": {"requests": 10, "window": 60},        # 10 per minute
    "/api/quality-check": {"requests": 30, "window": 60},   # 30 per minute
    "/api/guidance/chat": {"requests": 20, "window": 60},   # 20 per minute
    "/api/screenings/save-current": {"requests": 5, "window": 60},  # 5 per minute
}

_DEFAULT_LIMIT = {"requests": 60, "window": 60}  # 60 per minute default

# Authenticated user multipliers (higher limits for logged-in users)
_AUTH_MULTIPLIER = 2.0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Enhanced sliding window rate limiter.

    Configuration via environment variables or defaults:
    - RATE_LIMIT_ANALYZE_RPM (default: 10)
    - RATE_LIMIT_QUALITY_RPM (default: 30)
    - RATE_LIMIT_DEFAULT_RPM (default: 60)
    """

    def __init__(
        self,
        app,
        *,
        analyze_rpm: int | None = None,
        quality_rpm: int | None = None,
        default_rpm: int | None = None,
    ) -> None:
        super().__init__(app)

        # Override defaults from environment or constructor args
        self._endpoint_limits = dict(_ENDPOINT_LIMITS)

        if analyze_rpm is not None:
            self._endpoint_limits["/api/analyze"]["requests"] = analyze_rpm
        elif hasattr(settings, "rate_limit_analyze_rpm"):
            self._endpoint_limits["/api/analyze"]["requests"] = settings.rate_limit_analyze_rpm

        if quality_rpm is not None:
            self._endpoint_limits["/api/quality-check"]["requests"] = quality_rpm
        elif hasattr(settings, "rate_limit_quality_rpm"):
            self._endpoint_limits["/api/quality-check"]["requests"] = settings.rate_limit_quality_rpm

        if default_rpm is not None:
            _DEFAULT_LIMIT["requests"] = default_rpm

        self._limiter = UnifiedRateLimiter()
        self._cleanup_interval = 300
        self._last_cleanup = time.time()

        # Start background cleanup task
        self._cleanup_task: asyncio.Task | None = None

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Only rate-limit POST/PUT/DELETE requests to API routes
        if request.method not in ("POST", "PUT", "DELETE") or not request.url.path.startswith("/api/"):
            return await call_next(request)

        client_ip = self._client_ip(request)
        path = request.url.path

        # Get limit config for this path
        limit_config = self._endpoint_limits.get(path, dict(_DEFAULT_LIMIT))
        max_requests = limit_config["requests"]
        window_seconds = limit_config["window"]

        # Check if authenticated user gets higher limits
        auth_header = request.headers.get("authorization", "")
        is_authenticated = auth_header.startswith("Bearer ")
        if is_authenticated:
            max_requests = int(max_requests * _AUTH_MULTIPLIER)

        # Build rate limit key
        bucket_key = f"{client_ip}:{path}"

        # Check rate limit
        allowed, retry_after = await self._limiter.is_allowed(bucket_key, max_requests, window_seconds)

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded. Please slow down.",
                    "retry_after_seconds": retry_after,
                    "path": path,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Window": f"{window_seconds}s",
                },
            )

        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Window"] = f"{window_seconds}s"

        # Periodic cleanup
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self._last_cleanup = now
            asyncio.create_task(self._limiter.cleanup())

        return response

    @staticmethod
    def _client_ip(request: Request) -> str:
        """Extract client IP, respecting proxy headers."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"
