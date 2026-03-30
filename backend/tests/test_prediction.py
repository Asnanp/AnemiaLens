from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml import archive_model as archive_model_module
from app.services.prediction import ScreeningPredictor
from app.services import prediction as prediction_module
from app.schemas import PatientProfileInput, PredictionResult, QualityAssessment


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


def test_screening_decision_downgrades_strong_positive_when_hb_is_clearly_normal() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)

    label, text = predictor._screening_decision(
        risk=0.78,
        uncertainty=0.28,
        threshold=0.42,
        predicted_hemoglobin=14.9,
    )

    assert label == "uncertain"
    assert "do not agree" in text.lower()


def test_v8_live_decision_threshold_uses_recall_friendly_override() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)

    assert predictor._v8_live_decision_threshold(0.42) == 0.30
    assert predictor._v8_live_decision_threshold(0.26) == 0.26


def test_display_hemoglobin_keeps_value_even_when_uncertainty_is_high() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)

    assert predictor._display_hemoglobin(12.84, 0.82) == 12.84


def test_v8_classifier_rescue_lifts_borderline_positive_signal() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    quality = QualityAssessment(
        passed=True,
        blur_score=160.0,
        brightness_score=0.28,
        contrast_score=0.15,
        framing_score=1.8,
        lighting_score=0.44,
        lighting_condition="glare_heavy",
        lighting_summary="Glare is present.",
        glare_risk=0.58,
        shadow_risk=0.08,
        issues=[],
    )

    rescued_risk, rescued = predictor._apply_v8_classifier_rescue(
        risk=0.24,
        decision_threshold=0.30,
        prediction={"classifier_probability": 0.27},
        feature_map={"clinical_pallor_score": 0.58},
        quality=quality,
    )

    assert rescued is True
    assert rescued_risk >= 0.31


def test_v8_conflicted_hb_is_suppressed_for_strong_image_signal() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    quality = QualityAssessment(
        passed=True,
        blur_score=170.0,
        brightness_score=0.24,
        contrast_score=0.16,
        framing_score=1.9,
        lighting_score=0.72,
        lighting_condition="balanced",
        lighting_summary="Balanced lighting.",
        glare_risk=0.05,
        shadow_risk=0.10,
        issues=[],
    )

    suppressed = predictor._should_suppress_v8_conflicted_hemoglobin(
        risk=0.46,
        decision_threshold=0.30,
        prediction={
            "predicted_hemoglobin": 14.8,
            "classifier_probability": 0.38,
            "regressor_risk": 0.07,
        },
        feature_map={"clinical_pallor_score": 0.69},
        quality=quality,
    )

    assert suppressed is True


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


