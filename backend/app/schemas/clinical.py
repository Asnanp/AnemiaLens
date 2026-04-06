"""
Clinical brief and signal breakdown schemas.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.common import PriorityWindow, ReliabilityFlag


class SignalBreakdown(BaseModel):
    image_risk: Annotated[float, Field(ge=0.0, le=1.0)] | None = Field(
        default=None,
        description="Image-model risk signal before symptom fusion, if model inference ran.",
    )
    symptom_score: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        description="Normalized symptom score contributed by the questionnaire."
    )
    fused_score: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        description="Final triage score after combining the image-model signal and symptoms."
    )
    image_weight: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        description="Weight applied to the image-model signal in the triage fusion."
    )
    symptom_weight: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        description="Weight applied to the symptom score in the triage fusion."
    )
    symptom_burden: Literal["none", "mild", "moderate", "severe"] = Field(
        description="Qualitative symptom burden derived from the questionnaire."
    )
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] | None = Field(
        default=None,
        description="Model confidence when inference ran."
    )
    uncertainty: Annotated[float, Field(ge=0.0, le=1.0)] | None = Field(
        default=None,
        description="Model uncertainty when inference ran."
    )
    reliability_flag: ReliabilityFlag | None = Field(
        default=None,
        description="Reliability tier attached to the model output when inference ran."
    )


class ClinicalBrief(BaseModel):
    headline: str = Field(description="Short clinical-style title for the run.")
    verdict: str = Field(description="One-paragraph interpretation grounded in the multilayer pipeline.")
    action_window: PriorityWindow = Field(description="Safest next-action window for this run.")
    action_label: str = Field(description="Human-readable label for the next-action window.")
    signal_breakdown: SignalBreakdown = Field(
        description="Structured breakdown of the image, symptom, and fused triage signals."
    )
    supporting_evidence: list[str] = Field(
        description="Grounded facts that support the current screening result.",
        min_length=1,
    )
    limiting_factors: list[str] = Field(
        description="Warnings or uncertainty factors that limit how strongly the result should be used.",
        min_length=1,
    )
    safety_checks: list[str] = Field(
        description="Safety and governance checks applied during this run.",
        min_length=1,
    )
    recommended_actions: list[str] = Field(
        description="Concrete next actions carried forward from the guidance and triage layers.",
        min_length=1,
    )
    share_text: str = Field(
        description="Copy-ready clinical brief text for demo, handoff, or export."
    )
