"""
Reusable Pydantic schemas for the AnemiaLens API.

This package reorganizes the original monolithic schemas.py into
domain-specific modules while preserving full backward compatibility.

All symbols from the original `app.schemas` module remain importable
via the flat re-export in this package's `__init__.py`.

Module layout:
- common          : Boolean coercion helpers, shared type aliases
- patient         : SymptomInput, PatientProfileInput
- quality         : QualityIssue, QualityAssessment, IssueCode
- prediction      : PredictionResult, reliability/screening/model types
- decision        : DecisionAudit, decision/threshold types
- triage          : TriageResult, TriageBand
- guidance        : GuidanceResult, GuidanceSource
- handoff         : HandoffSummary
- insight         : CaseInsightPack, InsightDriver, TimelineStep
- clinical        : ClinicalBrief, SignalBreakdown
- workflow        : WorkflowStage, PatientProfile, workflow types
- structured_case : StructuredCaseRecord, image quality, screening result
- meta            : AnalysisMeta
- status          : GuidanceRuntimeStatus, ModelRuntimeStatus, RuntimeStatusResponse
- response        : AnalyzeResponse, QualityCheckResponse, GuidanceChat*, RoiBox, RoiPreview
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Re-export every public symbol from the sub-modules so that existing
# imports like `from app.schemas import AnalyzeResponse` continue to work.
# ---------------------------------------------------------------------------

from app.schemas.common import (
    _coerce_boolean,
    _TRUE_VALUES,
    _FALSE_VALUES,
    _NONE_VALUES,
    SexType,
    DietType,
    IssueCode,
    ReliabilityFlag,
    ScreeningLabel,
    ModelSource,
    DecisionProcessingPath,
    CalibrationBand,
    TriageBand,
    GuidanceSource,
    PriorityWindow,
    DriverImpact,
    DriverStrength,
    WorkflowStageKey,
    WorkflowStageStatus,
)

from app.schemas.patient import (
    SymptomInput,
    PatientProfileInput,
)

from app.schemas.quality import (
    QualityIssue,
    QualityAssessment,
)

from app.schemas.prediction import (
    PredictionResult,
)

from app.schemas.decision import (
    DecisionAudit,
)

from app.schemas.triage import (
    TriageResult,
)

from app.schemas.guidance import (
    GuidanceResult,
)

from app.schemas.handoff import (
    HandoffSummary,
)

from app.schemas.insight import (
    InsightDriver,
    TimelineStep,
    CaseInsightPack,
)

from app.schemas.clinical import (
    SignalBreakdown,
    ClinicalBrief,
)

from app.schemas.workflow import (
    PatientProfile,
    WorkflowStage,
)

from app.schemas.structured_case import (
    StructuredCaseImageQuality,
    StructuredCaseScreeningResult,
    StructuredCaseRecord,
)

from app.schemas.meta import (
    AnalysisMeta,
)

from app.schemas.status import (
    GuidanceRuntimeStatus,
    ModelRuntimeStatus,
    RuntimeStatusResponse,
)

from app.schemas.response import (
    RoiBox,
    RoiPreview,
    QualityCheckResponse,
    AnalyzeResponse,
    GuidanceChatMessage,
    GuidanceChatRequest,
    GuidanceChatResponse,
)

__all__ = [
    # Common type aliases
    "SexType",
    "DietType",
    "IssueCode",
    "ReliabilityFlag",
    "ScreeningLabel",
    "ModelSource",
    "DecisionProcessingPath",
    "CalibrationBand",
    "TriageBand",
    "GuidanceSource",
    "PriorityWindow",
    "DriverImpact",
    "DriverStrength",
    "WorkflowStageKey",
    "WorkflowStageStatus",
    # Helpers
    "_coerce_boolean",
    "_TRUE_VALUES",
    "_FALSE_VALUES",
    "_NONE_VALUES",
    # Request schemas
    "SymptomInput",
    "PatientProfileInput",
    # Quality
    "QualityIssue",
    "QualityAssessment",
    # Prediction
    "PredictionResult",
    # Decision
    "DecisionAudit",
    # Triage
    "TriageResult",
    # Guidance
    "GuidanceResult",
    # Handoff
    "HandoffSummary",
    # Insight
    "InsightDriver",
    "TimelineStep",
    "CaseInsightPack",
    # Clinical
    "SignalBreakdown",
    "ClinicalBrief",
    # Workflow
    "PatientProfile",
    "WorkflowStage",
    # Structured case
    "StructuredCaseImageQuality",
    "StructuredCaseScreeningResult",
    "StructuredCaseRecord",
    # Meta
    "AnalysisMeta",
    # Status
    "GuidanceRuntimeStatus",
    "ModelRuntimeStatus",
    "RuntimeStatusResponse",
    # Response envelopes
    "RoiBox",
    "RoiPreview",
    "QualityCheckResponse",
    "AnalyzeResponse",
    "GuidanceChatMessage",
    "GuidanceChatRequest",
    "GuidanceChatResponse",
]
