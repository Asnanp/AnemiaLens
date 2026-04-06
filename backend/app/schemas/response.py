"""
HTTP response envelope schemas: AnalyzeResponse, QualityCheckResponse, chat types, ROI previews.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.clinical import ClinicalBrief
from app.schemas.decision import DecisionAudit
from app.schemas.guidance import GuidanceResult
from app.schemas.handoff import HandoffSummary
from app.schemas.insight import CaseInsightPack
from app.schemas.meta import AnalysisMeta
from app.schemas.patient import SymptomInput
from app.schemas.prediction import PredictionResult
from app.schemas.quality import QualityAssessment
from app.schemas.structured_case import StructuredCaseRecord
from app.schemas.triage import TriageResult
from app.schemas.workflow import PatientProfile, WorkflowStage
from app.schemas.common import GuidanceSource


class RoiBox(BaseModel):
    x: int = Field(ge=0, description="Left coordinate of the ROI box in the original image.")
    y: int = Field(ge=0, description="Top coordinate of the ROI box in the original image.")
    width: int = Field(ge=0, description="Width of the ROI box in the original image.")
    height: int = Field(ge=0, description="Height of the ROI box in the original image.")


class RoiPreview(BaseModel):
    source: str = Field(description="Which extraction strategy produced the preview image.")
    extracted: bool = Field(
        description="True when a dedicated conjunctival ROI was isolated from the frame."
    )
    extraction_confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        description="Confidence that the extracted region contains the exposed conjunctiva."
    )
    original_data_url: str | None = Field(default=None, description="Compact data URL for the raw ROI preview image.")
    enhanced_data_url: str | None = Field(
        default=None,
        description="Compact data URL for the lighting-corrected, sharpened ROI preview image.",
    )
    frame_width: int | None = Field(
        default=None,
        description="Original uploaded image width.",
    )
    frame_height: int | None = Field(
        default=None,
        description="Original uploaded image height.",
    )
    roi_box: RoiBox | None = Field(
        default=None,
        description="Detected lower-inner-eyelid rectangle in original-image coordinates.",
    )
    preview_sharpness: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.0,
        description="Preview sharpness score after enhancement, normalised to [0,1].",
    )
    preview_contrast: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.0,
        description="Preview contrast score after enhancement, normalised to [0,1].",
    )
    preview_tone_balance: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.0,
        description="How balanced the preview exposure is after enhancement, normalised to [0,1].",
    )
    enhancement_summary: str = Field(
        default="ROI preview unavailable.",
        description="Plain-language explanation of what the ROI enhancement achieved.",
    )


class QualityCheckResponse(BaseModel):
    quality: QualityAssessment
    roi_preview: RoiPreview | None = Field(
        default=None,
        description="Original and enhanced ROI previews used to explain what region the system focused on.",
    )


class AnalyzeResponse(BaseModel):
    """
    Full analysis response returned by POST /api/analyze.

    blocked=True means image quality failed and no ML prediction was
    attempted.  In that case prediction will be None.
    """

    blocked: bool = Field(
        description="True if image quality fails and analysis was skipped."
    )
    quality: QualityAssessment
    roi_preview: RoiPreview | None = Field(
        default=None,
        description="Original and enhanced ROI previews used to explain what region the system focused on.",
    )
    prediction: PredictionResult | None = Field(
        default=None,
        description="ML prediction — None when blocked=True.",
    )
    decision_audit: DecisionAudit
    triage: TriageResult
    guidance: GuidanceResult
    insight_pack: CaseInsightPack
    clinical_brief: ClinicalBrief
    handoff_summary: HandoffSummary
    analysis_meta: AnalysisMeta
    patient_profile: PatientProfile
    workflow_stages: list[WorkflowStage] = Field(
        description="Explicit multi-step screening workflow stages for this run.",
        min_length=4,
    )
    structured_case: StructuredCaseRecord = Field(
        description="FHIR-style structured case summary suitable for provider-facing views or export."
    )
    symptoms: SymptomInput
    language: str | None = Field(default=None, description="BCP-47 language tag or plain name.")
    region: str | None = Field(default=None, description="Geographic region for localised guidance.")


class GuidanceChatMessage(BaseModel):
    role: Literal["user", "assistant"] = Field(description="Speaker role in the chat exchange.")
    content: str = Field(min_length=1, description="Plain text message content.")


class GuidanceChatRequest(BaseModel):
    analysis: AnalyzeResponse = Field(description="Current screening analysis context to ground the reply.")
    message: str = Field(min_length=1, description="User follow-up question about this screening.")
    history: list[GuidanceChatMessage] = Field(default_factory=list, description="Prior chat turns for continuity.")


class GuidanceChatResponse(BaseModel):
    source: GuidanceSource = Field(default="fallback", description="Which guidance strategy produced this reply.")
    model_used: str | None = Field(default=None, description="LLM model identifier, if available.")
    provider_used: str | None = Field(default=None, description="Inference provider, if applicable.")
    message: str = Field(description="Assistant reply grounded in the screening result.")
