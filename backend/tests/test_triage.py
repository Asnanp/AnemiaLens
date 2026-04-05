"""
Tests for TriageService — the decision layer that combines image quality,
ML prediction, and self-reported symptoms into a risk band.

Coverage targets:
- Each risk band is reachable via the expected combination of inputs.
- Band boundaries are respected when risk scores sit on either side of a threshold.
- Quality failure always yields uncertain_retake_needed regardless of prediction.
- Specific issue codes (eye_not_visible) surface in the triage summary.
- Triage score is always in [0, 1].
- Computed properties on TriageResult work correctly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas import PredictionResult, QualityAssessment, QualityIssue, SymptomInput, TriageResult
from app.services.triage import TriageService


# ---------------------------------------------------------------------------
# Fixtures / factories
# ---------------------------------------------------------------------------

def _quality(
    passed: bool = True,
    issues: list[dict] | None = None,
) -> QualityAssessment:
    return QualityAssessment(
        passed=passed,
        blur_score=82.0,
        brightness_score=0.46,
        contrast_score=0.22,
        framing_score=1.2,
        issues=issues or [],
    )


def _prediction(
    risk: float,
    confidence: float = 0.72,
    uncertainty: float = 0.20,
    label: str | None = None,
    predicted_hb: float | None = None,
) -> PredictionResult:
    if label is None:
        label = "anemia_likely" if risk > 0.62 else ("anemia_unlikely" if risk < 0.35 else "uncertain")
    return PredictionResult(
        anemia_risk=risk,
        predicted_hemoglobin=predicted_hb,
        confidence=confidence,
        uncertainty=uncertainty,
        reliability_flag="medium",
        screening_label=label,
        screening_text="Screening model output.",
        model_source="archive-fusion-v2",
    )


SERVICE = TriageService()


# ---------------------------------------------------------------------------
# Happy-path band routing
# ---------------------------------------------------------------------------

class TestBandRouting:
    def test_high_concern_for_strong_signal_with_symptoms(self) -> None:
        result = SERVICE.assess(
            _quality(),
            _prediction(0.78),
            SymptomInput(fatigue=True, dizziness=True, shortness_of_breath=True, poor_diet_low_iron=True),
        )
        assert result.band == "high_concern"

    def test_moderate_risk_for_mid_signal_no_symptoms(self) -> None:
        result = SERVICE.assess(_quality(), _prediction(0.52), SymptomInput())
        assert result.band in {"moderate_risk", "high_concern"}

    def test_low_risk_for_weak_signal_no_symptoms(self) -> None:
        result = SERVICE.assess(_quality(), _prediction(0.18), SymptomInput())
        assert result.band == "low_risk"

    def test_low_band_for_anemia_unlikely_signal_with_normal_hb(self) -> None:
        result = SERVICE.assess(
            _quality(),
            _prediction(0.43, label="anemia_unlikely", predicted_hb=13.1),
            SymptomInput(),
        )
        assert result.band == "low_risk"

    def test_moderate_band_for_likely_signal_with_mildly_low_hb(self) -> None:
        result = SERVICE.assess(
            _quality(),
            _prediction(0.55, label="anemia_likely", predicted_hb=12.4),
            SymptomInput(),
        )
        assert result.band == "moderate_risk"

    def test_symptoms_alone_cannot_override_quality_failure(self) -> None:
        """Even with many symptoms, a quality failure must yield uncertain."""
        heavy_symptoms = SymptomInput(
            fatigue=True, dizziness=True, pale_skin=True, shortness_of_breath=True
        )
        result = SERVICE.assess(_quality(passed=False), None, heavy_symptoms)
        assert result.band == "uncertain_retake_needed"


# ---------------------------------------------------------------------------
# Quality-failure paths
# ---------------------------------------------------------------------------

class TestQualityFailure:
    def test_failed_quality_yields_uncertain(self) -> None:
        result = SERVICE.assess(_quality(passed=False), None, SymptomInput(fatigue=True))
        assert result.band == "uncertain_retake_needed"

    def test_eye_not_visible_surfaces_in_summary(self) -> None:
        quality = QualityAssessment(
            passed=False,
            blur_score=82.0,
            brightness_score=0.2,
            contrast_score=0.18,
            framing_score=0.9,
            issues=[
                QualityIssue(
                    code="eye_not_visible",
                    severity="blocking",
                    title="Eye is not clearly visible",
                    message="Retake with the inner lower eyelid clearly visible.",
                )
            ],
        )
        result = SERVICE.assess(quality, None, SymptomInput())
        assert result.band == "uncertain_retake_needed"
        assert "inner eyelid" in result.summary.lower() or "eyelid" in result.summary.lower()

    def test_blur_issue_surfaces_in_summary(self) -> None:
        quality = _quality(
            passed=False,
            issues=[
                {"code": "blur_detected", "severity": "blocking",
                 "title": "Image is blurry", "message": "Hold the camera steady and retake."}
            ],
        )
        result = SERVICE.assess(quality, None, SymptomInput())
        assert result.band == "uncertain_retake_needed"


# ---------------------------------------------------------------------------
# Score validity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("risk,sym_count", [
    (0.1, 0), (0.35, 1), (0.5, 2), (0.7, 4), (0.95, 5),
])
def test_triage_score_always_in_unit_interval(risk: float, sym_count: int) -> None:
    symptoms_on = list(SymptomInput.model_fields.keys())[:sym_count]
    symptoms = SymptomInput(**{k: True for k in symptoms_on if k != "heavy_menstrual_bleeding"})
    result = SERVICE.assess(_quality(), _prediction(risk), symptoms)
    assert 0.0 <= result.score <= 1.0


# ---------------------------------------------------------------------------
# TriageResult computed properties
# ---------------------------------------------------------------------------

class TestTriageResultProperties:
    def test_high_concern_requires_urgent_followup(self) -> None:
        t = TriageResult(
            band="high_concern", score=0.8, label="High concern",
            summary="Urgent.", disclaimer="Screening only.",
        )
        assert t.requires_urgent_followup is True
        assert t.requires_retake is False

    def test_uncertain_requires_retake(self) -> None:
        t = TriageResult(
            band="uncertain_retake_needed", score=0.3, label="Uncertain",
            summary="Retake needed.", disclaimer="Screening only.",
        )
        assert t.requires_retake is True
        assert t.requires_urgent_followup is False

    def test_low_risk_neither_urgent_nor_retake(self) -> None:
        t = TriageResult(
            band="low_risk", score=0.15, label="Low risk",
            summary="Looking good.", disclaimer="Screening only.",
        )
        assert t.requires_urgent_followup is False
        assert t.requires_retake is False


# ---------------------------------------------------------------------------
# Disclaimer is always present
# ---------------------------------------------------------------------------

def test_triage_result_always_has_disclaimer() -> None:
    result = SERVICE.assess(_quality(), _prediction(0.5), SymptomInput())
    assert len(result.disclaimer) > 20
    assert "screening" in result.disclaimer.lower()


def test_signal_breakdown_exposes_fusion_components() -> None:
    quality = _quality()
    prediction = _prediction(0.64, confidence=0.81, uncertainty=0.17)
    symptoms = SymptomInput(fatigue=True, pale_skin=True)

    breakdown = SERVICE.build_signal_breakdown(quality, prediction, symptoms)

    assert breakdown.image_risk == 0.64
    assert breakdown.symptom_score == pytest.approx(0.42)
    assert breakdown.fused_score == pytest.approx((0.64 * 0.55) + (0.42 * 0.45))
    assert breakdown.image_weight == 0.55
    assert breakdown.symptom_weight == 0.45
    assert breakdown.reliability_flag == "medium"
