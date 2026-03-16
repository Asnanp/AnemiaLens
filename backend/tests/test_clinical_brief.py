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
from app.services.analysis_meta import build_analysis_meta
from app.services.case_insight import CaseInsightService
from app.services.clinical_brief import ClinicalBriefService
from app.services.handoff import HandoffSummaryService
from app.services.triage import TriageService


def test_clinical_brief_builds_grounded_high_concern_summary() -> None:
    quality = QualityAssessment(
        passed=True,
        blur_score=198.0,
        brightness_score=0.33,
        contrast_score=0.19,
        framing_score=1.9,
        issues=[],
    )
    prediction = PredictionResult(
        anemia_risk=0.84,
        predicted_hemoglobin=7.8,
        confidence=0.91,
        uncertainty=0.08,
        reliability_flag="high",
        screening_label="anemia_likely",
        screening_text="The screening model detected a strong low-hemoglobin signal.",
        model_source="archive-evidence-fusion-v4",
    )
    symptoms = SymptomInput(fatigue=True, shortness_of_breath=True, poor_diet_low_iron=True)
    triage_service = TriageService()
    signal_breakdown = triage_service.build_signal_breakdown(quality, prediction, symptoms)
    triage = triage_service.assess(
        quality,
        prediction,
        symptoms,
        signal_breakdown=signal_breakdown,
    )
    decision_audit = DecisionAudit(
        processing_path="roi_crop",
        calibration_band="strong_positive",
        decision_threshold=0.435,
        threshold_margin=0.405,
        quality_warning_codes=[],
        review_flags=[],
        summary="Direct ROI inference produced a strong positive margin.",
    )
    guidance = GuidanceResult(
        source="fallback",
        explanation="The screening signal is concerning and should be reviewed soon.",
        urgency_guidance="Seek medical review within 24 to 48 hours.",
        food_advice="Eat iron-rich foods and include vitamin C with meals.",
        next_steps=["Book a clinic or lab visit within 24 to 48 hours", "Request a CBC test"],
    )
    insight_pack = CaseInsightService().build(
        quality,
        prediction,
        triage,
        decision_audit,
        guidance,
        symptoms,
    )
    handoff_summary = HandoffSummaryService().build(
        quality,
        prediction,
        triage,
        guidance,
        symptoms,
    )

    brief = ClinicalBriefService().build(
        quality,
        prediction,
        triage,
        decision_audit,
        guidance,
        symptoms,
        insight_pack,
        handoff_summary,
        signal_breakdown,
    )

    assert brief.action_window == "within_24_48_hours"
    assert brief.signal_breakdown.image_risk == 0.84
    assert brief.signal_breakdown.symptom_burden == "moderate"
    assert any("hemoglobin signal" in item.lower() for item in brief.supporting_evidence)
    assert any("uncertainty" in item.lower() for item in brief.safety_checks)
    assert "AnemiaLens clinical brief" in brief.share_text


def test_clinical_brief_handles_quality_blocked_case_and_meta() -> None:
    quality = QualityAssessment(
        passed=False,
        blur_score=42.0,
        brightness_score=0.05,
        contrast_score=0.03,
        framing_score=0.4,
        issues=[
            QualityIssue(
                code="poor_lighting",
                severity="blocking",
                title="Lighting is not usable",
                message="Use bright natural light.",
            )
        ],
    )
    symptoms = SymptomInput(dizziness=True)
    triage_service = TriageService()
    signal_breakdown = triage_service.build_signal_breakdown(quality, None, symptoms)
    triage = triage_service.assess(
        quality,
        None,
        symptoms,
        signal_breakdown=signal_breakdown,
    )
    decision_audit = DecisionAudit(
        processing_path="quality_blocked",
        calibration_band="quality_blocked",
        decision_threshold=None,
        threshold_margin=None,
        quality_warning_codes=[],
        review_flags=["quality_blocked"],
        summary="Quality blocked model inference.",
    )
    guidance = GuidanceResult(
        source="fallback",
        explanation="The image was too weak for a reliable screening result.",
        urgency_guidance="Retake the scan in better light.",
        food_advice="Wait for a valid scan before using food guidance from the app.",
        next_steps=["Retake the image in bright natural light"],
    )
    insight_pack = CaseInsightService().build(
        quality,
        None,
        triage,
        decision_audit,
        guidance,
        symptoms,
    )
    handoff_summary = HandoffSummaryService().build(
        quality,
        None,
        triage,
        guidance,
        symptoms,
    )

    brief = ClinicalBriefService().build(
        quality,
        None,
        triage,
        decision_audit,
        guidance,
        symptoms,
        insight_pack,
        handoff_summary,
        signal_breakdown,
    )
    meta = build_analysis_meta(
        request_id="abc12345",
        api_version="0.3.0",
        processing_time_ms=187.36,
        quality=quality,
        decision_audit=decision_audit,
        guidance=guidance,
        used_raw_frame_rescue=False,
    )

    assert brief.signal_breakdown.image_risk is None
    assert any("blocked model inference" in item.lower() for item in brief.supporting_evidence)
    assert any("primary blocker" in item.lower() for item in brief.limiting_factors)
    assert "image=not available" in brief.share_text
    assert meta.request_id == "abc12345"
    assert meta.processing_path == "quality_blocked"
    assert meta.guidance_source == "fallback"
    assert meta.safety_layers == [
        "image_quality_gate",
        "symptom_fusion",
        "triage_banding",
        "non_diagnostic_guidance",
    ]
