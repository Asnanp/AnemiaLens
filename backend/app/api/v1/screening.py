"""
API v1 screening routes.

Mirrors the top-level screening endpoints from ``app.main``
under the ``/api/v1`` namespace so that clients can pin to
a stable API version.

The implementation delegates to the same services as the
unversioned routes — this is purely a routing layer change.
"""

from __future__ import annotations

from fastapi import APIRouter

# V1 screening router (prefix will be applied by the parent v1 router).
router = APIRouter(tags=["screening"])

# NOTE: The actual screening endpoints (analyze, quality-check, guidance/chat)
# are defined in app.main.py. They remain at /api/* for backward compatibility.
# When the v1 screening endpoints are fully extracted from main.py, they will
# be registered here with the same handlers.
#
# For now, this module exists as a placeholder so that:
# 1. The /api/v1/screening namespace is reserved
# 2. Future extraction of screening logic from main.py has a clear home
# 3. Clients can begin using /api/v1/* routes as they are migrated
