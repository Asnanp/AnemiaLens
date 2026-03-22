from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.prediction import ScreeningPredictor
from app.services import prediction as prediction_module
from app.schemas import PredictionResult, QualityAssessment


def test_predictor_init_is_lazy(monkeypatch, tmp_path) -> None:
    archive_path = tmp_path / "archive.joblib"
    efficientnet_path = tmp_path / "efficientnet.pth"
    archive_path.write_bytes(b"archive")
    efficientnet_path.write_bytes(b"efficientnet")

    calls: list[str] = []

    monkeypatch.setattr(prediction_module, "DEFAULT_ARCHIVE_MODEL_PATH", archive_path)
    monkeypatch.setattr(
        prediction_module,
        "DEFAULT_EFFICIENTNET_MODEL_PATH",
        efficientnet_path,
    )
    monkeypatch.setattr(
        prediction_module,
        "_load_archive_model_artifact",
        lambda path: calls.append(f"archive:{path.name}") or {"artifact": True},
    )
    monkeypatch.setattr(
        prediction_module,
        "_load_efficientnet_checkpoint_bundle",
        lambda path: calls.append(f"efficientnet:{path.name}") or {"bundle": True},
    )

    predictor = ScreeningPredictor()

    assert calls == []
    assert predictor.archive_model is None
    assert predictor.efficientnet_bundle is None
    assert predictor.is_ready() is True


def test_predictor_preload_loads_models_once(monkeypatch, tmp_path) -> None:
    archive_path = tmp_path / "archive.joblib"
    efficientnet_path = tmp_path / "efficientnet.pth"
    archive_path.write_bytes(b"archive")
    efficientnet_path.write_bytes(b"efficientnet")

    calls: list[str] = []

    monkeypatch.setattr(prediction_module, "DEFAULT_ARCHIVE_MODEL_PATH", archive_path)
    monkeypatch.setattr(
        prediction_module,
        "DEFAULT_EFFICIENTNET_MODEL_PATH",
        efficientnet_path,
    )
    monkeypatch.setattr(
        prediction_module,
        "_load_archive_model_artifact",
        lambda path: calls.append(f"archive:{path.name}") or {"artifact": True},
    )
    monkeypatch.setattr(
        prediction_module,
        "_load_efficientnet_checkpoint_bundle",
        lambda path: calls.append(f"efficientnet:{path.name}") or {"bundle": True},
    )
    monkeypatch.setattr(prediction_module.settings, "enable_efficientnet_fallback", True)

    predictor = ScreeningPredictor()
    predictor.preload()
    predictor.preload()

    assert calls == ["archive:archive.joblib", "efficientnet:efficientnet.pth"]
    assert predictor.archive_model == {"artifact": True}
    assert predictor.efficientnet_bundle == {"bundle": True}


def test_dark_signal_guardrail_triggers_on_dark_positive_with_near_normal_hb() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)

    triggered = predictor._dark_signal_guardrail(
        risk=0.71,
        predicted_hemoglobin=11.9,
        feature_map={
            "brightness": 0.11,
            "hist_bright": 0.03,
            "hist_highlight": 0.0,
        },
        threshold=0.68,
    )

    assert triggered is True


def test_dark_signal_guardrail_skips_clear_low_hb_cases() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)

    triggered = predictor._dark_signal_guardrail(
        risk=0.74,
        predicted_hemoglobin=10.4,
        feature_map={
            "brightness": 0.11,
            "hist_bright": 0.03,
            "hist_highlight": 0.0,
        },
        threshold=0.68,
    )

    assert triggered is False


def test_screening_decision_returns_uncertain_when_guardrail_triggers() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)

    label, text = predictor._screening_decision(
        risk=0.72,
        uncertainty=0.19,
        threshold=0.68,
        predicted_hemoglobin=12.4,
        signal_guardrail_triggered=True,
    )

    assert label == "uncertain"
    assert "dark" in text.lower()


