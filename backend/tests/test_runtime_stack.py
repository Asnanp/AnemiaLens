from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.runtime_stack import (
    RUNTIME_STACK_VERSION,
    build_runtime_stack_prediction,
    decision_threshold_for_source,
    hb_archive_weight_for_source,
    risk_archive_weight_for_source,
)


def test_decision_threshold_defaults_are_source_aware() -> None:
    assert decision_threshold_for_source("roi_original") == 0.435
    assert decision_threshold_for_source("palpebral") == 0.66
    assert decision_threshold_for_source("forniceal_palpebral") == 0.66


def test_runtime_stack_prediction_keeps_archive_signal_without_secondary_model() -> None:
    result = build_runtime_stack_prediction(
        {
            "anemia_risk": 0.58,
            "predicted_hemoglobin": 11.4,
            "uncertainty": 0.21,
        },
        source_hint="roi_original",
    )

    assert result["anemia_risk"] == 0.58
    assert result["predicted_hemoglobin"] == 11.4
    assert result["uncertainty"] == 0.21
    assert result["decision_threshold"] == 0.435


def test_runtime_stack_blends_archive_and_efficientnet_for_roi() -> None:
    result = build_runtime_stack_prediction(
        {
            "anemia_risk": 0.7,
            "predicted_hemoglobin": 10.8,
            "uncertainty": 0.18,
        },
        efficientnet_prediction={
            "anemia_risk": 0.3,
            "predicted_hemoglobin": 12.0,
            "uncertainty": 0.24,
        },
        source_hint="roi_original",
    )

    assert round(result["anemia_risk"], 4) == 0.636
    assert round(result["predicted_hemoglobin"], 4) == 10.848
    assert round(result["decision_threshold"], 4) == 0.435
    assert round(result["uncertainty"], 4) > 0.18


def test_runtime_stack_weights_are_source_aware() -> None:
    assert risk_archive_weight_for_source("roi_original") == 0.84
    assert risk_archive_weight_for_source("palpebral") == 1.0
    assert hb_archive_weight_for_source("roi_original") == 0.96
    assert hb_archive_weight_for_source("palpebral") == 1.0


def test_runtime_stack_version_is_declared() -> None:
    assert RUNTIME_STACK_VERSION == "archive-evidence-fusion-v4"
