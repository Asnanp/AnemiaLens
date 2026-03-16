"""
Tests for GuidanceService, covering both Qwen-backed guidance and the
rule-based fallback.
"""

from __future__ import annotations

from collections import OrderedDict
import sys
import unittest
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import Settings
from app.schemas import (
    GuidanceResult,
    GuidanceRuntimeStatus,
    ModelRuntimeStatus,
    PredictionResult,
    SymptomInput,
    TriageResult,
)
from app.services.guidance import GuidanceService
from app.services.runtime_status import build_runtime_status


class _PredictorStub:
    def runtime_status(self) -> ModelRuntimeStatus:
        return ModelRuntimeStatus(
            primary_model="efficientnet-b0-ft",
            deep_stack_loaded=False,
            legacy_loaded=False,
        )


class _GuidanceStub:
    def runtime_status(self) -> GuidanceRuntimeStatus:
        return GuidanceRuntimeStatus(
            active_strategy="qwen",
            qwen_enabled=True,
            client_ready=True,
            api_key_configured=True,
            qwen_model="Qwen/Qwen2.5-7B-Instruct",
            provider="hf-inference",
        )


def _triage(band: str = "moderate_risk", score: float = 0.48) -> TriageResult:
    return TriageResult(
        band=band,
        score=score,
        label=band.replace("_", " ").title(),
        summary="Routine follow-up would be reasonable.",
        disclaimer="Screening only.",
    )


SERVICE = GuidanceService()


class TestParseGuidanceResponse:
    BASE_KWARGS = dict(
        source="qwen",
        model_used="Qwen/Qwen2.5-7B-Instruct",
        provider_used="hf-inference",
    )

    def test_accepts_code_fenced_json(self) -> None:
        raw = """```json
        {
          "explanation": "A grounded summary.",
          "urgency_guidance": "Book a routine follow-up.",
          "food_advice": "Add iron-rich foods.",
          "next_steps": ["Retake if symptoms change", "Plan a CBC test"]
        }
        ```"""
        result = SERVICE._parse_guidance_response(raw, **self.BASE_KWARGS)

        assert result.source == "qwen"
        assert result.model_used == "Qwen/Qwen2.5-7B-Instruct"
        assert result.provider_used == "hf-inference"
        assert len(result.next_steps) == 2
        assert result.next_steps[0] == "Retake if symptoms change"

    def test_accepts_plain_json(self) -> None:
        raw = """{
          "explanation": "Looks fine.",
          "urgency_guidance": "No urgency.",
          "food_advice": "Eat spinach.",
          "next_steps": ["Follow up in 3 months"]
        }"""
        result = SERVICE._parse_guidance_response(raw, **self.BASE_KWARGS)
        assert result.next_steps == ["Follow up in 3 months"]

    def test_accepts_python_literal_with_single_quotes(self) -> None:
        raw = (
            "{'explanation': 'Summary', 'urgency_guidance': 'Monitor closely', "
            "'food_advice': 'Eat lentils', 'next_steps': 'Book a clinic visit'}"
        )
        result = SERVICE._parse_guidance_response(raw, **self.BASE_KWARGS)
        assert result.next_steps == ["Book a clinic visit"]

    def test_coerces_string_next_steps_to_list(self) -> None:
        raw = """{
          "explanation": "Mild signal.",
          "urgency_guidance": "Monitor symptoms.",
          "food_advice": "Iron-rich diet.",
          "next_steps": "See a doctor soon"
        }"""
        result = SERVICE._parse_guidance_response(raw, **self.BASE_KWARGS)
        assert isinstance(result.next_steps, list)
        assert len(result.next_steps) == 1

    def test_allows_explicit_non_diagnostic_disclaimer(self) -> None:
        raw = """{
          "explanation": "This is screening guidance, not a diagnosis. The current result suggests some concern.",
          "urgency_guidance": "Follow up with a clinician if symptoms continue.",
          "food_advice": "Add iron-rich foods like lentils and spinach.",
          "next_steps": ["Book a routine clinic visit", "Monitor symptoms and retake if they change"]
        }"""
        result = SERVICE._parse_guidance_response(raw, **self.BASE_KWARGS)
        assert result.source == "qwen"
        assert "not a diagnosis" in result.explanation.lower()


