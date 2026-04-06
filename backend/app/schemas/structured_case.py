"""
Structured case record schemas for FHIR-style case summaries.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.common import (
    DietType,
    ReliabilityFlag,
    SexType,
    TriageBand,
)


class StructuredCaseImageQuality(BaseModel):
    status: Literal["acceptable", "warning", "blocked"] = Field(
        description="Image usability status for the final screening flow."
    )
    lighting_condition: str = Field(description="Lighting classification for the capture.")
    lighting_score: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        description="Composite lighting quality score for the case."
    )
    blur_detected: bool = Field(description="Whether the pipeline flagged blur as an issue.")
    eye_region_visible: bool = Field(description="Whether the eye / conjunctiva region was adequately visible.")
    primary_issue: str | None = Field(default=None, description="Most important quality issue, if any.")
    warnings: list[str] = Field(default_factory=list, description="Non-blocking quality issue titles.")


class StructuredCaseScreeningResult(BaseModel):
    risk_level: TriageBand = Field(description="Final triage band used as the case risk level.")
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] | None = Field(
        default=None,
        description="Final model confidence, when inference ran.",
    )
    reliability: ReliabilityFlag | None = Field(
        default=None,
        description="Reliability tier attached to the prediction, when inference ran.",
    )
    predicted_hemoglobin: float | None = Field(
        default=None,
        description="Estimated hemoglobin value in g/dL, when available.",
    )
    anemia_risk: Annotated[float, Field(ge=0.0, le=1.0)] | None = Field(
        default=None,
        description="Raw anemia-like risk score from the image model, when inference ran.",
    )


class StructuredCaseRecord(BaseModel):
    case_id: str = Field(description="Stable case identifier for export, demo, or interoperability surfaces.")
    patient_id: str = Field(description="Patient identifier copied from the intake profile.")
    age: int | None = Field(default=None, description="Approximate patient age in years, if provided.")
    sex: SexType = Field(description="Self-reported sex captured during intake.")
    diet_type: DietType = Field(description="Self-reported diet pattern captured during intake.")
    symptoms: list[str] = Field(default_factory=list, description="Active symptoms captured for this case.")
    image_quality: StructuredCaseImageQuality = Field(description="Structured image quality summary.")
    screening_result: StructuredCaseScreeningResult = Field(description="Structured screening result summary.")
    recommendation: str = Field(description="Primary next-step recommendation for this case.")
    case_summary: str = Field(description="Short clinician-facing summary sentence.")
