from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas import GuidanceRuntimeStatus, ModelRuntimeStatus
from app.services import runtime_status as runtime_status_module


class _DummyPredictor:
    def runtime_status(self) -> ModelRuntimeStatus:
        return ModelRuntimeStatus(
            primary_model="archive-evidence-fusion-v4",
            deep_stack_loaded=False,
            legacy_loaded=False,
            artifact_ready=True,
            artifact_path="backend/models/archive_screening_model.joblib",
        )


class _DummyGuidance:
    def runtime_status(self) -> GuidanceRuntimeStatus:
        return GuidanceRuntimeStatus(
            active_strategy="fallback",
            mistral_enabled=True,
            client_ready=False,
            api_key_configured=False,
            mistral_model="mistral-small-latest",
            fallback_reason="Fallback active.",
        )


class _DummyV8Predictor:
    def runtime_status(self) -> ModelRuntimeStatus:
        return ModelRuntimeStatus(
            primary_model="archive-fusion-v8-clinical-robust",
            deep_stack_loaded=False,
            legacy_loaded=False,
            artifact_ready=True,
            artifact_path="backend/models/archive-fusion-v8-clinical-robust.joblib",
        )


def test_runtime_status_includes_deployed_metrics(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_status_module,
        "_load_training_report",
        lambda: {
            "primary_model": "archive-evidence-fusion-v4",
            "record_count": 432,
            "metrics": {
                "accuracy": 0.8864,
                "f1": 0.8,
                "split_strategy": "group-shuffle-balance-select: roi_original",
            },
        },
    )
    monkeypatch.setattr(
        runtime_status_module,
        "_load_json_report",
        lambda path: (
            {
                "version": "runtime-risk-calibrator-v1",
                "method": "temperature",
                "selected_thresholds": {"roi_original": 0.58},
                "diagnostics": {
                    "ece_before": 0.121,
                    "ece_after": 0.072,
                    "brier_before": 0.164,
                    "brier_after": 0.133,
                },
            }
            if str(path).endswith("runtime_calibration_report.json")
            else {
                "version": "runtime-screening-refiner-v1",
                "method": "logistic-regression",
                "selected_threshold": 0.53,
                "metrics_after": {
                    "accuracy": 0.8636,
                    "precision": 0.7857,
                    "recall": 0.7857,
                    "f1": 0.7857,
                },
            }
            if str(path).endswith("runtime_refinement_report.json")
            else {
                "evaluation_scope": "deployed_roi_screening",
                "validation_size": 44,
                "metrics": {
                    "accuracy": 0.9091,
                    "precision": 1.0,
                    "recall": 0.7143,
                    "f1": 0.8333,
                },
                "operating_counts": {
                    "blocked_total": 0,
                    "likely_count": 10,
                    "uncertain_count": 3,
                },
            }
        ),
    )

    status = runtime_status_module.build_runtime_status(_DummyPredictor(), _DummyGuidance())

    assert status.model.validation_f1 == 0.8
    assert status.model.deployed_accuracy == 0.9091
    assert status.model.deployed_f1 == 0.8333
    assert status.model.deployed_blocked_total == 0
    assert status.model.deployed_uncertain_count == 3
    assert status.model.runtime_calibration_ready is True
    assert status.model.runtime_calibration_method == "temperature"
    assert status.model.runtime_calibrated_threshold == 0.58
    assert status.model.runtime_calibration_ece_after == 0.072
    assert status.model.runtime_refiner_ready is True
    assert status.model.runtime_refiner_method == "logistic-regression"
    assert status.model.runtime_refined_threshold == 0.53
    assert status.model.runtime_refined_f1 == 0.7857


def test_runtime_status_uses_v8_calibration_report(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_status_module,
        "_load_training_report",
        lambda prefer_training_report=False: {
            "primary_model": "archive-fusion-v8-clinical-robust",
            "record_count": 577,
            "metrics": {
                "accuracy": 0.7895,
                "f1": 0.6998,
                "split_strategy": "group-shuffle-repeat-v8-multiview",
            },
        },
    )

    def _fake_load_json_report(path):
        path_str = str(path)
        if path_str.endswith("runtime_calibration_report_v8.json"):
            return {
                "version": "runtime-risk-calibrator-v8",
                "method": "isotonic-blend",
                "selected_thresholds": {"roi_original": 0.1},
                "diagnostics": {
                    "ece_before": 0.2655,
                    "ece_after": 0.0929,
                    "brier_before": 0.1246,
                    "brier_after": 0.0334,
                },
            }
        if path_str.endswith("runtime_refinement_report.json"):
            return {
                "version": "runtime-screening-refiner-v1",
                "method": "logistic-regression",
                "selected_threshold": 0.31,
                "stage_metrics_after": {
                    "accuracy": 0.9545,
                    "precision": 0.9286,
                    "recall": 0.9286,
                    "f1": 0.9286,
                },
            }
        return {
            "evaluation_scope": "deployed_roi_screening",
            "validation_size": 44,
            "metrics": {
                "accuracy": 0.8864,
                "precision": 0.9091,
                "recall": 0.7143,
                "f1": 0.8,
            },
            "operating_counts": {
                "blocked_total": 6,
                "likely_count": 11,
                "uncertain_count": 1,
            },
        }

    monkeypatch.setattr(runtime_status_module, "_load_json_report", _fake_load_json_report)

    status = runtime_status_module.build_runtime_status(_DummyV8Predictor(), _DummyGuidance())

    assert status.model.primary_model == "archive-fusion-v8-clinical-robust"
    assert status.model.runtime_calibration_ready is True
    assert status.model.runtime_calibration_method == "isotonic-blend"
    assert status.model.runtime_calibrated_threshold == 0.1
    assert status.model.runtime_calibration_ece_after == 0.0929
    assert status.model.runtime_refined_f1 == 0.9286
