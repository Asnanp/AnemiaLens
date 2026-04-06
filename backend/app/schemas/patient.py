"""
Patient-related request schemas: symptom input and patient profile.
"""

from __future__ import annotations

from functools import cached_property
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import (
    DietType,
    SexType,
    _coerce_boolean,
)


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


class PatientProfileInput(BaseModel):
    """
    Lightweight intake details that make the screening flow feel closer to a
    real healthcare workflow without pretending to be a full medical record.
    """

    model_config = ConfigDict(extra="forbid")

    age: int | None = Field(
        default=None,
        ge=1,
        le=120,
        description="Approximate patient age in years, if provided.",
    )
    sex: SexType = Field(
        default="not_specified",
        description="Self-reported sex used only for screening context.",
    )
    diet_type: DietType = Field(
        default="not_specified",
        description="Self-reported diet pattern relevant to iron intake context.",
    )

    @field_validator("age", mode="before")
    @classmethod
    def _normalise_age(cls, value: object) -> int | None:
        if value is None:
            return None
        if isinstance(value, str):
            normalised = value.strip()
            if not normalised:
                return None
            return int(normalised)
        if isinstance(value, (int, float)):
            return int(value)
        raise ValueError("age must be an integer or null")

    @field_validator("sex", "diet_type", mode="before")
    @classmethod
    def _normalise_intake_enum(cls, value: object) -> str:
        if value is None:
            return "not_specified"
        if isinstance(value, str):
            normalised = value.strip().lower()
            return normalised or "not_specified"
        raise ValueError("Expected a string value")