UNSAFE_CLAIMS = [
    "This definitely confirms anemia.",
    "You have anemia based on this scan.",
    "The result diagnoses iron deficiency.",
    "This scan proves you are anaemic.",
]


@pytest.mark.parametrize("unsafe_explanation", UNSAFE_CLAIMS)
def test_parse_guidance_rejects_unsafe_claims(unsafe_explanation: str) -> None:
    raw = f"""{{
      "explanation": "{unsafe_explanation}",
      "urgency_guidance": "See a clinician.",
      "food_advice": "Eat iron-rich foods.",
      "next_steps": ["Book a CBC test"]
    }}"""
    with pytest.raises(ValueError, match="[Uu]nsafe|diagnostic|claim"):
        SERVICE._parse_guidance_response(
            raw,
            source="qwen",
            model_used="Qwen/Qwen2.5-7B-Instruct",
            provider_used="hf-inference",
        )


class TestFallbackGuidance:
    @pytest.mark.parametrize("band", ["low_risk", "moderate_risk", "high_concern", "uncertain_retake_needed"])
    def test_fallback_has_next_steps_for_every_band(self, band: str) -> None:
        result = SERVICE._fallback_guidance(
            triage=_triage(band=band),
            symptoms=SymptomInput(fatigue=True),
            prediction=None,
        )
        assert len(result.next_steps) >= 1

    def test_fallback_marks_source_correctly(self) -> None:
        result = SERVICE._fallback_guidance(
            triage=_triage(),
            symptoms=SymptomInput(fatigue=True, poor_diet_low_iron=True),
            prediction=None,
        )
        assert result.source == "fallback"
        assert result.model_used is None
        assert result.provider_used is None

    def test_fallback_result_validates_as_guidance_result(self) -> None:
        result = SERVICE._fallback_guidance(
            triage=_triage(band="high_concern", score=0.80),
            symptoms=SymptomInput(fatigue=True, dizziness=True),
            prediction=None,
        )
        GuidanceResult.model_validate(result.model_dump())

    def test_fallback_explanation_not_empty(self) -> None:
        result = SERVICE._fallback_guidance(
            triage=_triage(),
            symptoms=SymptomInput(),
            prediction=None,
        )
        assert len(result.explanation) > 20

    def test_fallback_language_is_non_diagnostic(self) -> None:
        result = SERVICE.generate_smart_fallback(
            "moderate_risk",
            10.2,
            0.74,
            SymptomInput(fatigue=True),
            "India",
        )
        combined = " ".join([result.explanation, result.urgency_guidance, result.food_advice, *result.next_steps]).lower()
        assert "diagnos" not in combined
        assert "you have anemia" not in combined

    def test_runtime_status_reports_fallback_reason_without_api_key(self) -> None:
        service = GuidanceService.__new__(GuidanceService)
        service.qwen_enabled = True
        service.qwen_model = "Qwen/Qwen2.5-7B-Instruct"
        service.hf_provider = "hf-inference"
        service.guidance_timeout = 6.0
        service.guidance_max_tokens = 256
        service.api_key_configured = False
        service.provider_name = "hf-inference"
        service._client = None
        service._fallback_reason = "Hugging Face API key is missing, so rule-based guidance is active."
        service._last_provider_error = None
        service._response_cache = OrderedDict()
        service._response_cache_size = 64

        status = service.runtime_status()

        assert status.active_strategy == "fallback"
        assert status.qwen_enabled is True
        assert status.client_ready is False
        assert status.api_key_configured is False
        assert "missing" in (status.fallback_reason or "").lower()

    def test_generate_skips_llm_for_uncertain_retake_cases(self) -> None:
        service = GuidanceService.__new__(GuidanceService)
        service.qwen_enabled = True
        service.qwen_model = "Qwen/Qwen2.5-7B-Instruct"
        service.hf_provider = "hf-inference"
        service.guidance_timeout = 6.0
        service.guidance_max_tokens = 256
        service.api_key_configured = True
        service.provider_name = "hf-inference"
        service._client = object()
        service._fallback_reason = None
        service._last_provider_error = None
        service._response_cache = OrderedDict()
        service._response_cache_size = 64
        service._call_qwen_api = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Qwen should be skipped"))  # type: ignore[method-assign]

        result = service.generate(
            triage=_triage(band="uncertain_retake_needed"),
            symptoms=SymptomInput(fatigue=True),
            prediction=None,
        )

        assert result.source == "fallback"
        assert "not a clear result" in result.explanation.lower()

    def test_generate_smart_fallback_personalizes_region_and_symptoms(self) -> None:
        result = SERVICE.generate_smart_fallback(
            "moderate_risk",
            10.1,
            0.72,
            SymptomInput(
                fatigue=True,
                shortness_of_breath=True,
                heavy_menstrual_bleeding=True,
            ),
            "India",
        )

        assert result.source == "fallback"
        assert "palak" in result.food_advice.lower()
        assert "tea or coffee" in result.food_advice.lower()
        assert "Avoid strenuous activity until reviewed by a doctor." in result.next_steps
        assert "Discuss menstrual blood loss with your doctor as a likely contributing factor." in result.next_steps

    def test_generate_qwen_returns_smart_fallback_when_provider_fails(self) -> None:
        service = GuidanceService.__new__(GuidanceService)
        service.qwen_enabled = True
        service.qwen_model = "Qwen/Qwen2.5-7B-Instruct"
        service.hf_provider = "hf-inference"
        service.guidance_timeout = 6.0
        service.guidance_max_tokens = 256
        service.api_key_configured = True
        service.provider_name = "hf-inference"
        service._client = object()
        service._fallback_reason = None
        service._last_provider_error = None
        service._response_cache = OrderedDict()
        service._response_cache_size = 64
        service._call_qwen_api = lambda *args, **kwargs: (_ for _ in ()).throw(  # type: ignore[method-assign]
            RuntimeError("403 Forbidden: This authentication method does not have sufficient permissions to call Inference Providers")
        )

        result = service.generate(
            triage=_triage(band="high_concern", score=0.82),
            symptoms=SymptomInput(fatigue=True, shortness_of_breath=True),
            prediction=PredictionResult(
                anemia_risk=0.87,
                predicted_hemoglobin=7.6,
                confidence=0.84,
                uncertainty=0.16,
                reliability_flag="high",
                screening_label="anemia_likely",
                screening_text="The screening model estimates a lower-than-expected hemoglobin trend from the eye image.",
                model_source="efficientnet-b0-ft",
            ),
            region="India",
        )

        assert result.source == "fallback"
        assert "24 to 48 hours" in result.urgency_guidance
        assert "inference providers" in (service._last_provider_error or "").lower()


