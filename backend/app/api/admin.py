"""
Admin analytics dashboard API.
Provides global system stats for internal monitoring.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models.screening import Screening
from app.models.user import User

log = logging.getLogger("anemialens.admin")

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AdminTrendPoint(BaseModel):
    date: str
    label: str
    scans: int
    blocked: int


class AdminRecentScreeningItem(BaseModel):
    uid: str
    triage_band: str
    triage_label: str
    screening_label: str | None
    confidence: float | None
    predicted_hemoglobin: float | None
    processing_time_ms: float
    guidance_source: str
    processing_path: str
    headline: str | None
    blocked: bool
    created_at: str


class AdminStatsResponse(BaseModel):
    total_users: int
    active_users: int
    total_scans: int
    scans_by_band: dict[str, int]
    avg_processing_time_ms: float
    blocked_scans: int
    blocked_rate: float
    pro_users: int
    free_users: int
    pro_adoption_rate: float
    avg_confidence: float
    avg_risk: float
    recent_scans_24h: int
    scans_last_7_days: list[AdminTrendPoint]
    processing_paths: dict[str, int]
    guidance_sources: dict[str, int]
    recent_screenings: list[AdminRecentScreeningItem]


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


def _safe_ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _normalise_count_map(rows: list[tuple[str | None, int]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key, count in rows:
        label = key or "unknown"
        counts[label] = int(count or 0)
    return counts


def _to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat() if dt.tzinfo else dt.isoformat()


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Get global platform statistics (Admin only)",
    dependencies=[Depends(require_admin)],
)
async def get_system_stats(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> AdminStatsResponse:
    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)
    since_7d = now - timedelta(days=6)

    users_result = await db.execute(select(func.count()).select_from(User))
    total_users = int(users_result.scalar() or 0)

    active_users_result = await db.execute(
        select(func.count()).select_from(User).where(User.is_active.is_(True))
    )
    active_users = int(active_users_result.scalar() or 0)

    pro_result = await db.execute(
        select(func.count()).select_from(User).where(User.subscription_tier == "pro")
    )
    pro_users = int(pro_result.scalar() or 0)

    scans_result = await db.execute(select(func.count()).select_from(Screening))
    total_scans = int(scans_result.scalar() or 0)

    blocked_result = await db.execute(
        select(func.count()).select_from(Screening).where(Screening.blocked.is_(True))
    )
    blocked_scans = int(blocked_result.scalar() or 0)

    scans_24h_result = await db.execute(
        select(func.count())
        .select_from(Screening)
        .where(Screening.created_at >= since_24h)
    )
    recent_scans_24h = int(scans_24h_result.scalar() or 0)

    bands_result = await db.execute(
        select(Screening.triage_band, func.count(Screening.id)).group_by(Screening.triage_band)
    )
    scans_by_band = _normalise_count_map(list(bands_result.all()))

    time_result = await db.execute(
        select(func.avg(Screening.processing_time_ms)).where(Screening.processing_time_ms > 0)
    )
    avg_processing_time = float(time_result.scalar() or 0.0)

    confidence_result = await db.execute(
        select(func.avg(Screening.confidence)).where(Screening.confidence.is_not(None))
    )
    avg_confidence = float(confidence_result.scalar() or 0.0)

    risk_result = await db.execute(
        select(func.avg(Screening.anemia_risk)).where(Screening.anemia_risk.is_not(None))
    )
    avg_risk = float(risk_result.scalar() or 0.0)

    path_result = await db.execute(
        select(Screening.processing_path, func.count(Screening.id)).group_by(Screening.processing_path)
    )
    processing_paths = _normalise_count_map(list(path_result.all()))

    guidance_result = await db.execute(
        select(Screening.guidance_source, func.count(Screening.id)).group_by(Screening.guidance_source)
    )
    guidance_sources = _normalise_count_map(list(guidance_result.all()))

    recent_activity_result = await db.execute(
        select(Screening.created_at, Screening.blocked)
        .where(Screening.created_at >= since_7d)
        .order_by(Screening.created_at.asc())
    )
    trend_seed = {
        (now.date() - timedelta(days=offset)).isoformat(): {"scans": 0, "blocked": 0}
        for offset in range(6, -1, -1)
    }
    for created_at, blocked in recent_activity_result.all():
        if created_at is None:
            continue
        day_key = (
            created_at.astimezone(timezone.utc).date().isoformat()
            if created_at.tzinfo
            else created_at.date().isoformat()
        )
        if day_key not in trend_seed:
            continue
        trend_seed[day_key]["scans"] += 1
        trend_seed[day_key]["blocked"] += int(bool(blocked))

    scans_last_7_days = [
        AdminTrendPoint(
            date=day_key,
            label=datetime.fromisoformat(day_key).strftime("%a"),
            scans=payload["scans"],
            blocked=payload["blocked"],
        )
        for day_key, payload in trend_seed.items()
    ]

    recent_screenings_result = await db.execute(
        select(Screening).order_by(desc(Screening.created_at)).limit(6)
    )
    recent_screenings = recent_screenings_result.scalars().all()

    return AdminStatsResponse(
        total_users=total_users,
        active_users=active_users,
        total_scans=total_scans,
        scans_by_band=scans_by_band,
        avg_processing_time_ms=avg_processing_time,
        blocked_scans=blocked_scans,
        blocked_rate=_safe_ratio(blocked_scans, total_scans),
        pro_users=pro_users,
        free_users=max(total_users - pro_users, 0),
        pro_adoption_rate=_safe_ratio(pro_users, total_users),
        avg_confidence=avg_confidence,
        avg_risk=avg_risk,
        recent_scans_24h=recent_scans_24h,
        scans_last_7_days=scans_last_7_days,
        processing_paths=processing_paths,
        guidance_sources=guidance_sources,
        recent_screenings=[
            AdminRecentScreeningItem(
                uid=screening.uid,
                triage_band=screening.triage_band,
                triage_label=screening.triage_label,
                screening_label=screening.screening_label,
                confidence=screening.confidence,
                predicted_hemoglobin=screening.predicted_hemoglobin,
                processing_time_ms=screening.processing_time_ms,
                guidance_source=screening.guidance_source,
                processing_path=screening.processing_path,
                headline=screening.headline,
                blocked=screening.blocked,
                created_at=_to_iso(screening.created_at),
            )
            for screening in recent_screenings
        ],
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
                created_at=_to_iso(u.created_at),
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
    log.info("Admin toggled %s -> %s", user.email, body.subscription_tier)
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
    log.info("Admin toggled active for %s -> %s", user.email, user.is_active)
    return {"uid": user_uid, "is_active": user.is_active}
