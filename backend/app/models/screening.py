"""Screening ORM model — persists every analysis result.

Performance optimizations:
- Composite index on (user_id, created_at) for history queries
- Index on triage_band for filtering by risk band
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Screening(Base):
    __tablename__ = "screenings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    request_id: Mapped[str] = mapped_column(String(16), nullable=False)

    # Triage
    triage_band: Mapped[str] = mapped_column(String(32), nullable=False)
    triage_score: Mapped[float] = mapped_column(Float, nullable=False)
    triage_label: Mapped[str] = mapped_column(String(64), nullable=False)

    # Prediction (nullable — blocked scans have no prediction)
    anemia_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_hemoglobin: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    uncertainty: Mapped[float | None] = mapped_column(Float, nullable=True)
    screening_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model_source: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Quality
    quality_passed: Mapped[bool] = mapped_column(default=True, nullable=False)
    blocked: Mapped[bool] = mapped_column(default=False, nullable=False)
    processing_path: Mapped[str] = mapped_column(String(32), nullable=False, default="roi_crop")

    # Guidance
    guidance_source: Mapped[str] = mapped_column(String(16), default="fallback", nullable=False)

    # Symptoms (stored as JSON text)
    symptoms_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Full response (stored as JSON for export)
    full_response_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Handoff
    share_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    urgency_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    headline: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Meta
    processing_time_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )

    # Composite index for history queries: order by created_at DESC where user_id = ?
    __table_args__ = (
        Index("ix_screenings_user_created", "user_id", "created_at"),
        Index("ix_screenings_triage_band", "triage_band"),
    )

    def __repr__(self) -> str:
        return f"<Screening {self.uid!r} band={self.triage_band!r}>"
