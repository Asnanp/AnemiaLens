"""
dynamic_ensemble.py — Quality-aware dynamic ensemble weighting for AnemiaLens.

Replaces static ensemble weights with input-quality-dependent weights that
adapt based on image quality metrics, model agreement, and prediction
confidence.

Key Concepts
------------
1. **Quality-Dependent Weighting**: Models that are more robust to poor
   quality get higher weight when image quality is low.

2. **Disagreement-Adaptive Fusion**: When models disagree significantly,
   the ensemble increases uncertainty and may defer to the more calibrated model.

3. **Source-Aware Calibration**: Different ROI sources (original, palpebral,
   forniceal) have different optimal thresholds and weights.

4. **Confidence-Weighted Blending**: Each model's contribution is weighted
   by its self-reported confidence (1 - uncertainty).

Ensemble Architecture
---------------------
Input: Multiple model predictions + quality metrics
Output: Weighted ensemble prediction with calibrated uncertainty

Weight Components:
- Base weight (source-dependent prior)
- Quality adjustment (quality-dependent multiplier)
- Confidence adjustment (model self-assessment)
- Agreement bonus (consensus reinforcement)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

SourceHint = Literal["roi_original", "palpebral", "forniceal_palpebral"]


@dataclass(frozen=True)
class ModelPrediction:
    """A single model's prediction output."""
    model_name: str
    anemia_risk: float          # [0, 1]
    predicted_hemoglobin: float | None  # g/dL or None
    uncertainty: float          # [0, 1]
    extra: dict = field(default_factory=dict)  # Model-specific extras


@dataclass(frozen=True)
class EnsembleResult:
    """Result of dynamic ensemble fusion."""
    anemia_risk: float          # Fused risk [0, 1]
    predicted_hemoglobin: float | None  # Fused Hb
    uncertainty: float          # Fused uncertainty [0, 1]
    model_weights: dict[str, float]  # Actual weights used per model
    model_contributions: dict[str, float]  # Per-model risk contribution
    agreement_score: float      # [0, 1] — 1 = perfect agreement
    decision_threshold: float
    fusion_method: str
    quality_adjustment_applied: bool
    diagnostics: dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Default source-specific priors
# ─────────────────────────────────────────────────────────────────────────────

# Base weights for different model types by source
# Structure: {source: {model_type: base_weight}}
DEFAULT_SOURCE_WEIGHTS: dict[SourceHint, dict[str, float]] = {
    "roi_original": {
        "archive": 0.55,
        "deep_learning": 0.35,
        "heuristic": 0.10,
    },
    "palpebral": {
        "archive": 0.70,
        "deep_learning": 0.25,
        "heuristic": 0.05,
    },
    "forniceal_palpebral": {
        "archive": 0.70,
        "deep_learning": 0.25,
        "heuristic": 0.05,
    },
}

# Decision thresholds by source
DEFAULT_THRESHOLDS: dict[SourceHint, float] = {
    "roi_original": 0.495,
    "palpebral": 0.65,
    "forniceal_palpebral": 0.65,
}

# Quality robustness scores per model type
# How well each model type handles poor quality images
QUALITY_ROBUSTNESS: dict[str, float] = {
    "archive": 0.85,       # Feature-based models are more robust to noise
    "deep_learning": 0.60,  # DL models degrade faster with poor quality
    "heuristic": 0.70,      # Heuristics are moderately robust
}


