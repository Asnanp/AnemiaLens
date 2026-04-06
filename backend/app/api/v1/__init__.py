"""
API v1 — versioned route namespace for AnemiaLens.

This module sets up the ``/api/v1`` namespace for future route versioning.

Current approach:
- Existing routes at ``/api/*`` remain the canonical implementation.
- This v1 router is wired into the app so that the namespace is reserved.
- When breaking changes are needed, route handlers will be extracted into
  v1-specific modules (``app/api/v1/auth.py``, ``app/api/v1/screening.py``, etc.)
  while the old routes at ``/api/*`` become deprecation aliases.

Why not duplicate routes now:
- The existing route handlers are tightly coupled to services in ``app.main``.
- Duplicating them under v1 would create maintenance debt.
- The v1 namespace is reserved so the transition path is clear.

Migration path for v2:
1. Extract route handlers from ``app/main.py`` into ``app/api/v1/screening.py``.
2. Extract feature routers into their own v1 modules.
3. Keep ``/api/*`` as deprecation aliases pointing to v1 handlers.
4. When ready, deprecate ``/api/*`` in favor of ``/api/v1/*``.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["v1"])


@router.get("/meta", summary="API v1 metadata")
async def v1_meta() -> dict:
    """Returns API v1 metadata and migration information."""
    return {
        "version": "1.0.0",
        "status": "active",
        "note": (
            "API v1 namespace is reserved. "
            "Current routes are served at /api/* for backward compatibility. "
            "Feature routers (auth, history, admin, billing, email-report) "
            "are also available under /api/v1/<feature>/*."
        ),
        "features": [
            "auth",
            "history",
            "admin",
            "billing",
            "email-report",
        ],
    }
