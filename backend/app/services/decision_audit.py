from __future__ import annotations

from app.ml.runtime_stack import RUNTIME_STACK_VERSION, decision_threshold_for_source
from app.schemas import DecisionAudit, PredictionResult, QualityAssessment, TriageResult


_RUNTIME_STACK_SOURCES = {
    RUNTIME_STACK_VERSION,
    "archive-primary-v3",
    "archive-fusion-v2",
    "archive-fusion-v7-ultimate-clinical",
}


def build_decision_audit(
    quality: QualityAssessment,
    prediction: PredictionResult | None,
    triage: TriageResult,
    *,
    used_raw_frame_rescue: bool = False,
) -> DecisionAudit:
    warning_codes = [issue.code for issue in quality.warning_issues]
    review_flags: list[str] = []

    if prediction is None:
        review_flags.extend(["quality_blocked", *sorted({f"warning:{code}" for code in warning_codes})])
        return DecisionAudit(
            processing_path="quality_blocked",
            calibration_band="quality_blocked",
            decision_threshold=None,
            threshold_margin=None,
            quality_warning_codes=warning_codes,
            review_flags=review_flags,
            summary="Image quality blocked model inference before a screening result could be produced.",
        )

    threshold = _decision_threshold(prediction)
    margin = round(prediction.anemia_risk - threshold, 3)
    calibration_band = _calibration_band(prediction, margin)

    if used_raw_frame_rescue:
        review_flags.append("raw_frame_rescue")
    if warning_codes:
        review_flags.append("quality_warnings_present")
        review_flags.extend(sorted({f"warning:{code}" for code in warning_codes}))
    if prediction.reliability_flag == "low":
        review_flags.append("low_reliability")
    if prediction.predicted_hemoglobin is None:
        review_flags.append("hemoglobin_hidden")
    if abs(margin) < 0.05:
        review_flags.append("near_threshold")
    if prediction.screening_label == "uncertain":
        review_flags.append("borderline_signal")
    if triage.band == "uncertain_retake_needed":
        review_flags.append("retake_recommended")

    processing_path = "full_frame_rescue" if used_raw_frame_rescue else "roi_crop"
    return DecisionAudit(
        processing_path=processing_path,
        calibration_band=calibration_band,
        decision_threshold=round(threshold, 3),
        threshold_margin=margin,
        quality_warning_codes=warning_codes,
        review_flags=review_flags,
        summary=_build_summary(
            prediction,
            threshold=threshold,
            margin=margin,
            used_raw_frame_rescue=used_raw_frame_rescue,
        ),
    )


def _decision_threshold(prediction: PredictionResult) -> float:
    confidence_breakdown = prediction.confidence_breakdown or {}
    if isinstance(confidence_breakdown, dict):
        threshold_value = confidence_breakdown.get("decision_threshold")
        if isinstance(threshold_value, (int, float)):
            return float(threshold_value)
    model_source = prediction.model_source
    if model_source in _RUNTIME_STACK_SOURCES:
        return float(decision_threshold_for_source("roi_original"))
    return 0.5


def _calibration_band(prediction: PredictionResult, margin: float) -> str:
    if prediction.screening_label == "uncertain":
        return "uncertain"
    if prediction.screening_label == "anemia_likely":
        return "strong_positive" if margin >= 0.18 and prediction.uncertainty < 0.35 else "borderline_positive"
    return "strong_negative" if margin <= -0.18 and prediction.uncertainty < 0.4 else "borderline_negative"


def _build_summary(
    prediction: PredictionResult,
    *,
    threshold: float,
    margin: float,
    used_raw_frame_rescue: bool,
) -> str:
    prefix = (
        "Full-frame rescue was used after the ROI crop looked weak. "
        if used_raw_frame_rescue
        else "Direct ROI analysis was used. "
    )
    if prediction.screening_label == "uncertain":
        return (
            prefix
            + "The signal stayed close to the screening threshold or carried enough uncertainty "
            + "that the safest result remains uncertain."
        )
    direction = "above" if margin >= 0 else "below"
    return (
        prefix
        + f"The final anemia risk sits {abs(margin):.3f} {direction} the operating threshold "
        + f"of {threshold:.3f}, resulting in a {prediction.screening_label.replace('_', ' ')} call."
    )