class DynamicEnsembleFuser:
    """
    Quality-aware dynamic ensemble fuser.

    Usage
    -----
    fuser = DynamicEnsembleFuser()
    result = fuser.fuse(
        predictions=[archive_pred, dl_pred],
        source_hint="roi_original",
        quality_metrics={"blur": 120.0, "brightness": 0.35, ...},
    )
    """

    def __init__(
        self,
        source_weights: dict[SourceHint, dict[str, float]] | None = None,
        thresholds: dict[SourceHint, float] | None = None,
        quality_robustness: dict[str, float] | None = None,
    ) -> None:
        self.source_weights = source_weights or DEFAULT_SOURCE_WEIGHTS
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        self.quality_robustness = quality_robustness or QUALITY_ROBUSTNESS

    def fuse(
        self,
        predictions: list[ModelPrediction],
        source_hint: SourceHint = "roi_original",
        quality_metrics: dict[str, float] | None = None,
        roi_confidence: float | None = None,
    ) -> EnsembleResult:
        """
        Fuse multiple model predictions with quality-aware dynamic weighting.

        Parameters
        ----------
        predictions : List of model predictions
        source_hint : ROI source type
        quality_metrics : Pre-inference quality metrics
        roi_confidence : ROI extraction confidence score

        Returns
        -------
        EnsembleResult with fused prediction and diagnostics
        """
        if not predictions:
            return EnsembleResult(
                anemia_risk=0.5,
                predicted_hemoglobin=None,
                uncertainty=1.0,
                model_weights={},
                model_contributions={},
                agreement_score=0.0,
                decision_threshold=self.thresholds.get(source_hint, 0.5),
                fusion_method="empty",
                quality_adjustment_applied=False,
                diagnostics={"error": "No predictions provided"},
            )

        if len(predictions) == 1:
            pred = predictions[0]
            return EnsembleResult(
                anemia_risk=float(np.clip(pred.anemia_risk, 0.0, 1.0)),
                predicted_hemoglobin=pred.predicted_hemoglobin,
                uncertainty=float(np.clip(pred.uncertainty, 0.0, 1.0)),
                model_weights={pred.model_name: 1.0},
                model_contributions={pred.model_name: pred.anemia_risk},
                agreement_score=1.0,
                decision_threshold=self.thresholds.get(source_hint, 0.5),
                fusion_method="single_model",
                quality_adjustment_applied=False,
            )

        # ── Step 1: Compute base weights from source ────────────────────────
        base_weights = self._get_base_weights(source_hint, predictions)

        # ── Step 2: Apply quality adjustments ───────────────────────────────
        quality_adjusted = False
        if quality_metrics is not None:
            quality_score = self._compute_quality_score(quality_metrics)
            base_weights = self._apply_quality_adjustment(
                base_weights, quality_score, predictions
            )
            quality_adjusted = True

        # ── Step 3: Apply confidence weighting ─────────────────────────────
        weights = self._apply_confidence_weighting(base_weights, predictions)

        # ── Step 4: Compute agreement score ─────────────────────────────────
        agreement = self._compute_agreement(predictions, weights)

        # ── Step 5: Apply agreement bonus/penalty ───────────────────────────
        weights = self._apply_agreement_adjustment(weights, agreement, predictions)

        # Normalize final weights
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        else:
            weights = {k: 1.0 / len(weights) for k in weights}

        # ── Step 6: Compute fused prediction ────────────────────────────────
        fused_risk = sum(
            weights[pred.model_name] * pred.anemia_risk
            for pred in predictions
        )

        # Hemoglobin: weighted average (only from models that provide it)
        hb_predictions = [
            (pred.model_name, pred.predicted_hemoglobin)
            for pred in predictions
            if pred.predicted_hemoglobin is not None
        ]
        if hb_predictions:
            hb_total_weight = sum(weights[name] for name, _ in hb_predictions)
            if hb_total_weight > 0:
                fused_hb = sum(
                    weights[name] * hb
                    for name, hb in hb_predictions
                ) / hb_total_weight
            else:
                fused_hb = None
        else:
            fused_hb = None

        # ── Step 7: Compute fused uncertainty ───────────────────────────────
        fused_uncertainty = self._compute_fused_uncertainty(
            predictions, weights, agreement
        )

        # ── Step 8: Model contributions ─────────────────────────────────────
        contributions = {
            pred.model_name: weights[pred.model_name] * pred.anemia_risk
            for pred in predictions
        }

        decision_threshold = self.thresholds.get(source_hint, 0.5)

        return EnsembleResult(
            anemia_risk=float(np.clip(fused_risk, 0.0, 1.0)),
            predicted_hemoglobin=fused_hb,
            uncertainty=float(np.clip(fused_uncertainty, 0.0, 1.0)),
            model_weights={k: round(v, 4) for k, v in weights.items()},
            model_contributions={k: round(v, 4) for k, v in contributions.items()},
            agreement_score=round(agreement, 4),
            decision_threshold=decision_threshold,
            fusion_method="quality_aware_dynamic",
            quality_adjustment_applied=quality_adjusted,
            diagnostics={
                "quality_score": (
                    round(self._compute_quality_score(quality_metrics), 3)
                    if quality_metrics else None
                ),
                "n_models": len(predictions),
                "source_hint": source_hint,
            },
        )

    # ──────────────────────────────────────────────────────────────────────
    # Private fusion methods
    # ──────────────────────────────────────────────────────────────────────

    def _get_base_weights(
        self,
        source_hint: SourceHint,
        predictions: list[ModelPrediction],
    ) -> dict[str, float]:
        """Get base weights from source-specific priors."""
        source_priors = self.source_weights.get(source_hint, self.source_weights["roi_original"])

        weights = {}
        for pred in predictions:
            model_type = self._classify_model_type(pred.model_name)
            weights[pred.model_name] = source_priors.get(model_type, 0.33)

        # Normalize
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        return weights

    def _apply_quality_adjustment(
        self,
        weights: dict[str, float],
        quality_score: float,
        predictions: list[ModelPrediction],
    ) -> dict[str, float]:
        """
        Adjust weights based on image quality.

        When quality is low, shift weight toward more robust models.
        """
        adjusted = {}
        for pred in predictions:
            model_type = self._classify_model_type(pred.model_name)
            robustness = self.quality_robustness.get(model_type, 0.5)

            # Low quality → boost robust models, reduce fragile ones
            # quality_score in [0, 1]; robustness in [0, 1]
            # When quality=0.3, robustness=0.85 → multiplier = 1 + (0.85-0.5)*(1-0.3) = 1.245
            # When quality=0.3, robustness=0.60 → multiplier = 1 + (0.60-0.5)*(1-0.3) = 1.07
            quality_delta = 1.0 - quality_score
            multiplier = 1.0 + (robustness - 0.5) * quality_delta * 0.8

            adjusted[pred.model_name] = weights[pred.model_name] * multiplier

        # Normalize
        total = sum(adjusted.values())
        if total > 0:
            adjusted = {k: v / total for k, v in adjusted.items()}
        return adjusted

    def _apply_confidence_weighting(
        self,
        weights: dict[str, float],
        predictions: list[ModelPrediction],
    ) -> dict[str, float]:
        """
        Weight each model by its self-reported confidence.

        confidence = 1 - uncertainty
        Final weight = base_weight * confidence
        """
        adjusted = {}
        for pred in predictions:
            confidence = 1.0 - pred.uncertainty
            adjusted[pred.model_name] = weights[pred.model_name] * max(confidence, 0.1)

        # Normalize
        total = sum(adjusted.values())
        if total > 0:
            adjusted = {k: v / total for k, v in adjusted.items()}
        return adjusted

    def _compute_agreement(
        self,
        predictions: list[ModelPrediction],
        weights: dict[str, float],
    ) -> float:
        """
        Compute weighted agreement score [0, 1].

        1.0 = all models agree perfectly
        0.0 = maximum disagreement
        """
        risks = np.array([p.anemia_risk for p in predictions])
        w = np.array([weights.get(p.model_name, 0.33) for p in predictions])
        w = w / w.sum()

        weighted_mean = float(np.average(risks, weights=w))
        weighted_std = float(np.sqrt(np.average((risks - weighted_mean) ** 2, weights=w)))

        # Convert std to agreement: std=0 → agreement=1, std=0.5 → agreement=0
        agreement = max(0.0, 1.0 - weighted_std * 3.0)
        return float(np.clip(agreement, 0.0, 1.0))

    def _apply_agreement_adjustment(
        self,
        weights: dict[str, float],
        agreement: float,
        predictions: list[ModelPrediction],
    ) -> dict[str, float]:
        """
        When models disagree, reduce overall confidence (via uncertainty later)
        but maintain weights. When they agree, slightly reinforce.
        """
        if agreement > 0.8:
            # High agreement: slight reinforcement proportional to agreement
            adjusted = {
                name: w * (1.0 + (agreement - 0.8) * 0.25)
                for name, w in weights.items()
            }
            total = sum(adjusted.values())
            if total > 0:
                adjusted = {k: v / total for k, v in adjusted.items()}
            return adjusted
        return weights

    def _compute_fused_uncertainty(
        self,
        predictions: list[ModelPrediction],
        weights: dict[str, float],
        agreement: float,
    ) -> float:
        """
        Compute fused uncertainty incorporating:
        - Individual model uncertainties (weighted)
        - Model disagreement penalty
        - Agreement bonus
        """
        # Base: weighted average of individual uncertainties
        base_uncertainty = sum(
            weights.get(p.model_name, 0.33) * p.uncertainty
            for p in predictions
        )

        # Disagreement penalty
        disagreement_penalty = (1.0 - agreement) * 0.15

        # Agreement bonus (reduce uncertainty when models agree)
        agreement_bonus = agreement * 0.05

        fused = base_uncertainty + disagreement_penalty - agreement_bonus
        return float(np.clip(fused, 0.04, 0.95))

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _classify_model_type(model_name: str) -> str:
        """Classify a model name into its type category."""
        name_lower = model_name.lower()
        if "archive" in name_lower or "fusion" in name_lower:
            return "archive"
        if "efficientnet" in name_lower or "deep" in name_lower or "dl" in name_lower:
            return "deep_learning"
        return "heuristic"

    @staticmethod
    def _compute_quality_score(quality_metrics: dict[str, float]) -> float:
        """
        Compute composite quality score from metrics.

        Metrics expected: blur_score, brightness, contrast, noise_level, etc.
        """
        scores = []
        weights = []

        # Blur score (normalized to [0, 1], higher = better)
        if "blur_score" in quality_metrics:
            blur = quality_metrics["blur_score"]
            scores.append(min(blur / 200.0, 1.0))
            weights.append(0.30)

        # Brightness (0.35 is ideal)
        if "brightness_raw" in quality_metrics or "brightness" in quality_metrics:
            bright = quality_metrics.get("brightness_raw", quality_metrics.get("brightness", 0.35))
            # Normalize: if raw [0, 255], convert to [0, 1]
            if bright > 1.0:
                bright = bright / 255.0
            brightness_score = 1.0 - abs(bright - 0.35) / 0.35
            scores.append(max(0.0, brightness_score))
            weights.append(0.20)

        # Contrast
        if "contrast_raw" in quality_metrics or "contrast" in quality_metrics:
            contrast = quality_metrics.get("contrast_raw", quality_metrics.get("contrast", 0.15))
            if contrast > 1.0:
                contrast = contrast / 255.0
            scores.append(min(contrast / 0.25, 1.0))
            weights.append(0.15)

        # Noise (lower is better)
        if "noise_level" in quality_metrics:
            noise = quality_metrics["noise_level"]
            scores.append(max(0.0, 1.0 - noise / 40.0))
            weights.append(0.15)

        # Overexposure (lower is better)
        if "overexposed_fraction" in quality_metrics:
            overexp = quality_metrics["overexposed_fraction"]
            scores.append(max(0.0, 1.0 - overexp / 0.15))
            weights.append(0.10)

        # Saturation
        if "saturation" in quality_metrics:
            sat = quality_metrics["saturation"]
            scores.append(min(sat / 0.15, 1.0))
            weights.append(0.10)

        if not scores:
            return 0.5  # Default neutral score

        w = np.array(weights)
        w = w / w.sum()
        return float(np.clip(np.average(scores, weights=w), 0.0, 1.0))


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience
# ─────────────────────────────────────────────────────────────────────────────

_default_fuser: DynamicEnsembleFuser | None = None


def get_ensemble_fuser() -> DynamicEnsembleFuser:
    """Get or create the singleton ensemble fuser."""
    global _default_fuser
    if _default_fuser is None:
        _default_fuser = DynamicEnsembleFuser()
    return _default_fuser


def fuse_predictions(
    predictions: list[ModelPrediction],
    source_hint: SourceHint = "roi_original",
    quality_metrics: dict[str, float] | None = None,
) -> EnsembleResult:
    """Convenience function for dynamic ensemble fusion."""
    return get_ensemble_fuser().fuse(predictions, source_hint, quality_metrics)
