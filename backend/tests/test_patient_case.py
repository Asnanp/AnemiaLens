from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas import (
    GuidanceResult,
    PatientProfileInput,
    PredictionResult,
    QualityAssessment,
    QualityIssue,
    SymptomInput,
    TriageResult,
)
from app.services.patient_case import PatientCaseService


def _quality(*, passed: bool = True, warnings: list[QualityIssue] | None = None, blockers: list[QualityIssue] | None = None) -> QualityAssessment:
    return QualityAssessment(
        passed=passed,
        blur_score=120.0,
        brightness_score=0.44,
        contrast_score=0.22,
        framing_score=1.2,
        lighting_score=0.74,
        lighting_condition="balanced",
        lighting_summary="Even clinical-style lighting.",
        glare_risk=0.1,
        shadow_risk=0.15,
        issues=[*(warnings or []), *(blockers or [])],
    )


def test_build_profile_generates_patient_id_and_summary() -> None:
    service = PatientCaseService()
    symptoms = SymptomInput(fatigue=True, dizziness=True)

    profile = service.build_profile(
        "abc123ef",
        PatientProfileInput(age=17, sex="female", diet_type="vegetarian"),
        symptoms,
    )

    assert profile.patient_id == "ANM-C123EF"
    assert profile.reported_symptoms == ["Fatigue", "Dizziness"]
    assert "17-year-old female" in profile.summary.lower()


def test_build_workflow_stages_marks_quality_block() -> None:
    service = PatientCaseService()
    blocked_quality = _quality(
        passed=False,
        blockers=[
            QualityIssue(
                code="eye_not_visible",
                severity="blocking",
                title="Eye region not visible",
                message="Pull down the lower eyelid and try again.",
            )
        ],
    )

    stages = service.build_workflow_stages(
        blocked_quality,
        None,
        TriageResult(
            band="uncertain_retake_needed",
            score=0.22,
            label="Uncertain, retake needed",
            summary="Retake needed before screening interpretation.",
            disclaimer="Screening only.",
        ),
        GuidanceResult(
            source="fallback",
            explanation="Fallback guidance.",
            urgency_guidance="Retake the image first.",
            food_advice="Eat iron-rich foods.",
            next_steps=["Retake image", "Repeat screening"],
        ),
        SymptomInput(),
    )

    assert stages[0].status == "blocked"
    assert stages[1].status == "blocked"


def test_build_structured_case_contains_quality_and_recommendation() -> None:
    service = PatientCaseService()
    quality = _quality(
        warnings=[
            QualityIssue(
                code="poor_lighting",
                severity="warning",
                title="Dim lighting",
                message="Move into brighter light.",
            )
        ]
    )
    prediction = PredictionResult(
        anemia_risk=0.64,
        predicted_hemoglobin=11.9,
        confidence=0.72,
        uncertainty=0.18,
        reliability_flag="medium",
        screening_label="anemia_likely",
        screening_text="Moderate anemia-like screening signal.",
        model_source="archive-evidence-fusion-v4",
    )
    triage = TriageResult(
        band="moderate_risk",
        score=0.58,
        label="Moderate risk",
        summary="This screening shows some concern.",
        disclaimer="Screening only.",
    )
    guidance = GuidanceResult(
        source="fallback",
        explanation="Result suggests follow-up.",
        urgency_guidance="Arrange a CBC in 1-2 weeks.",
        food_advice="Add beans and greens.",
        next_steps=["Arrange CBC", "See clinician"],
    )
    symptoms = SymptomInput(fatigue=True, poor_diet_low_iron=True)
    profile = service.build_profile("abc123ef", PatientProfileInput(age=21, sex="female", diet_type="vegetarian"), symptoms)

    case_record = service.build_structured_case(
        "abc123ef",
        profile,
        quality,
        prediction,
        triage,
        guidance,
        symptoms,
    )

    assert case_record.case_id == "CASE-C123EF"
    assert case_record.image_quality.status == "warning"
    assert case_record.screening_result.risk_level == "moderate_risk"
    assert case_record.recommendation == "Arrange CBC"
