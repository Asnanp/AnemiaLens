"""
Decision audit schema — transparent request-level metadata.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import CalibrationBand, DecisionProcessingPath


class DecisionAudit(BaseModel):
    """
    Transparent request-level metadata explaining how a screening result
    was reached and how close it was to the operating threshold.
    """

    processing_path: DecisionProcessingPath = Field(
        description="Whether the result came from the ROI crop, a full-frame rescue, or was blocked."
    )
    calibration_band: CalibrationBand = Field(
        description="Qualitative strength of the final model decision."
    )
    decision_threshold: float | None = Field(
        default=None,
        description="Binary operating threshold used for the anemia risk score, if available.",
    )
    threshold_margin: float | None = Field(
        default=None,
        description="anemia_risk - decision_threshold. Positive means above the screening threshold.",
    )
    quality_warning_codes: list[str] = Field(
        default_factory=list,
        description="Non-blocking quality issue codes still present after quality handling.",
    )
    review_flags: list[str] = Field(
        default_factory=list,
        description="Compact machine-readable review flags for UI and logging.",
    )
    summary: str = Field(
        description="One-sentence explanation of the decision path and confidence."
    )