def test_screening_decision_rescues_high_suspicion_positive() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)

    label, text = predictor._screening_decision(
        risk=0.52,
        uncertainty=0.6,
        threshold=0.435,
        predicted_hemoglobin=12.1,
    )

    assert label == "anemia_likely"
    assert "likely anemia" in text.lower()


def test_screening_decision_rescues_borderline_high_suspicion_positive() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)

    label, text = predictor._screening_decision(
        risk=0.428,
        uncertainty=0.56,
        threshold=0.435,
        predicted_hemoglobin=12.35,
    )

    assert label == "anemia_likely"
    assert "likely anemia" in text.lower()


def test_screening_decision_downgrades_mild_positive_near_normal_hb() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)

    label, text = predictor._screening_decision(
        risk=0.56,
        uncertainty=0.54,
        threshold=0.435,
        predicted_hemoglobin=12.3,
    )

    assert label == "uncertain"
    assert "near normal" in text.lower()


def test_screening_decision_rescues_clarity_exception_borderline_positive() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)

    label, text = predictor._screening_decision(
        risk=0.392,
        uncertainty=0.62,
        threshold=0.435,
        predicted_hemoglobin=12.24,
    )

    assert label == "anemia_likely"
    assert "likely anemia" in text.lower()


def test_screening_decision_high_threshold_low_reliability_positive_requires_extra_evidence() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)

    label, text = predictor._screening_decision(
        risk=0.708,
        uncertainty=0.582,
        threshold=0.65,
        predicted_hemoglobin=11.62,
    )

    assert label == "uncertain"
    assert "confidence level" in text.lower()


def test_screening_decision_keeps_strong_low_reliability_positive_with_clear_margin() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)

    label, text = predictor._screening_decision(
        risk=0.761,
        uncertainty=0.617,
        threshold=0.65,
        predicted_hemoglobin=11.46,
    )

    assert label == "anemia_likely"
    assert "likely anemia" in text.lower()


def test_screening_decision_keeps_overwhelming_positive_signal_likely_even_when_noisy() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)

    label, text = predictor._screening_decision(
        risk=0.768,
        uncertainty=0.804,
        threshold=0.495,
        predicted_hemoglobin=11.72,
    )

    assert label == "anemia_likely"
    assert "still be treated as likely" in text.lower()


def test_screening_decision_keeps_signal_only_positive_likely_when_hb_missing() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)

    label, text = predictor._screening_decision(
        risk=0.648,
        uncertainty=0.88,
        threshold=0.495,
        predicted_hemoglobin=None,
    )

    assert label == "anemia_likely"
    assert "image-only anemia signal" in text.lower()


def test_screening_decision_skips_below_threshold_rescue_for_strict_runtime_threshold() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)

    label, text = predictor._screening_decision(
        risk=0.646,
        uncertainty=0.602,
        threshold=0.65,
        predicted_hemoglobin=11.56,
    )

    assert label == "uncertain"
    assert "uncertain" in text.lower()


def test_screening_decision_keeps_high_uncertainty_borderline_case_uncertain() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)

    label, text = predictor._screening_decision(
        risk=0.45,
        uncertainty=0.61,
        threshold=0.435,
        predicted_hemoglobin=12.8,
    )

    assert label == "uncertain"
    assert "uncertain" in text.lower()


def test_should_accept_raw_frame_rescue_for_strong_positive() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    prediction = PredictionResult(
        anemia_risk=0.86,
        predicted_hemoglobin=10.9,
        confidence=0.61,
        uncertainty=0.39,
        reliability_flag="medium",
        screening_label="anemia_likely",
        screening_text="Likely anemia.",
        model_source="archive-evidence-fusion-v4",
    )

    assert predictor.should_accept_raw_frame_rescue(prediction) is True


def test_should_reject_raw_frame_rescue_for_weak_positive() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    prediction = PredictionResult(
        anemia_risk=0.62,
        predicted_hemoglobin=11.8,
        confidence=0.52,
        uncertainty=0.48,
        reliability_flag="medium",
        screening_label="anemia_likely",
        screening_text="Likely anemia.",
        model_source="archive-evidence-fusion-v4",
    )

    assert predictor.should_accept_raw_frame_rescue(prediction) is False


