"""
Shared utilities and type aliases used across all schema modules.
"""

from __future__ import annotations

from typing import Literal

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
# Shared type aliases
# ---------------------------------------------------------------------------

SexType = Literal["female", "male", "other", "not_specified"]
DietType = Literal["omnivore", "vegetarian", "vegan", "mixed", "not_specified"]

IssueCode = Literal[
    "blur_detected",
    "eye_not_visible",
    "inner_eye_not_detected",
    "poor_lighting",
    "resolution_too_low",
    "overexposed",
    "low_contrast",
    "framing_off",
    "bad_framing",
    "roi_cropped",
]

ReliabilityFlag = Literal["low", "medium", "high"]
ScreeningLabel = Literal["anemia_likely", "anemia_unlikely", "uncertain"]
ModelSource = Literal[
    "efficientnet-b0-ft",
    "archive-fusion-v2",
    "archive-primary-v3",
    "archive-fusion-v7-ultimate-clinical",
    "archive-fusion-v8-clinical-robust",
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

TriageBand = Literal["low_risk", "moderate_risk", "high_concern", "uncertain_retake_needed"]

GuidanceSource = Literal["mistral", "fallback"]

PriorityWindow = Literal[
    "retake_now",
    "within_24_48_hours",
    "within_1_2_weeks",
    "routine_monitoring",
]
DriverImpact = Literal["up", "down", "limit"]
DriverStrength = Literal["high", "medium", "watch"]

WorkflowStageKey = Literal[
    "image_quality_agent",
    "screening_agent",
    "triage_agent",
    "guidance_agent",
]
WorkflowStageStatus = Literal["passed", "warning", "blocked", "complete"]
