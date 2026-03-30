from __future__ import annotations

import json

from app.database import async_session_factory
from app.models.screening import Screening
from app.models.user import User
from app.schemas import AnalyzeResponse


async def persist_screening_result(
    request_id: str,
    analysis: AnalyzeResponse,
    user_id: int | None,
    processing_time_ms: float,
) -> Screening:
    """Persist a completed screening result and optionally attach it to a user."""

    screening = Screening(
        request_id=request_id,
        user_id=user_id,
        triage_band=analysis.triage.band,
        triage_score=analysis.triage.score,
        triage_label=analysis.triage.label,
        anemia_risk=analysis.prediction.anemia_risk if analysis.prediction else None,
        predicted_hemoglobin=analysis.prediction.predicted_hemoglobin if analysis.prediction else None,
        confidence=analysis.prediction.confidence if analysis.prediction else None,
        uncertainty=analysis.prediction.uncertainty if analysis.prediction else None,
        screening_label=analysis.prediction.screening_label if analysis.prediction else None,
        model_source=analysis.prediction.model_source if analysis.prediction else None,
        quality_passed=analysis.quality.passed,
        blocked=analysis.blocked,
        processing_path=analysis.decision_audit.processing_path,
        guidance_source=analysis.guidance.source,
        symptoms_json=json.dumps(analysis.symptoms.model_dump()),
        full_response_json=json.dumps(
            analysis.model_dump(exclude={"roi_preview"}),
            default=str,
        ),
        share_text=analysis.handoff_summary.share_text,
        urgency_label=analysis.handoff_summary.urgency_label,
        headline=analysis.handoff_summary.headline,
        processing_time_ms=processing_time_ms,
        language=analysis.language,
        region=analysis.region,
    )

    async with async_session_factory() as session:
        session.add(screening)
        await session.flush()

        if user_id is not None:
            user = await session.get(User, user_id)
            if user is not None:
                user.scan_count += 1

        await session.commit()
        await session.refresh(screening)
        return screening