def test_guidance_result_requires_model_and_provider_when_qwen() -> None:
    with pytest.raises(Exception):
        GuidanceResult(
            source="qwen",
            explanation="Looks fine.",
            urgency_guidance="No urgency.",
            food_advice="Eat well.",
            next_steps=["Follow up"],
        )


def test_guidance_result_allows_null_model_for_fallback() -> None:
    result = GuidanceResult(
        source="fallback",
        model_used=None,
        provider_used=None,
        explanation="Looks fine.",
        urgency_guidance="No urgency.",
        food_advice="Eat well.",
        next_steps=["Follow up"],
    )
    assert result.source == "fallback"


class TestRuntimeStatus(unittest.TestCase):
    def test_enriches_model_metadata_from_training_report(self) -> None:
        status = build_runtime_status(_PredictorStub(), _GuidanceStub())

        self.assertEqual(status.api_status, "ok")
        self.assertEqual(status.guidance.active_strategy, "qwen")
        self.assertIn(
            status.model.primary_model,
            {"archive-fusion-v2", "efficientnet-b0-ft", "archive-primary-v3", "archive-evidence-fusion-v4"},
        )
        self.assertGreaterEqual(status.model.record_count or 0, 200)
        self.assertGreater(status.model.validation_f1 or 0.0, 0.6)

    def test_guidance_qwen_fields_propagated(self) -> None:
        status = build_runtime_status(_PredictorStub(), _GuidanceStub())
        self.assertEqual(status.guidance.qwen_model, "Qwen/Qwen2.5-7B-Instruct")
        self.assertEqual(status.guidance.provider, "hf-inference")
        self.assertTrue(status.guidance.qwen_enabled)
        self.assertTrue(status.guidance.client_ready)


