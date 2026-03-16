from __future__ import annotations

from datetime import datetime

from app.schemas import AnalysisMeta, DecisionAudit, GuidanceResult, QualityAssessment


def build_analysis_meta(
    *,
    request_id: str,
    api_version: str,
    processing_time_ms: float,
    quality: QualityAssessment,
    decision_audit: DecisionAudit,
    guidance: GuidanceResult,
    used_raw_frame_rescue: bool,
) -> AnalysisMeta:
    safety_layers = ["image_quality_gate"]

    if quality.passed:
        safety_layers.extend(["calibrated_prediction", "uncertainty_scoring"])
    if used_raw_frame_rescue:
        safety_layers.append("raw_frame_rescue_review")
    if quality.warning_issues:
        safety_layers.append("quality_warning_review")

    safety_layers.extend(["symptom_fusion", "triage_banding", "non_diagnostic_guidance"])

    return AnalysisMeta(
        request_id=request_id,
        generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        api_version=api_version,
        processing_time_ms=round(processing_time_ms, 1),
        quality_gate_passed=quality.passed,
        processing_path=decision_audit.processing_path,
        guidance_source=guidance.source,
        used_raw_frame_rescue=used_raw_frame_rescue,
        safety_layers=safety_layers,
    )
