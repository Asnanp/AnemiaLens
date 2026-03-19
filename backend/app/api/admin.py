"""
Admin analytics dashboard API.
Provides global system stats for internal monitoring.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select, desc
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
    pro_users: int
    free_users: int


class AdminUserItem(BaseModel):
    uid: str
    email: str
    full_name: str | None
    role: str
    subscription_tier: str
    scan_count: int
    is_active: bool
    created_at: str


class AdminUsersResponse(BaseModel):
    users: list[AdminUserItem]
    total: int


class TogglePlanRequest(BaseModel):
    subscription_tier: str  # "free" | "pro"


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

    # 6. Pro vs free users
    pro_result = await db.execute(
        select(func.count()).select_from(User).where(User.subscription_tier == "pro")
    )
    pro_users = pro_result.scalar() or 0

    return AdminStatsResponse(
        total_users=total_users,
        total_scans=total_scans,
        scans_by_band=scans_by_band,
        avg_processing_time_ms=avg_processing_time,
        blocked_scans=blocked_scans,
        pro_users=pro_users,
        free_users=total_users - pro_users,
    )


@router.get(
    "/users",
    response_model=AdminUsersResponse,
    summary="List all users (Admin only)",
    dependencies=[Depends(require_admin)],
)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 50,
) -> AdminUsersResponse:
    total_result = await db.execute(select(func.count()).select_from(User))
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        select(User).order_by(desc(User.created_at)).offset(offset).limit(page_size)
    )
    users = result.scalars().all()

    return AdminUsersResponse(
        users=[
            AdminUserItem(
                uid=u.uid,
                email=u.email,
                full_name=u.full_name,
                role=u.role,
                subscription_tier=u.subscription_tier or "free",
                scan_count=u.scan_count,
                is_active=u.is_active,
                created_at=u.created_at.isoformat(),
            )
            for u in users
        ],
        total=total,
    )


@router.patch(
    "/users/{user_uid}/plan",
    summary="Toggle user subscription tier (Admin only)",
    dependencies=[Depends(require_admin)],
)
async def toggle_user_plan(
    user_uid: str,
    body: TogglePlanRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if body.subscription_tier not in ("free", "pro"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tier.")
    result = await db.execute(select(User).where(User.uid == user_uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.subscription_tier = body.subscription_tier
    await db.flush()
    log.info("Admin toggled %s → %s", user.email, body.subscription_tier)
    return {"uid": user_uid, "subscription_tier": body.subscription_tier}


@router.patch(
    "/users/{user_uid}/active",
    summary="Toggle user active status (Admin only)",
    dependencies=[Depends(require_admin)],
)
async def toggle_user_active(
    user_uid: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.uid == user_uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.is_active = not user.is_active
    await db.flush()
    log.info("Admin toggled active for %s → %s", user.email, user.is_active)
    return {"uid": user_uid, "is_active": user.is_active}