def test_settings_accept_hf_environment_variable_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANEMIALENS_HF_API_KEY", "test-token")
    monkeypatch.setenv("ANEMIALENS_QWEN_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    monkeypatch.setenv("ANEMIALENS_QWEN_ENABLED", "true")
    monkeypatch.setenv("ANEMIALENS_HF_PROVIDER", "hf-inference")

    settings_obj = Settings(_env_file=None)

    assert settings_obj.hf_api_key == "test-token"
    assert settings_obj.qwen_model == "Qwen/Qwen2.5-7B-Instruct"
    assert settings_obj.qwen_enabled is True
    assert settings_obj.hf_provider == "hf-inference"


def test_generate_uses_cached_qwen_result_for_same_payload() -> None:
    service = GuidanceService.__new__(GuidanceService)
    service.qwen_enabled = True
    service.qwen_model = "Qwen/Qwen2.5-7B-Instruct"
    service.hf_provider = "hf-inference"
    service.guidance_timeout = 6.0
    service.guidance_max_tokens = 256
    service.api_key_configured = True
    service.provider_name = "hf-inference"
    service._client = object()
    service._fallback_reason = None
    service._last_provider_error = None
    service._response_cache = OrderedDict()
    service._response_cache_size = 64

    calls = {"count": 0}

    def _fake_generate_qwen(*args, **kwargs) -> GuidanceResult:
        calls["count"] += 1
        return GuidanceResult(
            source="qwen",
            model_used="Qwen/Qwen2.5-7B-Instruct",
            provider_used="hf-inference",
            explanation="Screening suggests a mild low-hemoglobin signal.",
            urgency_guidance="Arrange a routine check if symptoms continue.",
            food_advice="Eat lentils, beans, spinach, and vitamin C-rich fruit.",
            next_steps=["Repeat the scan if symptoms change", "Plan a clinic test"],
        )

    service._generate_qwen = _fake_generate_qwen  # type: ignore[method-assign]

    prediction = PredictionResult(
        anemia_risk=0.58,
        predicted_hemoglobin=10.9,
        confidence=0.78,
        uncertainty=0.18,
        reliability_flag="high",
        screening_label="anemia_likely",
        screening_text="The screening model estimates a lower-than-expected hemoglobin trend from the eye image.",
        model_source="efficientnet-b0-ft",
    )

    first = service.generate(_triage(), SymptomInput(fatigue=True), prediction, "English", "India")
    second = service.generate(_triage(), SymptomInput(fatigue=True), prediction, "English", "India")

    assert first.source == "qwen"
    assert second.source == "qwen"
    assert calls["count"] == 1


def test_summarize_provider_error_flags_hf_permission_problem() -> None:
    service = GuidanceService.__new__(GuidanceService)
    message = service._summarize_provider_error(
        RuntimeError("403 Forbidden: This authentication method does not have sufficient permissions to call Inference Providers")
    )
    assert "inference providers" in message.lower()


def test_qwen_generates_response() -> None:
    service = GuidanceService.__new__(GuidanceService)
    service.qwen_enabled = True
    service.qwen_model = "Qwen/Qwen2.5-7B-Instruct"
    service.hf_provider = "hf-inference"
    service.guidance_timeout = 6.0
    service.guidance_max_tokens = 256
    service.api_key_configured = True
    service.provider_name = "hf-inference"
    service._client = object()
    service._fallback_reason = None
    service._last_provider_error = None
    service._response_cache = OrderedDict()
    service._response_cache_size = 64

    def _fake_generate_qwen(*args, **kwargs) -> GuidanceResult:
        return GuidanceResult(
            source="qwen",
            model_used="Qwen/Qwen2.5-7B-Instruct",
            provider_used="hf-inference",
            explanation="Screening suggests a mild low-hemoglobin signal.",
            urgency_guidance="Arrange a routine check if symptoms continue.",
            food_advice="Eat lentils, beans, spinach, and vitamin C-rich fruit.",
            next_steps=["Repeat the scan if symptoms change", "Plan a clinic test"],
        )

    service._generate_qwen = _fake_generate_qwen  # type: ignore[method-assign]

    result = service.generate(
        triage=_triage(),
        symptoms=SymptomInput(fatigue=True),
        prediction=PredictionResult(
            anemia_risk=0.87,
            predicted_hemoglobin=7.6,
            confidence=0.84,
            uncertainty=0.16,
            reliability_flag="high",
            screening_label="anemia_likely",
            screening_text="The screening model estimates a lower-than-expected hemoglobin trend from the eye image.",
            model_source="efficientnet-b0-ft",
        ),
    )

    assert result.source == "qwen"
