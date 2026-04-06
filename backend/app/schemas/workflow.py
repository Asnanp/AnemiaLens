"""
Workflow stage and patient profile schemas for case tracking.
"""

from __future__ import annotations


from pydantic import BaseModel, Field

from app.schemas.common import (
    DietType,
    SexType,
    WorkflowStageKey,
    WorkflowStageStatus,
)


class PatientProfile(BaseModel):
    patient_id: str = Field(description="Share-safe case identifier generated for this screening run.")
    age: int | None = Field(default=None, description="Approximate patient age in years, if provided.")
    sex: SexType = Field(description="Self-reported sex captured during intake.")
    diet_type: DietType = Field(description="Self-reported diet pattern captured during intake.")
    reported_symptoms: list[str] = Field(
        default_factory=list,
        description="Human-readable symptom labels captured during intake.",
    )
    summary: str = Field(description="Short patient-context summary for the workflow UI.")


class WorkflowStage(BaseModel):
    key: WorkflowStageKey = Field(description="Stable workflow-stage identifier.")
    agent_label: str = Field(description="User-facing module name, presented as an agent-like stage.")
    title: str = Field(description="Short workflow stage title.")
    status: WorkflowStageStatus = Field(description="Outcome of this stage for the current run.")
    summary: str = Field(description="One-sentence explanation of what happened at this stage.")
