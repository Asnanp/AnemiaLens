"""
Handoff summary schema.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


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
