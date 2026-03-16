from __future__ import annotations

from typing import Literal

from app.ml.archive_model import clamp


RUNTIME_STACK_VERSION = "archive-evidence-fusion-v4"
SourceHint = Literal["roi_original", "palpebral", "forniceal_palpebral"]

DEFAULT_SOURCE_THRESHOLDS: dict[SourceHint, float] = {
    "roi_original": 0.40,
    "palpebral": 0.60,
    "forniceal_palpebral": 0.60,
}

DEFAULT_RISK_ARCHIVE_WEIGHTS: dict[SourceHint, float] = {
    "roi_original": 0.55,
    "palpebral": 1.0,
    "forniceal_palpebral": 1.0,
}

DEFAULT_HB_ARCHIVE_WEIGHTS: dict[SourceHint, float] = {
    "roi_original": 0.70,
    "palpebral": 1.0,
    "forniceal_palpebral": 1.0,
}


def decision_threshold_for_source(source_hint: SourceHint = "roi_original") -> float:
    return float(DEFAULT_SOURCE_THRESHOLDS.get(source_hint, DEFAULT_SOURCE_THRESHOLDS["roi_original"]))


def risk_archive_weight_for_source(source_hint: SourceHint = "roi_original") -> float:
    return float(DEFAULT_RISK_ARCHIVE_WEIGHTS.get(source_hint, DEFAULT_RISK_ARCHIVE_WEIGHTS["roi_original"]))


def hb_archive_weight_for_source(source_hint: SourceHint = "roi_original") -> float:
    return float(DEFAULT_HB_ARCHIVE_WEIGHTS.get(source_hint, DEFAULT_HB_ARCHIVE_WEIGHTS["roi_original"]))


def build_runtime_stack_prediction(
    archive_prediction: dict[str, float],
    *,
    efficientnet_prediction: dict[str, float] | None = None,
    source_hint: SourceHint = "roi_original",
) -> dict[str, float]:
    archive_risk = float(archive_prediction["anemia_risk"])
    archive_hb = float(archive_prediction["predicted_hemoglobin"])
    archive_uncertainty = float(archive_prediction["uncertainty"])

    risk = archive_risk
    predicted_hemoglobin = archive_hb
    uncertainty = archive_uncertainty

    if efficientnet_prediction is not None:
        risk_weight = risk_archive_weight_for_source(source_hint)
        hb_weight = hb_archive_weight_for_source(source_hint)
        efficientnet_risk = float(efficientnet_prediction["anemia_risk"])
        efficientnet_hb = float(efficientnet_prediction["predicted_hemoglobin"])
        efficientnet_uncertainty = float(efficientnet_prediction.get("uncertainty", 0.35))
        disagreement = abs(archive_risk - efficientnet_risk)
        hemoglobin_gap = abs(archive_hb - efficientnet_hb)

        # When both models agree on direction, boost confidence
        agreement_bonus = 0.0
        if (archive_risk > 0.5) == (efficientnet_risk > 0.5):
            agreement_bonus = disagreement * 0.08  # small reduction in uncertainty

        risk = (risk_weight * archive_risk) + ((1.0 - risk_weight) * efficientnet_risk)
        predicted_hemoglobin = (hb_weight * archive_hb) + ((1.0 - hb_weight) * efficientnet_hb)
        uncertainty = clamp(
            (risk_weight * archive_uncertainty)
            + ((1.0 - risk_weight) * efficientnet_uncertainty)
            + (disagreement * 0.10)
            + (min(hemoglobin_gap / 10.0, 1.0) * 0.03)
            - agreement_bonus,
            0.05,
            0.92,
        )

    return {
        "anemia_risk": clamp(risk, 0.0, 1.0),
        "predicted_hemoglobin": predicted_hemoglobin,
        "uncertainty": clamp(uncertainty, 0.05, 0.95),
        "decision_threshold": decision_threshold_for_source(source_hint),
    }
