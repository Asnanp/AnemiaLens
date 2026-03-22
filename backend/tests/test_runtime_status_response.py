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
        lambda path: {
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
        },
    )

    status = runtime_status_module.build_runtime_status(_DummyPredictor(), _DummyGuidance())

    assert status.model.validation_f1 == 0.8
    assert status.model.deployed_accuracy == 0.9091
    assert status.model.deployed_f1 == 0.8333
    assert status.model.deployed_blocked_total == 0
    assert status.model.deployed_uncertain_count == 3
