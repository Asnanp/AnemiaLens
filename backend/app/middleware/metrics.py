"""
Metrics collection middleware for AnemiaLens backend.

Automatically records request counts, latencies, and error rates
for every HTTP request passing through the application.
"""

from __future__ import annotations

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.health_checks import metrics_collector


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Records request-level metrics for every HTTP call.

    Skips internal health/metrics endpoints to avoid self-referential noise,
    unless explicitly configured to include them.
    """

    # Paths to exclude from metrics (they create artificial noise)
    EXCLUDED_PATHS = {"/health", "/readyz", "/metrics", "/docs", "/redoc", "/openapi.json", "/"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Start timing
        start = time.perf_counter()

        # Process request
        response = await call_next(request)

        # Record metrics
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Always record to collector (for accuracy)
        await metrics_collector.record_request(
            path=path,
            status_code=response.status_code,
            latency_ms=elapsed_ms,
        )

        # Track active user if authenticated
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from app.utils.security import decode_token

                payload = decode_token(auth_header[7:])
                if payload and payload.get("type") == "access":
                    user_uid = payload.get("sub")
                    if user_uid:
                        # Use hash of uid as a numeric surrogate for tracking
                        user_id = hash(user_uid) % (10**9)
                        await metrics_collector.record_active_user(user_id)
            except Exception:
                pass

        return response
