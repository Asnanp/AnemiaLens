"""
ML prediction result schemas.
"""

from __future__ import annotations

from functools import cached_property

from pydantic import BaseModel, Field, model_validator
from typing import Annotated

from app.schemas.common import (
    ModelSource,
    ReliabilityFlag,
    ScreeningLabel,
)


class PredictionResult(BaseModel):
    """
    Output of the ML screening model for a single eye image.

    All probability fields are in [0, 1].  predicted_hemoglobin is
    an estimated value in g/dL and may be None for heuristic models
    that do not regress hemoglobin.
    """

    anemia_risk: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        description="Probability of anemia-like signal, 0 = absent, 1 = strong."
    )
    predicted_hemoglobin: float | None = Field(
        default=None,
        description="Estimated haemoglobin level in g/dL, if the model supports regression.",
    )
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        description="Model confidence in its own output."
    )
    uncertainty: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        description="Epistemic uncertainty (Monte Carlo dropout or ensemble spread)."
    )
    reliability_flag: ReliabilityFlag = Field(
        description="Summary reliability tier derived from confidence and uncertainty."
    )
    screening_label: ScreeningLabel = Field(
        description="Categorical screening outcome."
    )
    screening_text: str = Field(
        description="One-sentence plain-language description of the screening result."
    )
    model_source: ModelSource = Field(
        description="Which model or pipeline produced this prediction."
    )
    confidence_breakdown: dict[str, object] | None = Field(
        default=None,
        description="Decomposed confidence view covering capture quality, model stability, threshold stability, and guardrail effects.",
    )
    xai_data: dict[str, str | dict[str, float | list[float]] | list[float] | list[dict[str, float | list[float] | str]]] | None = Field(
        default=None,
        description="Explainable AI data including Grad-CAM heatmaps, bounding boxes, and Conjunctiva Pallor Analysis."
    )
    rich_confidence_metrics: dict[str, str] | None = Field(
        default=None,
        description="Human-readable rich confidence metrics (e.g. 'We are 92% confident', 'Lighting Quality: 85%')."
    )

    @model_validator(mode="after")
    def _confidence_uncertainty_consistent(self) -> "PredictionResult":
        if self.confidence + self.uncertainty > 1.05:
            raise ValueError(
                f"confidence ({self.confidence}) + uncertainty ({self.uncertainty}) > 1.0 — "
                "these values are inconsistent."
            )
        return self

    @cached_property
    def is_high_risk(self) -> bool:
        return self.screening_label == "anemia_likely" and self.reliability_flag != "low"
