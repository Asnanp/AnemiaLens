"""
Case insight pack schemas: drivers, timeline, and insight summary.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import DriverImpact, DriverStrength, PriorityWindow


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
