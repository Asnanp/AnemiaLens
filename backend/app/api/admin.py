"""
Admin analytics dashboard API.
Provides global system stats for internal monitoring.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models.screening import Screening
from app.models.user import User

log = logging.getLogger("anemialens.admin")

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AdminStatsResponse(BaseModel):
    total_users: int
    total_scans: int
    scans_by_band: dict[str, int]
    avg_processing_time_ms: float
    blocked_scans: int


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Get global platform statistics (Admin only)",
    dependencies=[Depends(require_admin)],
)
async def get_system_stats(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> AdminStatsResponse:
    # 1. Total users
    users_result = await db.execute(select(func.count()).select_from(User))
    total_users = users_result.scalar() or 0

    # 2. Total scans
    scans_result = await db.execute(select(func.count()).select_from(Screening))
    total_scans = scans_result.scalar() or 0

    # 3. Blocked scans (quality failures)
    blocked_result = await db.execute(
        select(func.count()).select_from(Screening).where(Screening.blocked == True)
    )
    blocked_scans = blocked_result.scalar() or 0

    # 4. Scans by triage band
    bands_result = await db.execute(
        select(Screening.triage_band, func.count(Screening.id))
        .group_by(Screening.triage_band)
    )
    scans_by_band = dict(bands_result.all())  # -> {'low_risk': 10, 'moderate_risk': 5, ...}

    # 5. Average processing time
    time_result = await db.execute(
        select(func.avg(Screening.processing_time_ms)).where(Screening.processing_time_ms > 0)
    )
    avg_processing_time = time_result.scalar() or 0.0

    return AdminStatsResponse(
        total_users=total_users,
        total_scans=total_scans,
        scans_by_band=scans_by_band,
        avg_processing_time_ms=avg_processing_time,
        blocked_scans=blocked_scans,
    )