def test_should_accept_raw_frame_rescue_for_strong_negative() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    prediction = PredictionResult(
        anemia_risk=0.21,
        predicted_hemoglobin=13.7,
        confidence=0.64,
        uncertainty=0.36,
        reliability_flag="medium",
        screening_label="anemia_unlikely",
        screening_text="Unlikely anemia.",
        model_source="archive-evidence-fusion-v4",
    )

    assert predictor.should_accept_raw_frame_rescue(prediction) is True


def test_should_accept_raw_frame_rescue_for_hidden_hb_negative() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    prediction = PredictionResult(
        anemia_risk=0.27,
        predicted_hemoglobin=None,
        confidence=0.45,
        uncertainty=0.55,
        reliability_flag="low",
        screening_label="anemia_unlikely",
        screening_text="Unlikely anemia.",
        model_source="archive-evidence-fusion-v4",
    )

    assert predictor.should_accept_raw_frame_rescue(prediction) is True


def test_should_accept_raw_frame_rescue_for_low_risk_uncertain() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    prediction = PredictionResult(
        anemia_risk=0.31,
        predicted_hemoglobin=None,
        confidence=0.33,
        uncertainty=0.67,
        reliability_flag="low",
        screening_label="uncertain",
        screening_text="Uncertain.",
        model_source="archive-evidence-fusion-v4",
    )

    assert predictor.should_accept_raw_frame_rescue(prediction) is True


def test_should_reject_raw_frame_rescue_for_weak_negative() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    prediction = PredictionResult(
        anemia_risk=0.29,
        predicted_hemoglobin=13.4,
        confidence=0.47,
        uncertainty=0.53,
        reliability_flag="low",
        screening_label="anemia_unlikely",
        screening_text="Unlikely anemia.",
        model_source="archive-evidence-fusion-v4",
    )

    assert predictor.should_accept_raw_frame_rescue(prediction) is False


def test_should_reject_raw_frame_rescue_for_high_risk_uncertain() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    prediction = PredictionResult(
        anemia_risk=0.36,
        predicted_hemoglobin=None,
        confidence=0.31,
        uncertainty=0.67,
        reliability_flag="low",
        screening_label="uncertain",
        screening_text="Uncertain.",
        model_source="archive-evidence-fusion-v4",
    )

    assert predictor.should_accept_raw_frame_rescue(prediction) is False


def test_should_accept_raw_frame_rescue_for_strong_positive_without_hb() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    prediction = PredictionResult(
        anemia_risk=0.72,
        predicted_hemoglobin=None,
        confidence=0.24,
        uncertainty=0.78,
        reliability_flag="low",
        screening_label="anemia_likely",
        screening_text="Likely anemia.",
        model_source="archive-evidence-fusion-v4",
    )

    assert predictor.should_accept_raw_frame_rescue(prediction) is True


