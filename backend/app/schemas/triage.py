"""
Triage result schema.
"""

from __future__ import annotations

from functools import cached_property

from pydantic import BaseModel, Field
from typing import Annotated

from app.schemas.common import TriageBand


class TriageResult(BaseModel):
    """
    Clinical triage decision combining image quality, ML prediction,
    and self-reported symptoms.
    """

    band: TriageBand = Field(description="Risk band assigned by the triage service.")
    score: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        description="Composite triage score in [0, 1]."
    )
    label: str = Field(description="Human-readable band label.")
    summary: str = Field(
        description="Plain-language explanation of the triage outcome (2-3 sentences)."
    )
    disclaimer: str = Field(
        description="Regulatory disclaimer — always rendered in the UI."
    )

    @cached_property
    def requires_urgent_followup(self) -> bool:
        return self.band == "high_concern"

    @cached_property
    def requires_retake(self) -> bool:
        return self.band == "uncertain_retake_needed"
