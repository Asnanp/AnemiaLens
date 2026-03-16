from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.prediction import ScreeningPredictor
from app.schemas import PredictionResult


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