def test_predict_returns_confidence_breakdown(monkeypatch) -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    predictor.enable_efficientnet_fallback = False
    predictor.archive_model = None
    predictor.efficientnet_bundle = None
    predictor.load_error = None
    predictor.model_path = Path("archive.joblib")
    predictor.efficientnet_path = Path("efficientnet.pth")
    predictor._archive_model_load_attempted = False
    predictor._efficientnet_model_load_attempted = False
    predictor.runtime_risk_calibrator = None
    predictor._runtime_risk_calibrator_load_attempted = True
    predictor.runtime_screening_refiner = None
    predictor._runtime_screening_refiner_load_attempted = True

    monkeypatch.setattr(
        predictor,
        "_ensure_archive_model_loaded",
        lambda: {"artifact": True},
    )
    monkeypatch.setattr(
        prediction_module,
        "extract_eye_features",
        lambda image: {
            "brightness": 0.21,
            "hist_bright": 0.05,
            "hist_highlight": 0.01,
        },
    )
    monkeypatch.setattr(
        prediction_module,
        "_predict_archive_model",
        lambda artifact, feature_map, source_hint: {
            "anemia_risk": 0.58,
            "uncertainty": 0.22,
            "predicted_hemoglobin": 11.7,
        },
    )
    monkeypatch.setattr(
        prediction_module,
        "_build_runtime_stack",
        lambda archive_prediction, **kwargs: {
            "anemia_risk": 0.58,
            "uncertainty": 0.22,
            "predicted_hemoglobin": 11.7,
            "decision_threshold": 0.5,
        },
    )

    quality = QualityAssessment(
        passed=True,
        blur_score=148.0,
        brightness_score=0.24,
        contrast_score=0.16,
        framing_score=1.7,
        lighting_score=0.78,
        lighting_condition="balanced",
        lighting_summary="Lighting is even enough for a confident conjunctiva read.",
        glare_risk=0.08,
        shadow_risk=0.12,
        issues=[],
    )

    result = predictor.predict(Image.new("RGB", (80, 80), "white"), quality)

    assert result.confidence_breakdown is not None
    assert result.confidence_breakdown["capture_quality"] > 0.6
    assert result.confidence_breakdown["model_stability"] > 0.7
    assert result.confidence_breakdown["lighting_condition"] == "balanced"
    assert "capture quality" in str(result.confidence_breakdown["summary"]).lower() or "threshold" in str(result.confidence_breakdown["summary"]).lower() or "support" in str(result.confidence_breakdown["summary"]).lower()


def test_predict_boosts_confidence_for_clear_low_risk_case(monkeypatch) -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    predictor.enable_efficientnet_fallback = False
    predictor.archive_model = None
    predictor.efficientnet_bundle = None
    predictor.load_error = None
    predictor.model_path = Path("archive.joblib")
    predictor.efficientnet_path = Path("efficientnet.pth")
    predictor._archive_model_load_attempted = False
    predictor._efficientnet_model_load_attempted = False
    predictor.runtime_risk_calibrator = None
    predictor._runtime_risk_calibrator_load_attempted = True
    predictor.runtime_screening_refiner = None
    predictor._runtime_screening_refiner_load_attempted = True

    monkeypatch.setattr(
        predictor,
        "_ensure_archive_model_loaded",
        lambda: {"artifact": True},
    )
    monkeypatch.setattr(
        prediction_module,
        "extract_eye_features",
        lambda image: {
            "brightness": 0.24,
            "hist_bright": 0.09,
            "hist_highlight": 0.01,
        },
    )
    monkeypatch.setattr(
        prediction_module,
        "_predict_archive_model",
        lambda artifact, feature_map, source_hint: {
            "anemia_risk": 0.22,
            "uncertainty": 0.24,
            "predicted_hemoglobin": 13.7,
        },
    )
    monkeypatch.setattr(
        prediction_module,
        "_build_runtime_stack",
        lambda archive_prediction, **kwargs: {
            "anemia_risk": 0.22,
            "uncertainty": 0.24,
            "predicted_hemoglobin": 13.7,
            "decision_threshold": 0.5,
        },
    )

    quality = QualityAssessment(
        passed=True,
        blur_score=86.0,
        brightness_score=0.23,
        contrast_score=0.14,
        framing_score=1.12,
        lighting_score=0.46,
        lighting_condition="dim",
        lighting_summary="Lighting is slightly dim but still usable.",
        glare_risk=0.1,
        shadow_risk=0.18,
        issues=[],
    )

    result = predictor.predict(Image.new("RGB", (80, 80), "white"), quality)

    assert result.screening_label == "anemia_unlikely"
    assert result.confidence >= 0.55
    assert result.reliability_flag in {"medium", "high"}
    assert result.confidence_breakdown is not None
    assert "low-risk side" in str(result.confidence_breakdown["summary"]).lower()


