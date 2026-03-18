"""
Screening history API — list, detail, delete past screenings.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.screening import Screening
from app.models.user import User

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
    # Count total
    count_result = await db.execute(
        select(func.count()).where(Screening.user_id == user.id)
    )
    total = count_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Screening)
        .where(Screening.user_id == user.id)
        .order_by(desc(Screening.created_at))
        .offset(offset)
        .limit(page_size)
    )
    screenings = result.scalars().all()

    return ScreeningListResponse(
        screenings=[
            ScreeningSummary(
                uid=s.uid,
                triage_band=s.triage_band,
                triage_label=s.triage_label,
                triage_score=s.triage_score,
                anemia_risk=s.anemia_risk,
                predicted_hemoglobin=s.predicted_hemoglobin,
                confidence=s.confidence,
                screening_label=s.screening_label,
                urgency_label=s.urgency_label,
                headline=s.headline,
                guidance_source=s.guidance_source,
                processing_time_ms=s.processing_time_ms,
                created_at=s.created_at.isoformat(),
            )
            for s in screenings
        ],
        total=total,
        page=page,
        page_size=page_size,
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
    return DeleteResponse(deleted=True, uid=screening_uid)
