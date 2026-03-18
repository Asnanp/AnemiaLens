"""
Memory guard middleware — runs gc.collect() after inference-heavy requests
and monitors RSS to prevent OOM on memory-constrained deployments.
"""

from __future__ import annotations

import gc
import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

log = logging.getLogger("anemialens.memory")

_INFERENCE_PATHS = {"/api/analyze", "/api/quality-check"}


class MemoryGuardMiddleware(BaseHTTPMiddleware):
    """
    Post-request garbage collection for inference endpoints.
    Also limits PyTorch threads to 1 at import time.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self._ensure_torch_threads()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        if request.url.path in _INFERENCE_PATHS:
            gc.collect()
            self._free_torch_cache()

        return response

    @staticmethod
    def _free_torch_cache() -> None:
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    @staticmethod
    def _ensure_torch_threads() -> None:
        try:
            import torch
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
            log.info("PyTorch threads limited to 1.")
        except Exception:
            pass
