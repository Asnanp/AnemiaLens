"""
In-process token-bucket rate limiter middleware for FastAPI.

Tracks requests per client IP. Separate buckets for different endpoint groups.
No external dependencies (no Redis required).
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


@dataclass
class _Bucket:
    tokens: float = 10.0
    last_refill: float = field(default_factory=time.monotonic)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token-bucket rate limiter.

    Configuration:
        analyze_rpm:  max requests/minute on /api/analyze
        quality_rpm:  max requests/minute on /api/quality-check
        default_rpm:  fallback for other POST routes
    """

    def __init__(
        self,
        app,
        *,
        analyze_rpm: int = 10,
        quality_rpm: int = 30,
        default_rpm: int = 60,
    ) -> None:
        super().__init__(app)
        self.limits: dict[str, int] = {
            "/api/analyze": analyze_rpm,
            "/api/quality-check": quality_rpm,
        }
        self.default_rpm = default_rpm
        self._buckets: dict[str, _Bucket] = defaultdict(_Bucket)
        self._cleanup_interval = 300  # seconds
        self._last_cleanup = time.monotonic()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Only rate-limit POST requests to API routes
        if request.method != "POST" or not request.url.path.startswith("/api/"):
            return await call_next(request)

        client_ip = self._client_ip(request)
        path = request.url.path
        rpm = self.limits.get(path, self.default_rpm)
        bucket_key = f"{client_ip}:{path}"

        bucket = self._buckets[bucket_key]
        now = time.monotonic()

        # Refill tokens
        elapsed = now - bucket.last_refill
        refill = elapsed * (rpm / 60.0)
        bucket.tokens = min(rpm, bucket.tokens + refill)
        bucket.last_refill = now

        if bucket.tokens < 1.0:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded. Please slow down.",
                    "retry_after_seconds": int(60 / max(rpm, 1)),
                },
                headers={"Retry-After": str(int(60 / max(rpm, 1)))},
            )

        bucket.tokens -= 1.0

        # Periodic cleanup of stale buckets
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup(now)

        return await call_next(request)

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup(self, now: float) -> None:
        stale_keys = [
            key
            for key, bucket in self._buckets.items()
            if now - bucket.last_refill > 120
        ]
        for key in stale_keys:
            del self._buckets[key]
        self._last_cleanup = now
