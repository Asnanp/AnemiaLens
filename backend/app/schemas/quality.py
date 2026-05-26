"""
Image quality assessment schemas.
"""

from __future__ import annotations

from functools import cached_property
from typing import Literal

from pydantic import BaseModel, Field, field_validator

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

    @field_validator("issues", mode="before")
    @classmethod
    def _coerce_legacy_issues(cls, value: object) -> object:
        if value is None:
            return []
        if not isinstance(value, list):
            return value

        def from_string(raw: str) -> dict[str, str]:
            normalized = raw.strip().lower().replace("-", "_").replace(" ", "_")
            if normalized in {"blurry", "blur", "soft"}:
                return {
                    "code": "blur_detected",
                    "severity": "blocking",
                    "title": "Image looks blurry",
                    "message": "Hold steady, tap to focus, and retake the photo without motion.",
                }
            if normalized in {"overexposed", "glare", "bright", "poor_lighting"}:
                return {
                    "code": "poor_lighting",
                    "severity": "blocking",
                    "title": "Lighting is not usable",
                    "message": "Use bright, even light without flash glare or heavy shadows.",
                }
            return {
                "code": "poor_lighting",
                "severity": "warning",
                "title": "Capture quality warning",
                "message": raw.strip() or "Review the capture quality before screening.",
            }

        coerced: list[object] = []
        for item in value:
            coerced.append(from_string(item) if isinstance(item, str) else item)
        return coerced

    @cached_property
    def blocking_issues(self) -> list[QualityIssue]:
        return [i for i in self.issues if i.severity == "blocking"]

    @cached_property
    def warning_issues(self) -> list[QualityIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @cached_property
    def issue_codes(self) -> frozenset[str]:
        return frozenset(i.code for i in self.issues)
