"""
Analysis metadata schema for API response tracking.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.common import (
    DecisionProcessingPath,
    GuidanceSource,
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
