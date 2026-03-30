from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas import GuidanceResult, PredictionResult, QualityAssessment, QualityIssue, SymptomInput, TriageResult
from app.services.decision_audit import build_decision_audit


def test_decision_audit_marks_full_frame_rescue_and_threshold_margin() -> None:
    audit = build_decision_audit(
        QualityAssessment(
            passed=True,
            blur_score=220.0,
            brightness_score=0.44,
            contrast_score=0.15,
            framing_score=1.7,
            issues=[
                QualityIssue(
                    code="bad_framing",
                    severity="warning",
                    title="Eye framing is loose",
                    message="The app fell back to the full eye frame.",
                )
            ],
        ),
        PredictionResult(
            anemia_risk=0.82,
            predicted_hemoglobin=10.8,
            confidence=0.66,
            uncertainty=0.34,
            reliability_flag="medium",
            screening_label="anemia_likely",
            screening_text="Likely anemia.",
            model_source="archive-evidence-fusion-v4",
        ),
        TriageResult(
            band="moderate_risk",
            score=0.54,
            label="Moderate risk",
            summary="Moderate concern.",
            disclaimer="Screening only.",
        ),
        used_raw_frame_rescue=True,
    )

    assert audit.processing_path == "full_frame_rescue"
    assert audit.calibration_band == "strong_positive"
    assert audit.decision_threshold == 0.495
    assert audit.threshold_margin == 0.325
    assert "raw_frame_rescue" in audit.review_flags
    assert "warning:bad_framing" in audit.review_flags


def test_decision_audit_handles_blocked_request() -> None:
    audit = build_decision_audit(
        QualityAssessment(
            passed=False,
            blur_score=40.0,
            brightness_score=0.05,
            contrast_score=0.03,
            framing_score=0.4,
            issues=[
                QualityIssue(
                    code="poor_lighting",
                    severity="blocking",
                    title="Lighting is not usable",
                    message="Use bright, even light.",
                )
            ],
        ),
        None,
        TriageResult(
            band="uncertain_retake_needed",
            score=0.2,
            label="Retake needed",
            summary="Retake the image.",
            disclaimer="Screening only.",
        ),
    )

    assert audit.processing_path == "quality_blocked"
    assert audit.calibration_band == "quality_blocked"
    assert audit.decision_threshold is None
    assert "quality_blocked" in audit.review_flags
    assert "blocked model inference" in audit.summary.lower()
