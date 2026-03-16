from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas import (
    DecisionAudit,
    GuidanceResult,
    PredictionResult,
    QualityAssessment,
    QualityIssue,
    SymptomInput,
    TriageResult,
)
from app.services.case_insight import CaseInsightService


def test_case_insight_builds_high_concern_story_with_drivers() -> None:
    service = CaseInsightService()
    pack = service.build(
        QualityAssessment(
            passed=True,
            blur_score=210.0,
            brightness_score=0.46,
            contrast_score=0.18,
            framing_score=1.9,
            issues=[],
        ),
        PredictionResult(
            anemia_risk=0.82,
            predicted_hemoglobin=7.6,
            confidence=0.89,
            uncertainty=0.09,
            reliability_flag="high",
            screening_label="anemia_likely",
            screening_text="The screening model detected a strong low-hemoglobin signal.",
            model_source="archive-evidence-fusion-v4",
        ),
        TriageResult(
            band="high_concern",
            score=0.88,
            label="High concern",
            summary="Arrange formal review soon.",
            disclaimer="Screening only.",
        ),
        DecisionAudit(
            processing_path="roi_crop",
            calibration_band="strong_positive",
            decision_threshold=0.435,
            threshold_margin=0.385,
            quality_warning_codes=[],
            review_flags=[],
            summary="Direct ROI inference produced a strong positive margin.",
        ),
        GuidanceResult(
            source="fallback",
            explanation="Severely low hemoglobin signal.",
            urgency_guidance="Seek medical attention within 24-48 hours.",
            food_advice="Eat iron-rich foods.",
            next_steps=["Visit nearest clinic or hospital today", "Request a full blood count (CBC) test"],
        ),
        SymptomInput(fatigue=True, shortness_of_breath=True),
    )

    assert pack.priority_window == "within_24_48_hours"
    assert pack.risk_drivers[0].impact == "up"
    assert any(driver.title == "Very low hemoglobin estimate" for driver in pack.risk_drivers)
    assert any("Avoid strenuous activity" in step.action for step in pack.follow_up_timeline)
    assert "symptom fusion" in pack.judge_summary.lower()


def test_case_insight_marks_rescue_path_as_confidence_limit() -> None:
    service = CaseInsightService()
    pack = service.build(
        QualityAssessment(
            passed=True,
            blur_score=180.0,
            brightness_score=0.39,
            contrast_score=0.13,
            framing_score=1.1,
            issues=[
                QualityIssue(
                    code="bad_framing",
                    severity="warning",
                    title="Eye framing is loose",
                    message="Recenter the eye.",
                )
            ],
        ),
        PredictionResult(
            anemia_risk=0.51,
            predicted_hemoglobin=10.9,
            confidence=0.63,
            uncertainty=0.29,
            reliability_flag="medium",
            screening_label="anemia_likely",
            screening_text="The screening model detected some pallor-like signal.",
            model_source="archive-evidence-fusion-v4",
        ),
        TriageResult(
            band="moderate_risk",
            score=0.59,
            label="Moderate risk",
            summary="Routine clinic follow-up is reasonable.",
            disclaimer="Screening only.",
        ),
        DecisionAudit(
            processing_path="full_frame_rescue",
            calibration_band="borderline_positive",
            decision_threshold=0.435,
            threshold_margin=0.075,
            quality_warning_codes=["bad_framing"],
            review_flags=["raw_frame_rescue", "warning:bad_framing"],
            summary="Full-frame rescue accepted a borderline positive result.",
        ),
        GuidanceResult(
            source="fallback",
            explanation="Mild to moderate anemia-like signal.",
            urgency_guidance="See a doctor within 1-2 weeks.",
            food_advice="Eat iron-rich foods.",
            next_steps=["Book a clinic visit this week", "Start iron-rich diet immediately"],
        ),
        SymptomInput(),
    )

    assert "full-frame rescue" in pack.confidence_story.lower()
    assert any(driver.impact == "limit" for driver in pack.risk_drivers)
    assert any("direct conjunctiva crop" in item.lower() for item in pack.capture_improvements)


def test_case_insight_handles_quality_blocked_retake_case() -> None:
    service = CaseInsightService()
    pack = service.build(
        QualityAssessment(
            passed=False,
            blur_score=42.0,
            brightness_score=0.06,
            contrast_score=0.03,
            framing_score=0.42,
            issues=[
                QualityIssue(
                    code="poor_lighting",
                    severity="blocking",
                    title="Lighting is not usable",
                    message="Use bright natural light.",
                )
            ],
        ),
        None,
        TriageResult(
            band="uncertain_retake_needed",
            score=0.2,
            label="Uncertain, retake needed",
            summary="Retake the image.",
            disclaimer="Screening only.",
        ),
        DecisionAudit(
            processing_path="quality_blocked",
            calibration_band="quality_blocked",
            decision_threshold=None,
            threshold_margin=None,
            quality_warning_codes=[],
            review_flags=["quality_blocked"],
            summary="Quality blocked model inference.",
        ),
        GuidanceResult(
            source="fallback",
            explanation="Image signal was not strong enough.",
            urgency_guidance="Retake the scan in better lighting.",
            food_advice="No food advice until a valid screening is available.",
            next_steps=["Retake eye image in bright natural light"],
        ),
        SymptomInput(dizziness=True),
    )

    assert pack.priority_window == "retake_now"
    assert "blocked model inference" in pack.risk_drivers[0].detail.lower()
    assert pack.capture_improvements[0].startswith("Move into bright, even natural light")
    assert "safety gate" in pack.judge_summary.lower()