def test_should_accept_raw_frame_rescue_for_v8_positive_signal_floor() -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    prediction = PredictionResult(
        anemia_risk=0.4,
        predicted_hemoglobin=None,
        confidence=0.34,
        uncertainty=0.69,
        reliability_flag="low",
        screening_label="anemia_likely",
        screening_text="Likely anemia.",
        model_source="archive-fusion-v8-clinical-robust",
        confidence_breakdown={"v8_positive_risk_floor_applied": True},
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


def test_predict_uses_v8_rescue_when_classifier_signal_conflicts_with_hb(monkeypatch) -> None:
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
    predictor.runtime_hb_calibrator = None
    predictor._runtime_risk_calibrator_load_attempted = True
    predictor._runtime_hb_calibrator_load_attempted = True
    predictor.runtime_screening_refiner = object()
    predictor._runtime_screening_refiner_load_attempted = True

    monkeypatch.setattr(
        predictor,
        "_ensure_archive_model_loaded",
        lambda: {"version": "archive-fusion-v8-clinical-robust"},
    )
    monkeypatch.setattr(
        prediction_module,
        "extract_eye_features",
        lambda image: {
            "brightness": 0.21,
            "hist_bright": 0.06,
            "hist_highlight": 0.01,
        },
    )
    monkeypatch.setattr(
        prediction_module,
        "extract_v8_clinical_features",
        lambda image, quality, **kwargs: {
            "clinical_pallor_score": 0.68,
            "brightness": 0.21,
            "contrast": 0.15,
            "center_cpi": 0.31,
            "pallor_score": 0.40,
        },
    )
    monkeypatch.setattr(
        prediction_module,
        "_predict_archive_model",
        lambda artifact, feature_map, source_hint: {
            "anemia_risk": 0.26,
            "uncertainty": 0.24,
            "predicted_hemoglobin": 14.9,
            "classifier_probability": 0.36,
            "regressor_risk": 0.08,
            "decision_threshold": 0.42,
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

    assert result.screening_label == "anemia_likely"
    assert result.predicted_hemoglobin is None
    assert result.confidence_breakdown is not None
    assert result.confidence_breakdown["v8_live_threshold_override"] is True
    assert result.confidence_breakdown["v8_image_signal_rescue"] is True
    assert result.confidence_breakdown["v8_hb_suppressed"] is True
    assert result.confidence_breakdown["v8_hb_display_disabled"] is False


def test_predict_shows_v8_hemoglobin_when_capture_is_coherent(monkeypatch) -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    predictor.enable_efficientnet_fallback = False
    predictor.archive_model = None
    predictor.efficientnet_bundle = None
    predictor.runtime_risk_calibrator = None
    predictor.runtime_hb_calibrator = None
    predictor.runtime_screening_refiner = None
    predictor.ultimate_runtime_refiner = None
    predictor._archive_model_load_attempted = True
    predictor._efficientnet_model_load_attempted = True
    predictor._runtime_risk_calibrator_load_attempted = True
    predictor._runtime_hb_calibrator_load_attempted = True
    predictor._runtime_screening_refiner_load_attempted = True
    predictor._ultimate_runtime_refiner_load_attempted = True
    predictor.load_error = None

    quality = QualityAssessment(
        passed=True,
        blur_score=180.0,
        brightness_score=0.30,
        contrast_score=0.16,
        framing_score=1.8,
        lighting_score=0.81,
        lighting_condition="balanced",
        lighting_summary="Lighting looks usable for screening.",
        glare_risk=0.02,
        shadow_risk=0.04,
        issues=[],
    )

    monkeypatch.setattr(
        predictor,
        "_ensure_archive_model_loaded",
        lambda: {"version": "archive-fusion-v8-clinical-robust"},
    )
    monkeypatch.setattr(predictor, "_ensure_runtime_risk_calibrator_loaded", lambda: None)
    monkeypatch.setattr(
        "app.services.prediction.extract_eye_features",
        lambda image: {
            "brightness": 0.30,
            "contrast": 0.16,
            "blur_score": 180.0,
        },
    )
    monkeypatch.setattr(
        "app.services.prediction.extract_v8_clinical_features",
        lambda image, quality, **kwargs: {
            "clinical_pallor_score": 0.18,
            "brightness": 0.30,
            "contrast": 0.16,
            "lighting_score": 0.81,
            "glare_risk": 0.02,
            "shadow_risk": 0.04,
        },
    )
    monkeypatch.setattr(
        "app.services.prediction._predict_archive_model",
        lambda artifact, feature_map, source_hint: {
            "anemia_risk": 0.18,
            "predicted_hemoglobin": 15.7,
            "uncertainty": 0.22,
            "classifier_probability": 0.12,
            "regressor_risk": 0.03,
            "decision_threshold": 0.42,
        },
    )

    result = predictor.predict(Image.new("RGB", (224, 224), color=(170, 90, 80)), quality)

    assert result.screening_label == "anemia_unlikely"
    assert result.predicted_hemoglobin == 15.7
    assert result.confidence_breakdown is not None
    assert result.confidence_breakdown["v8_hb_display_disabled"] is False
    assert result.confidence_breakdown["v8_hb_hidden_for_trust"] is False


def test_predict_keeps_v8_hemoglobin_for_passed_overexposed_capture(monkeypatch) -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    predictor.enable_efficientnet_fallback = False
    predictor.archive_model = None
    predictor.efficientnet_bundle = None
    predictor.runtime_risk_calibrator = None
    predictor.runtime_hb_calibrator = None
    predictor.runtime_screening_refiner = None
    predictor.ultimate_runtime_refiner = None
    predictor._archive_model_load_attempted = True
    predictor._efficientnet_model_load_attempted = True
    predictor._runtime_risk_calibrator_load_attempted = True
    predictor._runtime_hb_calibrator_load_attempted = True
    predictor._runtime_screening_refiner_load_attempted = True
    predictor._ultimate_runtime_refiner_load_attempted = True
    predictor.load_error = None

    quality = QualityAssessment(
        passed=True,
        blur_score=180.0,
        brightness_score=0.48,
        contrast_score=0.14,
        framing_score=1.7,
        lighting_score=0.58,
        lighting_condition="overexposed",
        lighting_summary="The image is brighter than ideal but the eyelid is still visible.",
        glare_risk=0.54,
        shadow_risk=0.03,
        issues=[],
    )

    monkeypatch.setattr(
        predictor,
        "_ensure_archive_model_loaded",
        lambda: {"version": "archive-fusion-v8-clinical-robust"},
    )
    monkeypatch.setattr(predictor, "_ensure_runtime_risk_calibrator_loaded", lambda: None)
    monkeypatch.setattr(
        "app.services.prediction.extract_eye_features",
        lambda image: {
            "brightness": 0.48,
            "contrast": 0.14,
            "blur_score": 180.0,
        },
    )
    monkeypatch.setattr(
        "app.services.prediction.extract_v8_clinical_features",
        lambda image, quality, **kwargs: {
            "clinical_pallor_score": 0.34,
            "brightness": 0.48,
            "contrast": 0.14,
            "lighting_score": 0.58,
            "glare_risk": 0.54,
            "shadow_risk": 0.03,
        },
    )
    monkeypatch.setattr(
        "app.services.prediction._predict_archive_model",
        lambda artifact, feature_map, source_hint: {
            "anemia_risk": 0.41,
            "predicted_hemoglobin": 12.6,
            "uncertainty": 0.31,
            "classifier_probability": 0.39,
            "regressor_risk": 0.27,
            "decision_threshold": 0.42,
        },
    )

    result = predictor.predict(Image.new("RGB", (224, 224), color=(205, 120, 115)), quality)

    assert result.predicted_hemoglobin == 12.6
    assert result.confidence_breakdown is not None
    assert result.confidence_breakdown["v8_hb_hidden_for_trust"] is False


def test_predict_keeps_v8_hemoglobin_for_passed_shadow_heavy_capture(monkeypatch) -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    predictor.enable_efficientnet_fallback = False
    predictor.archive_model = None
    predictor.efficientnet_bundle = None
    predictor.runtime_risk_calibrator = None
    predictor.runtime_hb_calibrator = None
    predictor.runtime_screening_refiner = None
    predictor.ultimate_runtime_refiner = None
    predictor._archive_model_load_attempted = True
    predictor._efficientnet_model_load_attempted = True
    predictor._runtime_risk_calibrator_load_attempted = True
    predictor._runtime_hb_calibrator_load_attempted = True
    predictor._runtime_screening_refiner_load_attempted = True
    predictor._ultimate_runtime_refiner_load_attempted = True
    predictor.load_error = None

    quality = QualityAssessment(
        passed=True,
        blur_score=92.0,
        brightness_score=0.19,
        contrast_score=0.12,
        framing_score=1.3,
        lighting_score=0.34,
        lighting_condition="shadow_heavy",
        lighting_summary="Shadow is present but the lower eyelid is still readable.",
        glare_risk=0.06,
        shadow_risk=0.74,
        issues=[],
    )

    monkeypatch.setattr(
        predictor,
        "_ensure_archive_model_loaded",
        lambda: {"version": "archive-fusion-v8-clinical-robust"},
    )
    monkeypatch.setattr(predictor, "_ensure_runtime_risk_calibrator_loaded", lambda: None)
    monkeypatch.setattr(
        "app.services.prediction.extract_eye_features",
        lambda image: {
            "brightness": 0.19,
            "contrast": 0.12,
            "blur_score": 92.0,
        },
    )
    monkeypatch.setattr(
        "app.services.prediction.extract_v8_clinical_features",
        lambda image, quality, **kwargs: {
            "clinical_pallor_score": 0.42,
            "brightness": 0.19,
            "contrast": 0.12,
            "lighting_score": 0.34,
            "glare_risk": 0.06,
            "shadow_risk": 0.74,
        },
    )
    monkeypatch.setattr(
        "app.services.prediction._predict_archive_model",
        lambda artifact, feature_map, source_hint: {
            "anemia_risk": 0.52,
            "predicted_hemoglobin": 11.2,
            "uncertainty": 0.58,
            "classifier_probability": 0.55,
            "regressor_risk": 0.43,
            "decision_threshold": 0.42,
        },
    )

    result = predictor.predict(Image.new("RGB", (224, 224), color=(130, 60, 65)), quality)

    assert result.predicted_hemoglobin == 11.2
    assert result.confidence_breakdown is not None
    assert result.confidence_breakdown["v8_hb_hidden_for_trust"] is False


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


def test_predict_harmonizes_runtime_refiner_when_normal_hb_conflicts_with_positive_risk(
    monkeypatch,
) -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    predictor.enable_efficientnet_fallback = False
    predictor.archive_model = None
    predictor.efficientnet_bundle = None
    predictor.load_error = None
    predictor.model_path = Path("archive.joblib")
    predictor.efficientnet_path = Path("efficientnet.pth")
    predictor.runtime_risk_calibrator = None
    predictor._runtime_risk_calibrator_load_attempted = True
    predictor.runtime_screening_refiner = None
    predictor._runtime_screening_refiner_load_attempted = False
    predictor.ultimate_runtime_refiner = None
    predictor._ultimate_runtime_refiner_load_attempted = True

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
            assert base_anemia_risk == 0.35
            assert predicted_hemoglobin == 14.9
            return 0.96

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
        predictor,
        "_ensure_runtime_risk_calibrator_loaded",
        lambda: None,
    )
    monkeypatch.setattr(
        prediction_module,
        "extract_eye_features",
        lambda image: {
            "brightness": 0.28,
            "hist_bright": 0.07,
            "hist_highlight": 0.01,
        },
    )
    monkeypatch.setattr(
        prediction_module,
        "_predict_archive_model",
        lambda artifact, feature_map, source_hint: {
            "anemia_risk": 0.35,
            "uncertainty": 0.24,
            "predicted_hemoglobin": 14.9,
        },
    )
    monkeypatch.setattr(
        prediction_module,
        "_build_runtime_stack",
        lambda archive_prediction, **kwargs: {
            "anemia_risk": 0.35,
            "uncertainty": 0.24,
            "predicted_hemoglobin": 14.9,
            "decision_threshold": 0.42,
        },
    )

    quality = QualityAssessment(
        passed=True,
        blur_score=160.0,
        brightness_score=0.28,
        contrast_score=0.16,
        framing_score=1.3,
        lighting_score=0.76,
        lighting_condition="balanced",
        lighting_summary="Lighting is balanced enough for screening.",
        glare_risk=0.03,
        shadow_risk=0.04,
        issues=[],
    )

    result = predictor.predict(Image.new("RGB", (80, 80), "white"), quality)

    assert result.anemia_risk < 0.42
    assert result.screening_label == "anemia_unlikely"
    assert result.confidence_breakdown is not None
    assert result.confidence_breakdown["risk_harmonized"] is True


class _FakeUltimateScaler:
    def transform(self, rows):
        return rows


class _FakeUltimateRegressor:
    def __init__(self, value: float) -> None:
        self.value = value

    def predict(self, rows):
        return [self.value]


class _FakeUltimateClassifier:
    def __init__(self, probability: float) -> None:
        self.probability = probability

    def predict_proba(self, rows):
        return [[1.0 - self.probability, self.probability]]


class _FakeUltimateRuntimeRefiner:
    threshold = 0.35
    method = "gradient-boosting-compatibility"

    def remap_ultimate_features(
        self,
        feature_map,
        *,
        archive_feature_names,
        expected_means,
        expected_stds,
    ):
        return {
            name: float(feature_map.get(name, expected_means.get(name, 0.0)))
            for name in archive_feature_names
        }

    def refine(self, *, base_prediction, quality, base_feature_map):
        return 0.18


def test_ultimate_archive_prediction_returns_complete_signal_set() -> None:
    artifact = {
        "version": "archive-fusion-v7-ultimate-clinical",
        "feature_names": archive_model_module.ULTIMATE_CLINICAL_FEATURE_NAMES,
        "scaler": _FakeUltimateScaler(),
        "models": {
            "gb_hb": _FakeUltimateRegressor(11.2),
            "rf_hb": _FakeUltimateRegressor(11.5),
            "ridge_hb": _FakeUltimateRegressor(11.4),
            "gb_clf": _FakeUltimateClassifier(0.73),
            "rf_clf": _FakeUltimateClassifier(0.69),
            "lr_clf": _FakeUltimateClassifier(0.71),
            "calibrated_clf": _FakeUltimateClassifier(0.75),
        },
    }
    feature_map = {name: 0.35 for name in archive_model_module.ULTIMATE_CLINICAL_FEATURE_NAMES}

    result = archive_model_module.predict_with_archive_model(artifact, feature_map)

    assert 0.0 <= result["anemia_risk"] <= 1.0
    assert 0.0 <= result["classifier_probability"] <= 1.0
    assert 0.0 <= result["regressor_risk"] <= 1.0
    assert 0.0 <= result["blend_signal"] <= 1.0
    assert 0.0 <= result["uncertainty"] <= 1.0
    assert result["hb_interval_low"] < result["hb_interval_high"]


def test_predict_ultimate_model_survives_missing_quality(monkeypatch) -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    predictor.enable_efficientnet_fallback = False
    predictor.archive_model = {
        "version": "archive-fusion-v7-ultimate-clinical",
        "feature_names": archive_model_module.ULTIMATE_CLINICAL_FEATURE_NAMES,
        "scaler": _FakeUltimateScaler(),
    }
    predictor.efficientnet_bundle = None
    predictor.load_error = None
    predictor.model_path = Path("ultimate.joblib")
    predictor.efficientnet_path = Path("efficientnet.pth")
    predictor.ultimate_refiner_path = Path("ultimate_runtime_refiner.pkl")
    predictor.runtime_risk_calibrator = None
    predictor.runtime_screening_refiner = None
    predictor.ultimate_runtime_refiner = None
    predictor._archive_model_load_attempted = True
    predictor._efficientnet_model_load_attempted = True
    predictor._runtime_risk_calibrator_load_attempted = True
    predictor._runtime_screening_refiner_load_attempted = True
    predictor._ultimate_runtime_refiner_load_attempted = True

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        predictor,
        "_ensure_archive_model_loaded",
        lambda: predictor.archive_model,
    )
    monkeypatch.setattr(
        predictor,
        "_ensure_runtime_risk_calibrator_loaded",
        lambda: None,
    )
    monkeypatch.setattr(
        predictor,
        "_ensure_runtime_screening_refiner_loaded",
        lambda: None,
    )
    monkeypatch.setattr(
        predictor,
        "_ensure_ultimate_runtime_refiner_loaded",
        lambda: None,
    )
    monkeypatch.setattr(
        prediction_module,
        "extract_eye_features",
        lambda image: {
            "brightness": 0.31,
            "contrast": 0.18,
            "blur_score": 128.0,
            "center_contrast": 0.2,
            "center_red_green_gap": 0.04,
            "highlight_fraction": 0.02,
            "shadow_fraction": 0.03,
            "illumination_std": 0.11,
            "size_score": 0.75,
            "hist_bright": 0.11,
            "hist_highlight": 0.02,
        },
    )

    def _fake_extract_ultimate(image, quality, *, age=None, sex="not_specified"):
        captured["quality"] = quality
        captured["age"] = age
        captured["sex"] = sex
        return {
            "lighting_uniformity": 0.82,
            "noise_level": 0.12,
            "pallor_intensity": 0.28,
            "pallor_gradient": 0.22,
        }

    monkeypatch.setattr(
        prediction_module,
        "extract_ultimate_clinical_features",
        _fake_extract_ultimate,
    )
    monkeypatch.setattr(
        prediction_module,
        "_predict_archive_model",
        lambda artifact, feature_map, source_hint: {
            "anemia_risk": 0.34,
            "uncertainty": 0.21,
            "predicted_hemoglobin": 12.7,
            "classifier_probability": 0.31,
            "regressor_risk": 0.29,
            "blend_signal": 0.30,
        },
    )
    monkeypatch.setattr(
        prediction_module,
        "_build_runtime_stack",
        lambda archive_prediction, **kwargs: {
            **archive_prediction,
            "decision_threshold": 0.5,
        },
    )

    result = predictor.predict(
        Image.new("RGB", (120, 120), "white"),
        None,
        patient_profile=PatientProfileInput(age=17, sex="female", diet_type="omnivore"),
    )

    assert isinstance(captured["quality"], QualityAssessment)
    assert captured["age"] == 17
    assert captured["sex"] == "female"
    assert result.model_source == "archive-fusion-v7-ultimate-clinical"
    assert result.predicted_hemoglobin is not None


def test_predict_ultimate_model_applies_runtime_refiner_to_reduce_false_positive(
    monkeypatch,
) -> None:
    predictor = ScreeningPredictor.__new__(ScreeningPredictor)
    predictor.enable_efficientnet_fallback = False
    predictor.archive_model = {
        "version": "archive-fusion-v7-ultimate-clinical",
        "feature_names": archive_model_module.ULTIMATE_CLINICAL_FEATURE_NAMES,
        "scaler": _FakeUltimateScaler(),
    }
    predictor.efficientnet_bundle = None
    predictor.load_error = None
    predictor.model_path = Path("ultimate.joblib")
    predictor.efficientnet_path = Path("efficientnet.pth")
    predictor.ultimate_refiner_path = Path("ultimate_runtime_refiner.pkl")
    predictor.runtime_risk_calibrator = None
    predictor.runtime_screening_refiner = None
    predictor.ultimate_runtime_refiner = _FakeUltimateRuntimeRefiner()
    predictor._archive_model_load_attempted = True
    predictor._efficientnet_model_load_attempted = True
    predictor._runtime_risk_calibrator_load_attempted = True
    predictor._runtime_screening_refiner_load_attempted = True
    predictor._ultimate_runtime_refiner_load_attempted = True

    monkeypatch.setattr(
        predictor,
        "_ensure_archive_model_loaded",
        lambda: predictor.archive_model,
    )
    monkeypatch.setattr(
        predictor,
        "_ensure_runtime_risk_calibrator_loaded",
        lambda: None,
    )
    monkeypatch.setattr(
        predictor,
        "_ensure_runtime_screening_refiner_loaded",
        lambda: None,
    )
    monkeypatch.setattr(
        predictor,
        "_ensure_ultimate_runtime_refiner_loaded",
        lambda: predictor.ultimate_runtime_refiner,
    )
    monkeypatch.setattr(
        prediction_module,
        "extract_eye_features",
        lambda image: {
            "brightness": 0.28,
            "contrast": 0.17,
            "blur_score": 150.0,
            "center_contrast": 0.19,
            "center_red_green_gap": 0.06,
            "center_cpi": 0.36,
            "pallor_score": 0.28,
            "rgb_entropy": 0.9,
            "center_blur_score": 980.0,
            "highlight_fraction": 0.01,
            "shadow_fraction": 0.02,
            "illumination_std": 0.08,
            "size_score": 0.8,
            "hist_bright": 0.09,
            "hist_highlight": 0.01,
        },
    )
    monkeypatch.setattr(
        prediction_module,
        "extract_ultimate_clinical_features",
        lambda image, quality, *, age=None, sex="not_specified": {
            name: 0.4 for name in archive_model_module.ULTIMATE_CLINICAL_FEATURE_NAMES
        },
    )
    monkeypatch.setattr(
        prediction_module,
        "_predict_archive_model",
        lambda artifact, feature_map, source_hint: {
            "anemia_risk": 0.91,
            "uncertainty": 0.24,
            "predicted_hemoglobin": 7.8,
            "classifier_probability": 0.88,
            "regressor_risk": 0.86,
            "blend_signal": 0.89,
        },
    )

    quality = QualityAssessment(
        passed=True,
        blur_score=150.0,
        brightness_score=0.28,
        contrast_score=0.17,
        framing_score=1.35,
        lighting_score=0.78,
        lighting_condition="balanced",
        lighting_summary="Lighting is balanced enough for reliable screening.",
        glare_risk=0.05,
        shadow_risk=0.08,
        issues=[],
    )

    result = predictor.predict(Image.new("RGB", (120, 120), "white"), quality)

    assert result.model_source == "archive-fusion-v7-ultimate-clinical"
    assert result.anemia_risk < 0.35
    assert result.screening_label == "anemia_unlikely"
    assert result.predicted_hemoglobin is None
    assert result.confidence_breakdown is not None
    assert result.confidence_breakdown["calibration_method"] == "ultimate-compatibility-remap"
    assert result.confidence_breakdown["refinement_method"] == "gradient-boosting-compatibility"
