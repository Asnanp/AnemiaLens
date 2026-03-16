from __future__ import annotations

import json

from app.config import (
    DEFAULT_DEPLOYED_SCREENING_REPORT_PATH,
    DEFAULT_RUNTIME_STACK_REPORT_PATH,
    DEFAULT_TRAINING_REPORT_PATH,
)
from app.schemas import ModelRuntimeStatus, RuntimeStatusResponse
from app.services.guidance import GuidanceService
from app.services.prediction import ScreeningPredictor


def build_runtime_status(
    predictor: ScreeningPredictor, guidance_service: GuidanceService
) -> RuntimeStatusResponse:
    model_status = predictor.runtime_status()
    report = _load_training_report()
    deployed_report = _load_json_report(DEFAULT_DEPLOYED_SCREENING_REPORT_PATH)

    if report is not None:
        metrics = report.get("metrics", {})
        model_status = model_status.model_copy(
            update={
                "primary_model": report.get("primary_model", model_status.primary_model),
                "record_count": report.get("record_count"),
                "validation_accuracy": metrics.get("accuracy"),
                "validation_f1": metrics.get("f1"),
                "split_strategy": metrics.get("split_strategy"),
            }
        )

    if deployed_report is not None:
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

    return RuntimeStatusResponse(
        api_status="ok",
        guidance=guidance_service.runtime_status(),
        model=model_status,
    )


def _load_training_report() -> dict[str, object] | None:
    for path in (DEFAULT_RUNTIME_STACK_REPORT_PATH, DEFAULT_TRAINING_REPORT_PATH):
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