def test_predict_keeps_low_risk_case_conservative_when_glare_is_high(monkeypatch) -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    predictor.enable_efficientnet_fallback = False
    predictor.archive_model = None
    predictor.efficientnet_bundle = None
    predictor.load_error = None
    predictor.model_path = Path("archive.joblib")
    predictor.efficientnet_path = Path("efficientnet.pth")
    predictor._archive_model_load_attempted = False
    predictor._efficientnet_model_load_attempted = False
    predictor.runtime_risk_calibrator = None
    predictor._runtime_risk_calibrator_load_attempted = True
    predictor.runtime_screening_refiner = None
    predictor._runtime_screening_refiner_load_attempted = True

    monkeypatch.setattr(
        predictor,
        "_ensure_archive_model_loaded",
        lambda: {"artifact": True},
    )
    monkeypatch.setattr(
        prediction_module,
        "extract_eye_features",
        lambda image: {
            "brightness": 0.24,
            "hist_bright": 0.09,
            "hist_highlight": 0.01,
        },
    )
    monkeypatch.setattr(
        prediction_module,
        "_predict_archive_model",
        lambda artifact, feature_map, source_hint: {
            "anemia_risk": 0.22,
            "uncertainty": 0.24,
            "predicted_hemoglobin": 13.7,
        },
    )
    monkeypatch.setattr(
        prediction_module,
        "_build_runtime_stack",
        lambda archive_prediction, **kwargs: {
            "anemia_risk": 0.22,
            "uncertainty": 0.24,
            "predicted_hemoglobin": 13.7,
            "decision_threshold": 0.5,
        },
    )

    quality = QualityAssessment(
        passed=True,
        blur_score=84.0,
        brightness_score=0.34,
        contrast_score=0.14,
        framing_score=1.12,
        lighting_score=0.44,
        lighting_condition="glare_heavy",
        lighting_summary="Highlights are clipping part of the eyelid surface.",
        glare_risk=0.72,
        shadow_risk=0.18,
        issues=[],
    )

    result = predictor.predict(Image.new("RGB", (80, 80), "white"), quality)

    assert result.screening_label == "anemia_unlikely"
    assert result.confidence < 0.55
    assert result.reliability_flag == "low"


def test_predict_keeps_strong_quality_limited_positive_above_flat_low_confidence(monkeypatch) -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    predictor.enable_efficientnet_fallback = False
    predictor.archive_model = None
    predictor.efficientnet_bundle = None
    predictor.load_error = None
    predictor.model_path = Path("archive.joblib")
    predictor.efficientnet_path = Path("efficientnet.pth")
    predictor._archive_model_load_attempted = False
    predictor._efficientnet_model_load_attempted = False
    predictor.runtime_risk_calibrator = None
    predictor._runtime_risk_calibrator_load_attempted = True
    predictor.runtime_screening_refiner = None
    predictor._runtime_screening_refiner_load_attempted = False

    class _FakeRefiner:
        method = "logistic-regression"

        def refine(
            self,
            *,
            base_anemia_risk: float,
            uncertainty: float,
            predicted_hemoglobin: float | None,
            quality: QualityAssessment,
            base_likely: bool,
        ) -> float:
            assert quality.lighting_condition == "shadow_heavy"
            return 0.956

    monkeypatch.setattr(
        predictor,
        "_ensure_runtime_screening_refiner_loaded",
        lambda: _FakeRefiner(),
    )
    monkeypatch.setattr(
        predictor,
        "_ensure_archive_model_loaded",
        lambda: {"artifact": True},
    )
    monkeypatch.setattr(
        prediction_module,
        "extract_eye_features",
        lambda image: {
            "brightness": 0.067,
            "hist_bright": 0.0,
            "hist_highlight": 0.0,
        },
    )
    monkeypatch.setattr(
        prediction_module,
        "_predict_archive_model",
        lambda artifact, feature_map, source_hint: {
            "anemia_risk": 0.496,
            "uncertainty": 0.782,
            "predicted_hemoglobin": 11.9,
        },
    )
    monkeypatch.setattr(
        prediction_module,
        "_build_runtime_stack",
        lambda archive_prediction, **kwargs: {
            "anemia_risk": 0.496,
            "uncertainty": 0.782,
            "predicted_hemoglobin": 11.9,
            "decision_threshold": 0.495,
        },
    )

    quality = QualityAssessment(
        passed=True,
        blur_score=195.0,
        brightness_score=0.067,
        contrast_score=0.16,
        framing_score=2.742,
        lighting_score=0.54,
        lighting_condition="shadow_heavy",
        lighting_summary="Shadows are covering part of the eyelid, so the model may miss the true pallor signal.",
        glare_risk=0.0,
        shadow_risk=1.0,
        issues=[],
    )

    result = predictor.predict(Image.new("RGB", (80, 80), "white"), quality)

    assert result.screening_label == "uncertain"
    assert result.confidence >= 0.5
    assert result.reliability_flag == "low"
    assert result.confidence_breakdown is not None
    assert float(result.confidence_breakdown["signal_strength"]) >= 0.9


