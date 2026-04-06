from __future__ import annotations

import json

from app.config import (
    DEFAULT_DEPLOYED_SCREENING_REPORT_PATH,
    DEFAULT_RUNTIME_CALIBRATION_REPORT_PATH,
    DEFAULT_RUNTIME_REFINEMENT_REPORT_PATH,
    DEFAULT_RUNTIME_STACK_REPORT_PATH,
    DEFAULT_TRAINING_REPORT_PATH,
    DEFAULT_ULTIMATE_REFINEMENT_REPORT_PATH,
    DEFAULT_V8_RUNTIME_CALIBRATION_REPORT_PATH,
)
from app.schemas import RuntimeStatusResponse
from app.services.guidance import GuidanceService
from app.services.prediction import ScreeningPredictor


def build_runtime_status(
    predictor: ScreeningPredictor, guidance_service: GuidanceService
) -> RuntimeStatusResponse:
    model_status = predictor.runtime_status()
    primary_model = str(model_status.primary_model)
    is_v8_archive = primary_model.startswith("archive-fusion-v8-clinical-robust")
    is_ultimate_archive = primary_model.startswith("archive-fusion-v7-ultimate-clinical")

    try:
        report = _load_training_report(
            prefer_training_report=is_v8_archive or is_ultimate_archive
        )
    except TypeError:
        report = _load_training_report()
    deployed_report = _load_json_report(DEFAULT_DEPLOYED_SCREENING_REPORT_PATH)
    calibration_report = (
        None
        if is_ultimate_archive
        else _load_json_report(
            DEFAULT_V8_RUNTIME_CALIBRATION_REPORT_PATH
            if is_v8_archive
            else DEFAULT_RUNTIME_CALIBRATION_REPORT_PATH
        )
    )
    refinement_report = (
        _load_json_report(
            DEFAULT_ULTIMATE_REFINEMENT_REPORT_PATH
            if is_ultimate_archive
            else DEFAULT_RUNTIME_REFINEMENT_REPORT_PATH
        )
    )

    report_primary_model = str(report.get("primary_model", "")).strip() if report is not None else ""
    should_apply_report = bool(
        report is not None
        and report_primary_model
        and (
            report_primary_model == primary_model
            or (
                not is_v8_archive
                and not is_ultimate_archive
                and not primary_model.startswith("missing-model")
            )
        )
    )

    if should_apply_report and report is not None:
        metrics = report.get("metrics", {})
        primary_model = (
            model_status.primary_model
            if is_ultimate_archive or is_v8_archive
            else report_primary_model
        )
        model_status = model_status.model_copy(
            update={
                "primary_model": primary_model,
                "record_count": report.get("record_count"),
                "validation_accuracy": metrics.get("accuracy"),
                "validation_f1": metrics.get("f1"),
                "split_strategy": metrics.get("split_strategy"),
            }
        )
    elif is_ultimate_archive and predictor.archive_model is not None:
        test_metrics = predictor.archive_model.get("test_metrics", {})
        training_results = predictor.archive_model.get("training_results", {})
        cv_results = training_results.get("cv_results", {})
        robustness = predictor.archive_model.get("robustness_results", {})
        model_status = model_status.model_copy(
            update={
                "validation_accuracy": test_metrics.get("auc"),
                "validation_f1": cv_results.get("calibrated_clf_auc"),
                "deployed_precision": test_metrics.get("precision"),
                "deployed_recall": test_metrics.get("recall"),
                "deployed_accuracy": test_metrics.get("auc"),
                "deployed_scope": "embedded_v7_test_metrics",
                "runtime_refined_accuracy": robustness.get("robust_auc"),
            }
        )

    if deployed_report is not None and not (is_v8_archive or is_ultimate_archive):
        metrics = deployed_report.get("metrics", {})
        counts = deployed_report.get("operating_counts", {})
        model_status = model_status.model_copy(
            update={
                "deployed_scope": deployed_report.get("evaluation_scope"),
                "deployed_validation_size": deployed_report.get("validation_size"),
                "deployed_accuracy": metrics.get("accuracy"),
                "deployed_precision": metrics.get("precision"),
                "deployed_recall": metrics.get("recall"),
                "deployed_f1": metrics.get("f1"),
                "deployed_blocked_total": counts.get("blocked_total"),
                "deployed_likely_count": counts.get("likely_count"),
                "deployed_uncertain_count": counts.get("uncertain_count"),
            }
        )

    if calibration_report is not None:
        diagnostics = calibration_report.get("diagnostics", {})
        selected_thresholds = calibration_report.get("selected_thresholds", {})
        model_status = model_status.model_copy(
            update={
                "runtime_calibration_ready": True,
                "runtime_calibration_method": calibration_report.get("method"),
                "runtime_calibrated_threshold": selected_thresholds.get("roi_original"),
                "runtime_calibration_ece_before": diagnostics.get("ece_before"),
                "runtime_calibration_ece_after": diagnostics.get("ece_after"),
                "runtime_calibration_brier_before": diagnostics.get("brier_before"),
                "runtime_calibration_brier_after": diagnostics.get("brier_after"),
            }
        )

    if refinement_report is not None:
        metrics = (
            refinement_report.get("stage_metrics_after", {})
            if is_v8_archive
            else refinement_report.get("metrics_after", {})
        )
        model_status = model_status.model_copy(
            update={
                "runtime_refiner_ready": True,
                "runtime_refiner_method": refinement_report.get("method"),
                "runtime_refined_threshold": refinement_report.get("selected_threshold"),
                "runtime_refined_accuracy": metrics.get("accuracy"),
                "runtime_refined_precision": metrics.get("precision"),
                "runtime_refined_recall": metrics.get("recall"),
                "runtime_refined_f1": metrics.get("f1"),
            }
        )

    return RuntimeStatusResponse(
        api_status="ok",
        guidance=guidance_service.runtime_status(),
        model=model_status,
    )


def _load_training_report(*, prefer_training_report: bool = False) -> dict[str, object] | None:
    paths = (
        (DEFAULT_TRAINING_REPORT_PATH, DEFAULT_RUNTIME_STACK_REPORT_PATH)
        if prefer_training_report
        else (DEFAULT_RUNTIME_STACK_REPORT_PATH, DEFAULT_TRAINING_REPORT_PATH)
    )
    for path in paths:
        report = _load_json_report(path)
        if report is not None:
            return report
    return None


def _load_json_report(path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None
