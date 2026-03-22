"""
Tests for request_parsing — the input-sanitisation layer that sits between
raw HTTP form data and the typed service layer.

Coverage targets:
- Boolean normalisation for every accepted truthy/falsy/null string.
- Extra-field rejection (prevents schema drift being silently ignored).
- Text normalisation: whitespace collapse, length enforcement.
- JSON edge cases: null payload, empty object, malformed JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas import PatientProfileInput, SymptomInput
from app.services.request_parsing import (
    InvalidRequestPayload,
    normalize_optional_text,
    parse_patient_profile,
    parse_symptoms,
)


# ---------------------------------------------------------------------------
# Boolean normalisation — parametrised for full coverage
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("truthy", ["yes", "Yes", "YES", "true", "True", "1", "on", "y"])
def test_parse_symptoms_accepts_truthy_strings(truthy: str) -> None:
    payload = json.dumps({"fatigue": truthy})
    result = parse_symptoms(payload)
    assert result.fatigue is True


@pytest.mark.parametrize("falsy", ["no", "No", "false", "False", "0", "off", "n", ""])
def test_parse_symptoms_accepts_falsy_strings(falsy: str) -> None:
    payload = json.dumps({"dizziness": falsy})
    result = parse_symptoms(payload)
    assert result.dizziness is False


@pytest.mark.parametrize("null_like", ["skip", "unknown", "n/a", "na", "none", "null"])
def test_parse_symptoms_accepts_null_strings_for_optional_field(null_like: str) -> None:
    payload = json.dumps({"heavy_menstrual_bleeding": null_like})
    result = parse_symptoms(payload)
    assert result.heavy_menstrual_bleeding is None


def test_parse_symptoms_normalises_mixed_types() -> None:
    """Realistic mixed-type payload from a browser form submission."""
    payload = json.dumps({
        "fatigue": "yes",
        "dizziness": "0",
        "pale_skin": True,
        "shortness_of_breath": "false",
        "heavy_menstrual_bleeding": "skip",
        "poor_diet_low_iron": "1",
    })

    result = parse_symptoms(payload)

    assert result == SymptomInput(
        fatigue=True,
        dizziness=False,
        pale_skin=True,
        shortness_of_breath=False,
        heavy_menstrual_bleeding=None,
        poor_diet_low_iron=True,
    )


def test_parse_symptoms_null_payload_returns_defaults() -> None:
    """A missing symptoms form field should yield all-False defaults."""
    result = parse_symptoms(None)
    assert result == SymptomInput()
    assert result.active_count == 0


def test_parse_symptoms_empty_object_returns_defaults() -> None:
    result = parse_symptoms("{}")
    assert result == SymptomInput()


def test_parse_patient_profile_defaults_when_missing() -> None:
    assert parse_patient_profile(None) == PatientProfileInput()


def test_parse_patient_profile_accepts_string_age_and_normalises_enums() -> None:
    result = parse_patient_profile(
        json.dumps({"age": "17", "sex": " Female ", "diet_type": " Vegetarian "})
    )
    assert result == PatientProfileInput(age=17, sex="female", diet_type="vegetarian")


def test_parse_patient_profile_rejects_non_object_json() -> None:
    with pytest.raises(InvalidRequestPayload):
        parse_patient_profile('["not", "an", "object"]')


# ---------------------------------------------------------------------------
# Schema enforcement
# ---------------------------------------------------------------------------

def test_parse_symptoms_rejects_unknown_fields() -> None:
    with pytest.raises(InvalidRequestPayload, match="unlisted_symptom"):
        parse_symptoms('{"fatigue": true, "unlisted_symptom": true}')


def test_parse_symptoms_rejects_multiple_unknown_fields() -> None:
    with pytest.raises(InvalidRequestPayload):
        parse_symptoms('{"fever": true, "nausea": true}')


# ---------------------------------------------------------------------------
# Malformed input
# ---------------------------------------------------------------------------

def test_parse_symptoms_rejects_malformed_json() -> None:
    with pytest.raises(InvalidRequestPayload, match="[Ii]nvalid"):
        parse_symptoms("{fatigue: true}")  # unquoted key — not valid JSON


def test_parse_symptoms_rejects_non_object_json() -> None:
    """Top-level arrays and scalars should be rejected."""
    with pytest.raises(InvalidRequestPayload):
        parse_symptoms('["fatigue", true]')


def test_parse_symptoms_rejects_invalid_boolean_value() -> None:
    with pytest.raises(InvalidRequestPayload):
        parse_symptoms('{"fatigue": "maybe"}')


# ---------------------------------------------------------------------------
# Computed properties
# ---------------------------------------------------------------------------

def test_symptom_input_active_count() -> None:
    s = SymptomInput(fatigue=True, dizziness=True, poor_diet_low_iron=True)
    assert s.active_count == 3


def test_symptom_input_burden_none() -> None:
    assert SymptomInput().symptom_burden == "none"


def test_symptom_input_burden_mild() -> None:
    assert SymptomInput(fatigue=True).symptom_burden == "mild"


def test_symptom_input_burden_moderate() -> None:
    s = SymptomInput(fatigue=True, dizziness=True, pale_skin=True)
    assert s.symptom_burden == "moderate"


def test_symptom_input_burden_severe() -> None:
    s = SymptomInput(
        fatigue=True, dizziness=True, pale_skin=True,
        shortness_of_breath=True, poor_diet_low_iron=True,
    )
    assert s.symptom_burden == "severe"


# ---------------------------------------------------------------------------
# normalize_optional_text
# ---------------------------------------------------------------------------

def test_normalize_optional_text_collapses_internal_whitespace() -> None:
    assert normalize_optional_text("  South   India  ", field_name="region") == "South India"


def test_normalize_optional_text_returns_none_for_blank() -> None:
    assert normalize_optional_text("   ", field_name="region") is None


def test_normalize_optional_text_returns_none_for_none() -> None:
    assert normalize_optional_text(None, field_name="language") is None


def test_normalize_optional_text_rejects_overly_long_values() -> None:
    with pytest.raises(InvalidRequestPayload, match="language"):
        normalize_optional_text("x" * 49, field_name="language")


def test_normalize_optional_text_accepts_max_length_value() -> None:
    # exactly 48 chars — should pass with the default limit
    value = "a" * 48
    result = normalize_optional_text(value, field_name="language")
    assert result == value


def test_normalize_optional_text_strips_unicode_whitespace() -> None:
    # Non-breaking space should be treated like regular whitespace
    result = normalize_optional_text("Kerala\u00a0India", field_name="region")
    assert "\u00a0" not in result