def test_predict_applies_runtime_risk_calibrator(monkeypatch) -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    predictor.enable_efficientnet_fallback = False
    predictor.archive_model = None
    predictor.efficientnet_bundle = None
    predictor.load_error = None
    predictor.model_path = Path("archive.joblib")
    predictor.efficientnet_path = Path("efficientnet.pth")
    predictor._archive_model_load_attempted = False
    predictor._efficientnet_model_load_attempted = False
    predictor.runtime_risk_calibrator = None
    predictor._runtime_risk_calibrator_load_attempted = False
    predictor.runtime_screening_refiner = None
    predictor._runtime_screening_refiner_load_attempted = True

    class _FakeCalibrator:
        method = "temperature"

        def calibrate(self, probability: float, *, source_hint: str = "roi_original") -> float:
            assert source_hint == "roi_original"
            return probability + 0.14

    monkeypatch.setattr(
        predictor,
        "_ensure_runtime_risk_calibrator_loaded",
        lambda: _FakeCalibrator(),
    )
    monkeypatch.setattr(
        predictor,
        "_ensure_archive_model_loaded",
        lambda: {"artifact": True},
    )
    monkeypatch.setattr(
        prediction_module,
        "extract_eye_features",
        lambda image: {
            "brightness": 0.24,
            "hist_bright": 0.09,
            "hist_highlight": 0.01,
        },
    )
    monkeypatch.setattr(
        prediction_module,
        "_predict_archive_model",
        lambda artifact, feature_map, source_hint: {
            "anemia_risk": 0.48,
            "uncertainty": 0.18,
            "predicted_hemoglobin": 11.7,
        },
    )
    monkeypatch.setattr(
        prediction_module,
        "_build_runtime_stack",
        lambda archive_prediction, **kwargs: {
            "anemia_risk": 0.48,
            "uncertainty": 0.18,
            "predicted_hemoglobin": 11.7,
            "decision_threshold": 0.5,
        },
    )

    quality = QualityAssessment(
        passed=True,
        blur_score=170.0,
        brightness_score=0.23,
        contrast_score=0.16,
        framing_score=1.35,
        lighting_score=0.82,
        lighting_condition="balanced",
        lighting_summary="Lighting is balanced enough for reliable screening.",
        glare_risk=0.06,
        shadow_risk=0.08,
        issues=[],
    )

    result = predictor.predict(Image.new("RGB", (80, 80), "white"), quality)

    assert result.screening_label == "anemia_likely"
    assert round(result.anemia_risk, 2) == 0.48
    assert result.confidence_breakdown is not None
    assert result.confidence_breakdown["calibration_applied"] is True
    assert result.confidence_breakdown["calibration_method"] == "temperature"
    assert round(float(result.confidence_breakdown["raw_anemia_risk"]), 2) == 0.48
    assert round(float(result.confidence_breakdown["calibrated_anemia_risk"]), 2) == 0.62
    assert round(float(result.confidence_breakdown["decision_threshold"]), 2) == 0.5
