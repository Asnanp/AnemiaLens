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
        efficientnet_risk = float(efficientnet_prediction["anemia_risk"])
        efficientnet_hb = float(efficientnet_prediction["predicted_hemoglobin"])
        efficientnet_uncertainty = float(efficientnet_prediction.get("uncertainty", 0.35))

        # Confidence-weighted ensemble: lower uncertainty → higher weight
        archive_conf = clamp(1.0 - archive_uncertainty)
        efficientnet_conf = clamp(1.0 - efficientnet_uncertainty)
        total_conf = archive_conf + efficientnet_conf + 1e-9

        # Apply source-specific floor weight for archive (it has calibrated features)
        source_floor = risk_archive_weight_for_source(source_hint)
        raw_archive_w = archive_conf / total_conf
        # Blend floor weight with confidence-derived weight
        archive_w = clamp(0.5 * source_floor + 0.5 * raw_archive_w, 0.25, 0.80)
        efficientnet_w = 1.0 - archive_w

        disagreement = abs(archive_risk - efficientnet_risk)
        hemoglobin_gap = abs(archive_hb - efficientnet_hb)

        # Agreement bonus: both models agree on direction → reduce uncertainty
        agreement_bonus = 0.0
        if (archive_risk > 0.5) == (efficientnet_risk > 0.5):
            agreement_bonus = 0.04 + disagreement * 0.06

        risk = (archive_w * archive_risk) + (efficientnet_w * efficientnet_risk)
        hb_archive_w = hb_archive_weight_for_source(source_hint)
        predicted_hemoglobin = (hb_archive_w * archive_hb) + ((1.0 - hb_archive_w) * efficientnet_hb)
        uncertainty = clamp(
            (archive_w * archive_uncertainty)
            + (efficientnet_w * efficientnet_uncertainty)
            + (disagreement * 0.08)
            + (min(hemoglobin_gap / 12.0, 1.0) * 0.025)
            - agreement_bonus,
            0.04,
            0.92,
        )

    return {
        "anemia_risk": clamp(risk, 0.0, 1.0),
        "predicted_hemoglobin": predicted_hemoglobin,
        "uncertainty": clamp(uncertainty, 0.04, 0.95),
        "decision_threshold": decision_threshold_for_source(source_hint),
    }
