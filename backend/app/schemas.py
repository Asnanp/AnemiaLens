"""
Pydantic schemas for AnemiaLens API requests and responses.

Design principles:
- Every public field has a description (powers OpenAPI docs automatically).
- Boolean-like strings from HTML forms are normalised via _coerce_boolean so
  the API is tolerant of real-world form submissions without being sloppy.
- Computed properties (e.g. SymptomInput.active_count) keep business logic
  close to the data rather than scattered across services.
- Literal unions are used for discriminated fields so the OpenAPI spec
  generates proper enum schemas and clients get type-safe access.
"""

from __future__ import annotations

from functools import cached_property
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Boolean normalisation helpers
# ---------------------------------------------------------------------------

_TRUE_VALUES: frozenset[str] = frozenset({"1", "true", "yes", "y", "on"})
_FALSE_VALUES: frozenset[str] = frozenset({"0", "false", "no", "n", "off", ""})
_NONE_VALUES: frozenset[str] = frozenset({"skip", "unknown", "n/a", "na", "none", "null"})


def _coerce_boolean(value: object, *, allow_none: bool = False) -> bool | None:
    """
    Normalise a value that may arrive as a Python bool, an int (0/1),
    or a string from an HTML form into a proper bool (or None).

    Raises ValueError for values that cannot be mapped.
    """
    if value is None:
        return None if allow_none else False

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)

    if isinstance(value, str):
        normalised = value.strip().lower()
        if allow_none and normalised in _NONE_VALUES:
            return None
        if normalised in _TRUE_VALUES:
            return True
        if normalised in _FALSE_VALUES:
            return False

    raise ValueError(
        f"Cannot coerce {value!r} to bool"
        f"{' or None' if allow_none else ''}. "
        f"Accepted true-ish: {sorted(_TRUE_VALUES)}, "
        f"false-ish: {sorted(_FALSE_VALUES)}"
        + (f", none-ish: {sorted(_NONE_VALUES)}" if allow_none else "")
    )


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class SymptomInput(BaseModel):
    """
    Self-reported symptoms submitted alongside an eye image.

    All boolean fields accept Python bools, integers (0/1), or strings
    ("yes"/"no"/"true"/"false"/"1"/"0" etc.) so HTML form submissions
    work without pre-processing.  heavy_menstrual_bleeding additionally
    accepts "skip"/"unknown"/"n/a" which maps to None (not applicable).
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "fatigue": True,
                "dizziness": False,
                "pale_skin": True,
                "shortness_of_breath": False,
                "heavy_menstrual_bleeding": None,
                "poor_diet_low_iron": True,
            }
        },
    )

    fatigue: bool = Field(default=False, description="Persistent tiredness or lack of energy.")
    dizziness: bool = Field(default=False, description="Feeling lightheaded or unsteady.")
    pale_skin: bool = Field(default=False, description="Noticeably pale or washed-out complexion.")
    shortness_of_breath: bool = Field(
        default=False, description="Breathlessness during normal activity."
    )
    heavy_menstrual_bleeding: bool | None = Field(
        default=None,
        description=(
            "Heavy or prolonged menstrual bleeding. "
            "Use null / 'skip' if not applicable or unknown."
        ),
    )
    poor_diet_low_iron: bool = Field(
        default=False,
        description="Diet consistently low in iron-rich foods.",
    )
    symptom_severity: dict[str, int] | None = Field(
        default=None,
        description=(
            "Optional per-symptom severity levels: 0=none, 1=mild, 2=severe. "
            "Keys match symptom field names. Used to weight the symptom score."
        ),
    )

    # --- Validators --------------------------------------------------------

    @field_validator(
        "fatigue", "dizziness", "pale_skin", "shortness_of_breath", "poor_diet_low_iron",
        mode="before",
    )
    @classmethod
    def _normalise_required_bool(cls, v: object) -> bool:
        result = _coerce_boolean(v, allow_none=False)
        assert isinstance(result, bool)
        return result

    @field_validator("heavy_menstrual_bleeding", mode="before")
    @classmethod
    def _normalise_optional_bool(cls, v: object) -> bool | None:
        return _coerce_boolean(v, allow_none=True)

    # --- Computed helpers --------------------------------------------------

    @cached_property
    def active_count(self) -> int:
        """Number of symptoms explicitly marked True."""
        return sum([
            self.fatigue,
            self.dizziness,
            self.pale_skin,
            self.shortness_of_breath,
            bool(self.heavy_menstrual_bleeding),
            self.poor_diet_low_iron,
        ])

    @cached_property
    def symptom_burden(self) -> Literal["none", "mild", "moderate", "severe"]:
        """
        Qualitative symptom burden used by the triage service to
        modulate the final risk band.
        """
        n = self.active_count
        if n == 0:
            return "none"
        if n <= 1:
            return "mild"
        if n <= 3:
            return "moderate"
        return "severe"

    @cached_property
    def as_dict(self) -> dict[str, bool | None]:
        """Plain dict representation — useful for prompt serialisation."""
        return {
            "fatigue": self.fatigue,
            "dizziness": self.dizziness,
            "pale_skin": self.pale_skin,
            "shortness_of_breath": self.shortness_of_breath,
            "heavy_menstrual_bleeding": self.heavy_menstrual_bleeding,
            "poor_diet_low_iron": self.poor_diet_low_iron,
        }


# ---------------------------------------------------------------------------
# Quality assessment
# ---------------------------------------------------------------------------

IssueCode = Literal[
    "blur_detected",
    "eye_not_visible",
    "poor_lighting",
    "resolution_too_low",
    "overexposed",
    "low_contrast",
    "framing_off",
    "bad_framing",
    "roi_cropped",
]


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
    title: str = Field(description="Short human-readable title (≤ 60 chars).")
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


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

ReliabilityFlag = Literal["low", "medium", "high"]
ScreeningLabel = Literal["anemia_likely", "anemia_unlikely", "uncertain"]
ModelSource = Literal[
    "efficientnet-b0-ft",
    "archive-fusion-v2",
    "archive-primary-v3",
    "archive-evidence-fusion-v4",
    "deep-stack",
    "heuristic-demo",
    "ensemble",
    "missing-model",
]
DecisionProcessingPath = Literal["roi_crop", "full_frame_rescue", "quality_blocked"]
CalibrationBand = Literal[
    "quality_blocked",
    "strong_positive",
    "borderline_positive",
    "strong_negative",
    "borderline_negative",
    "uncertain",
]


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
    confidence_breakdown: dict[str, float | bool | str] | None = Field(
        default=None,
        description="Decomposed confidence view covering capture quality, model stability, threshold stability, and guardrail effects.",
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


# ---------------------------------------------------------------------------
# Decision audit
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Triage
# ---------------------------------------------------------------------------

TriageBand = Literal["low_risk", "moderate_risk", "high_concern", "uncertain_retake_needed"]


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


# ---------------------------------------------------------------------------
# Guidance
# ---------------------------------------------------------------------------

GuidanceSource = Literal["mistral", "fallback"]


class GuidanceResult(BaseModel):
    """
    Personalised health guidance generated by Mistral AI or the rule-based
    fallback, grounded in the triage result and reported symptoms.
    """

    source: GuidanceSource = Field(
        default="fallback",
        description="Which guidance strategy produced this result.",
    )
    model_used: str | None = Field(
        default=None,
        description="LLM model identifier, if guidance was LLM-generated.",
    )
    provider_used: str | None = Field(
        default=None,
        description="Inference provider, if applicable.",
    )
    explanation: str = Field(
        description="Plain-language interpretation of the screening result."
    )
    urgency_guidance: str = Field(
        description="Recommended follow-up urgency and action."
    )
    food_advice: str = Field(
        description="Dietary suggestions relevant to the result."
    )
    next_steps: list[str] = Field(
        description="Ordered list of concrete next actions for the user.",
        min_length=1,
    )

    @model_validator(mode="after")
    def _llm_fields_present_when_mistral(self) -> "GuidanceResult":
        if self.source == "mistral" and (
            self.model_used is None or self.provider_used is None
        ):
            raise ValueError(
                "model_used and provider_used must be set when source='mistral'."
            )
        return self


# ---------------------------------------------------------------------------
# Handoff summary
# ---------------------------------------------------------------------------

class HandoffSummary(BaseModel):
    headline: str = Field(description="Short share-ready label for the screening result.")
    urgency_label: str = Field(description="Human-readable follow-up urgency label.")
    generated_at: str = Field(description="Local timestamp when the handoff summary was built.")
    key_points: list[str] = Field(
        description="Short structured statements suitable for clinician or caregiver handoff.",
        min_length=3,
    )
    next_steps: list[str] = Field(
        description="Top follow-up actions copied from the guidance layer.",
        min_length=1,
    )
    share_text: str = Field(description="Plain-text handoff summary that can be copied or exported.")


# ---------------------------------------------------------------------------
# Case intelligence
# ---------------------------------------------------------------------------

PriorityWindow = Literal[
    "retake_now",
    "within_24_48_hours",
    "within_1_2_weeks",
    "routine_monitoring",
]
DriverImpact = Literal["up", "down", "limit"]
DriverStrength = Literal["high", "medium", "watch"]


class InsightDriver(BaseModel):
    title: str = Field(description="Short factor name shown in the UI.")
    impact: DriverImpact = Field(description="Whether this factor pushes concern up, down, or limits confidence.")
    strength: DriverStrength = Field(description="Relative strength of this factor in the final story.")
    detail: str = Field(description="Short grounded explanation of how this factor affected the result.")


class TimelineStep(BaseModel):
    window: str = Field(description="Human-readable follow-up window.")
    action: str = Field(description="Concrete action tied to that window.")


class CaseInsightPack(BaseModel):
    priority_window: PriorityWindow = Field(
        description="Top-level timing bucket for the safest next action."
    )
    priority_label: str = Field(description="Short follow-up timing label for the UI.")
    why_this_result: str = Field(
        description="Plain-language explanation of why the system produced this band."
    )
    confidence_story: str = Field(
        description="Plain-language explanation of how reliable the result is and why."
    )
    risk_drivers: list[InsightDriver] = Field(
        description="Top grounded factors that drove the final result.",
        min_length=1,
    )
    capture_improvements: list[str] = Field(
        description="Targeted image improvements for the next scan.",
        min_length=1,
    )
    follow_up_timeline: list[TimelineStep] = Field(
        description="Structured timeline of what to do next.",
        min_length=1,
    )
    judge_summary: str = Field(
        description="Short demo-ready summary of what the multilayer system proved on this run."
    )


# ---------------------------------------------------------------------------
# Clinical brief + response provenance
# ---------------------------------------------------------------------------

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


class AnalysisMeta(BaseModel):
    request_id: str = Field(description="Short request identifier copied from the API response headers.")
    generated_at: str = Field(description="Local timestamp when the response payload was assembled.")
    api_version: str = Field(description="Backend API version that produced this result.")
    processing_time_ms: Annotated[float, Field(ge=0.0)] = Field(
        description="End-to-end backend processing time in milliseconds."
    )
    quality_gate_passed: bool = Field(description="Whether the image quality gate allowed model inference.")
    processing_path: DecisionProcessingPath = Field(
        description="Which inference path reached the final result."
    )
    guidance_source: GuidanceSource = Field(
        description="Whether guidance came from Mistral or the rule-based fallback."
    )
    used_raw_frame_rescue: bool = Field(
        description="True when the backend rescued a framing-limited case using the full-frame path."
    )
    safety_layers: list[str] = Field(
        description="Safety layers applied during this run in execution order.",
        min_length=1,
    )


# ---------------------------------------------------------------------------
# Runtime status
# ---------------------------------------------------------------------------

class GuidanceRuntimeStatus(BaseModel):
    active_strategy: GuidanceSource
    mistral_enabled: bool = False
    client_ready: bool = False
    api_key_configured: bool = False
    mistral_model: str | None = None
    provider: str | None = None
    fallback_reason: str | None = None
    last_provider_error: str | None = None


class ModelRuntimeStatus(BaseModel):
    primary_model: str
    deep_stack_loaded: bool
    legacy_loaded: bool
    artifact_ready: bool = False
    artifact_path: str | None = None
    load_error: str | None = None
    record_count: int | None = None
    validation_accuracy: float | None = None
    validation_f1: float | None = None
    split_strategy: str | None = None
    deployed_scope: str | None = None
    deployed_validation_size: int | None = None
    deployed_accuracy: float | None = None
    deployed_precision: float | None = None
    deployed_recall: float | None = None
    deployed_f1: float | None = None
    deployed_blocked_total: int | None = None
    deployed_likely_count: int | None = None
    deployed_uncertain_count: int | None = None


class RuntimeStatusResponse(BaseModel):
    api_status: Literal["ok"] = "ok"
    guidance: GuidanceRuntimeStatus
    model: ModelRuntimeStatus


# ---------------------------------------------------------------------------
# HTTP response envelopes
# ---------------------------------------------------------------------------

class QualityCheckResponse(BaseModel):
    quality: QualityAssessment


class AnalyzeResponse(BaseModel):
    """
    Full analysis response returned by POST /api/analyze.

    blocked=True means image quality failed and no ML prediction was
    attempted.  In that case prediction will be None.
    """

    blocked: bool = Field(
        description="True if image quality failed and analysis was skipped."
    )
    quality: QualityAssessment
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
    symptoms: SymptomInput
    language: str | None = Field(default=None, description="BCP-47 language tag or plain name.")
    region: str | None = Field(default=None, description="Geographic region for localised guidance.")
