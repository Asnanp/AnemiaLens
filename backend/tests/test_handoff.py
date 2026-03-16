from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas import GuidanceResult, PredictionResult, QualityAssessment, SymptomInput, TriageResult
from app.services.handoff import HandoffSummaryService


def test_handoff_summary_includes_prediction_symptoms_and_next_steps() -> None:
    service = HandoffSummaryService()
    summary = service.build(
        QualityAssessment(
            passed=True,
            blur_score=120.0,
            brightness_score=0.24,
            contrast_score=0.18,
            framing_score=1.8,
            issues=[],
        ),
        PredictionResult(
            anemia_risk=0.66,
            predicted_hemoglobin=10.4,
            confidence=0.81,
            uncertainty=0.19,
            reliability_flag="high",
            screening_label="anemia_likely",
            screening_text="The screening model estimates a lower-than-expected hemoglobin trend from the eye image.",
            model_source="efficientnet-b0-ft",
        ),
        TriageResult(
            band="moderate_risk",
            score=0.54,
            label="Moderate risk",
            summary="This screening shows some concern.",
            disclaimer="Screening only.",
        ),
        GuidanceResult(
            source="fallback",
            model_used=None,
            provider_used=None,
            explanation="Mild to moderate anemia detected.",
            urgency_guidance="See a doctor within 1-2 weeks.",
            food_advice="Eat iron-rich foods.",
            next_steps=["Book a clinic visit this week", "Start iron-rich diet immediately"],
        ),
        SymptomInput(fatigue=True, dizziness=True, poor_diet_low_iron=True),
        language="English",
        region="India",
    )

    assert "Moderate risk" in summary.headline
    assert any("Estimated hemoglobin" in point for point in summary.key_points)
    assert any("fatigue" in point for point in summary.key_points)
    assert summary.next_steps[0] == "Book a clinic visit this week"
    assert "AnemiaLens screening handoff" in summary.share_text


def test_handoff_summary_handles_retake_case_without_prediction() -> None:
    service = HandoffSummaryService()
    summary = service.build(
        QualityAssessment(
            passed=False,
            blur_score=40.0,
            brightness_score=0.05,
            contrast_score=0.02,
            framing_score=0.4,
            issues=[],
        ),
        None,
        TriageResult(
            band="uncertain_retake_needed",
            score=0.24,
            label="Uncertain, retake needed",
            summary="Retake the image.",
            disclaimer="Screening only.",
        ),
        GuidanceResult(
            source="fallback",
            model_used=None,
            provider_used=None,
            explanation="Image signal was not strong enough.",
            urgency_guidance="Retake the scan in better lighting.",
            food_advice="No food advice until a valid screening is available.",
            next_steps=["Retake eye image in bright natural light"],
        ),
        SymptomInput(),
    )

    assert summary.urgency_label == "Retake image"
    assert "quality" in summary.key_points[0].lower()
    assert "Retake" in summary.share_text
