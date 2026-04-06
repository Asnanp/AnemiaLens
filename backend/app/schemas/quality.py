"""
Image quality assessment schemas.
"""

from __future__ import annotations

from functools import cached_property
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import IssueCode


class QualityIssue(BaseModel):
    """A single image quality finding."""

    code: IssueCode = Field(description="Machine-readable issue identifier.")
    severity: Literal["warning", "blocking"] = Field(
        default="blocking",
        description=(
            "'blocking' prevents analysis; "
            "'warning' is informational and analysis proceeds."
        ),
    )
    title: str = Field(description="Short human-readable title (<= 60 chars).")
    message: str = Field(
        description="Actionable guidance for the user on how to fix the issue."
    )


class QualityAssessment(BaseModel):
    """
    Result of the image quality pipeline.

    passed=True means no blocking issues were found and ML inference
    should proceed.  Warnings may still be present.
    """

    passed: bool = Field(description="True if no blocking issues were detected.")
    blur_score: float = Field(ge=0.0, description="Laplacian variance (higher = sharper).")
    brightness_score: float = Field(ge=0.0, le=1.0, description="Mean luminance in [0, 1].")
    contrast_score: float = Field(ge=0.0, le=1.0, description="Normalised RMS contrast.")
    framing_score: float = Field(ge=0.0, description="Eye-region occupancy ratio.")
    lighting_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Composite lighting quality score, where higher means more usable lighting.",
    )
    lighting_condition: str = Field(
        default="balanced",
        description="Lighting classification inferred from exposure, glare, shadows, and contrast.",
    )
    lighting_summary: str = Field(
        default="Lighting details unavailable.",
        description="Plain-language explanation of the current lighting condition and what it means for screening.",
    )
    glare_risk: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Estimated risk that glare or clipped highlights are harming the capture.",
    )
    shadow_risk: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Estimated risk that shadows or underexposure are hiding useful signal.",
    )
    issues: list[QualityIssue] = Field(default_factory=list)

    @cached_property
    def blocking_issues(self) -> list[QualityIssue]:
        return [i for i in self.issues if i.severity == "blocking"]

    @cached_property
    def warning_issues(self) -> list[QualityIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @cached_property
    def issue_codes(self) -> frozenset[str]:
        return frozenset(i.code for i in self.issues)
