"""
Screening history API — list, detail, delete past screenings.

Performance optimizations:
- Response caching with TTL for list endpoint
- Optimized queries with select() column pruning
- Index-aware pagination
- Cache invalidation on delete/save
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.screening import Screening
from app.models.user import User
from app.schemas import AnalyzeResponse
from app.services.cache import response_cache
from app.services.screening_store import persist_screening_result

log = logging.getLogger("anemialens.history")

router = APIRouter(prefix="/api/screenings", tags=["history"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ScreeningSummary(BaseModel):
    uid: str
    triage_band: str
    triage_label: str
    triage_score: float
    anemia_risk: float | None
    predicted_hemoglobin: float | None
    confidence: float | None
    screening_label: str | None
    urgency_label: str | None
    headline: str | None
    guidance_source: str
    processing_time_ms: float
    created_at: str


class ScreeningDetail(ScreeningSummary):
    symptoms_json: str | None
    share_text: str | None
    full_response_json: str | None
    blocked: bool
    quality_passed: bool
    processing_path: str
    model_source: str | None
    language: str | None
    region: str | None


class ScreeningListResponse(BaseModel):
    screenings: list[ScreeningSummary]
    total: int
    page: int
    page_size: int


class DeleteResponse(BaseModel):
    deleted: bool
    uid: str


class SaveScreeningRequest(BaseModel):
    analysis: AnalyzeResponse


class SaveScreeningResponse(BaseModel):
    saved: bool
    uid: str
    message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=ScreeningListResponse,
    summary="List user's screening history",
)
async def list_screenings(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1, le=1000),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ScreeningListResponse:
    # Try cache first
    cache_key = response_cache.make_key(
        "/api/screenings",
        query_params={"page": page, "page_size": page_size},
        user_id=user.id,
    )
    cached = await response_cache.get(cache_key)
    if cached is not None:
        return ScreeningListResponse(**cached)

    # Optimized query: only select needed columns
    count_result = await db.execute(
        select(func.count()).where(Screening.user_id == user.id)
    )
    total = count_result.scalar() or 0

    # Fetch page with column-level selection for efficiency
    offset = (page - 1) * page_size
    result = await db.execute(
        select(
            Screening.uid,
            Screening.triage_band,
            Screening.triage_label,
            Screening.triage_score,
            Screening.anemia_risk,
            Screening.predicted_hemoglobin,
            Screening.confidence,
            Screening.screening_label,
            Screening.urgency_label,
            Screening.headline,
            Screening.guidance_source,
            Screening.processing_time_ms,
            Screening.created_at,
        )
        .where(Screening.user_id == user.id)
        .order_by(desc(Screening.created_at))
        .offset(offset)
        .limit(page_size)
    )
    rows = result.all()

    response = ScreeningListResponse(
        screenings=[
            ScreeningSummary(
                uid=r.uid,
                triage_band=r.triage_band,
                triage_label=r.triage_label,
                triage_score=r.triage_score,
                anemia_risk=r.anemia_risk,
                predicted_hemoglobin=r.predicted_hemoglobin,
                confidence=r.confidence,
                screening_label=r.screening_label,
                urgency_label=r.urgency_label,
                headline=r.headline,
                guidance_source=r.guidance_source,
                processing_time_ms=r.processing_time_ms,
                created_at=r.created_at.isoformat(),
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )

    # Cache for 30 seconds (short enough for reasonable freshness)
    await response_cache.set(cache_key, response.model_dump(), ttl_seconds=30)

    return response


@router.get(
    "/export/csv",
    summary="Export screening history as CSV (Pro only)",
    tags=["history"],
)
async def export_screenings_csv(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Export screening history as CSV. Requires Pro subscription or admin role."""
    if user.subscription_tier != "pro" and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="CSV export is a Pro feature. Upgrade to download your data.",
        )

    result = await db.execute(
        select(Screening)
        .where(Screening.user_id == user.id)
        .order_by(desc(Screening.created_at))
        .limit(1000)
    )
    screenings = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "date", "triage_band", "triage_label", "anemia_risk_%",
        "hemoglobin_g_dL", "confidence_%", "screening_label",
        "guidance_source", "processing_ms",
    ])
    for s in screenings:
        writer.writerow([
            s.created_at.strftime("%Y-%m-%d %H:%M"),
            s.triage_band,
            s.triage_label,
            f"{(s.anemia_risk or 0) * 100:.1f}" if s.anemia_risk is not None else "",
            f"{s.predicted_hemoglobin:.1f}" if s.predicted_hemoglobin is not None else "",
            f"{(s.confidence or 0) * 100:.1f}" if s.confidence is not None else "",
            s.screening_label or "",
            s.guidance_source,
            f"{s.processing_time_ms:.0f}",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=anemialens_history.csv"},
    )


@router.get(
    "/{screening_uid}",
    response_model=ScreeningDetail,
    summary="Get full screening detail",
)
async def get_screening(
    screening_uid: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScreeningDetail:
    result = await db.execute(
        select(Screening).where(
            Screening.uid == screening_uid,
            Screening.user_id == user.id,
        )
    )
    screening = result.scalar_one_or_none()
    if screening is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screening not found.",
        )

    return ScreeningDetail(
        uid=screening.uid,
        triage_band=screening.triage_band,
        triage_label=screening.triage_label,
        triage_score=screening.triage_score,
        anemia_risk=screening.anemia_risk,
        predicted_hemoglobin=screening.predicted_hemoglobin,
        confidence=screening.confidence,
        screening_label=screening.screening_label,
        urgency_label=screening.urgency_label,
        headline=screening.headline,
        guidance_source=screening.guidance_source,
        processing_time_ms=screening.processing_time_ms,
        created_at=screening.created_at.isoformat(),
        symptoms_json=screening.symptoms_json,
        share_text=screening.share_text,
        full_response_json=screening.full_response_json,
        blocked=screening.blocked,
        quality_passed=screening.quality_passed,
        processing_path=screening.processing_path,
        model_source=screening.model_source,
        language=screening.language,
        region=screening.region,
    )


@router.delete(
    "/{screening_uid}",
    response_model=DeleteResponse,
    summary="Delete a screening record",
)
async def delete_screening(
    screening_uid: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeleteResponse:
    result = await db.execute(
        select(Screening).where(
            Screening.uid == screening_uid,
            Screening.user_id == user.id,
        )
    )
    screening = result.scalar_one_or_none()
    if screening is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screening not found.",
        )

    await db.delete(screening)
    log.info("Screening deleted: %s by user %s", screening_uid, user.uid)

    # Invalidate user's history cache
    await response_cache.clear()

    return DeleteResponse(deleted=True, uid=screening_uid)


@router.post(
    "/save-current",
    response_model=SaveScreeningResponse,
    summary="Save the current screening result to the authenticated account",
)
async def save_current_screening(
    body: SaveScreeningRequest,
    user: Annotated[User, Depends(get_current_user)],
) -> SaveScreeningResponse:
    analysis = body.analysis
    screening = await persist_screening_result(
        request_id=analysis.analysis_meta.request_id,
        analysis=analysis,
        user_id=user.id,
        processing_time_ms=analysis.analysis_meta.processing_time_ms,
    )
    log.info("Screening saved to account: %s by user %s", screening.uid, user.uid)
    return SaveScreeningResponse(
        saved=True,
        uid=screening.uid,
        message="Screening saved to your account history.",
    )
