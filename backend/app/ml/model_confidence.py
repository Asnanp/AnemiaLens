"""
model_confidence.py — Composite confidence scoring for AnemiaLens predictions.

Computes a multi-dimensional confidence score that reflects:
1. Image quality confidence (from pre-inference quality gate)
2. Model stability confidence (from ensemble disagreement / MC dropout)
3. Threshold proximity confidence (how close to the decision boundary)
4. ROI confidence (quality of the region extraction)
5. Feature-space density confidence (how typical is this input)

The composite score is used to:
- Gate automated decisions
- Trigger human review
- Provide transparency to users
- Select fallback strategies
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from app.schemas.quality import QualityAssessment


@dataclass(frozen=True)
class ConfidenceComponents:
    """Decomposed confidence components for a prediction."""
    # Image quality confidence [0, 1]
    image_quality: float = 0.5
    # Model stability / internal consistency [0, 1]
    model_stability: float = 0.5
    # Threshold proximity confidence [0, 1]
    threshold_stability: float = 0.5
    # ROI extraction quality [0, 1]
    roi_confidence: float = 0.5
    # Feature-space typicality [0, 1]
    feature_typicality: float = 0.5
    # Calibration quality [0, 1]
    calibration_quality: float = 0.5

    # Free-form diagnostics
    diagnostics: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ConfidenceResult:
    """Complete confidence assessment for a prediction."""
    composite_confidence: float     # Overall confidence [0, 1]
    components: ConfidenceComponents
    confidence_tier: str            # "high", "medium", "low", "very_low"
    recommendation: str             # Actionable recommendation
    review_required: bool           # Whether human review is needed
    can_auto_act: bool              # Whether automated action is safe
    explanation: str                # Human-readable explanation


class ModelConfidenceScorer:
    """
    Multi-dimensional confidence scorer for AnemiaLens predictions.

    Usage
    -----
    scorer = ModelConfidenceScorer()
    result = scorer.compute(
        anemia_risk=0.72,
        uncertainty=0.18,
        decision_threshold=0.495,
        quality_metrics={"blur_score": 120.0, ...},
        roi_confidence=0.85,
        ensemble_agreement=0.82,
    )
    # result.confidence_tier → "high"
    # result.composite_confidence → 0.78
    """

    # Tier thresholds
    TIER_HIGH = 0.75
    TIER_MEDIUM = 0.55
    TIER_LOW = 0.35

    # Weights for composite confidence
    WEIGHTS = {
        "image_quality": 0.20,
        "model_stability": 0.25,
        "threshold_stability": 0.15,
        "roi_confidence": 0.15,
        "feature_typicality": 0.15,
        "calibration_quality": 0.10,
    }

    def compute(
        self,
        anemia_risk: float,
        uncertainty: float,
        decision_threshold: float = 0.5,
        quality_metrics: dict[str, float] | None = None,
        roi_confidence: float | None = None,
        ensemble_agreement: float | None = None,
        feature_vector: np.ndarray | None = None,
        feature_stats: dict[str, dict[str, float]] | None = None,
        calibration_score: float | None = None,
    ) -> ConfidenceResult:
        """
        Compute comprehensive confidence for a prediction.

        Parameters
        ----------
        anemia_risk : Model's anemia risk prediction [0, 1]
        uncertainty : Model's self-reported uncertainty [0, 1]
        decision_threshold : Classification threshold used
        quality_metrics : Pre-inference quality metrics
        roi_confidence : ROI extraction confidence
        ensemble_agreement : Ensemble agreement score [0, 1]
        feature_vector : Raw feature vector for typicality check
        feature_stats : Training set feature statistics (mean, std per feature)
        calibration_score : Model calibration quality metric

        Returns
        -------
        ConfidenceResult
        """
        # ── 1. Image quality confidence ─────────────────────────────────────
        image_quality = self._compute_image_quality_confidence(quality_metrics)

        # ── 2. Model stability confidence ───────────────────────────────────
        model_stability = self._compute_model_stability(
            uncertainty, ensemble_agreement
        )

        # ── 3. Threshold proximity confidence ───────────────────────────────
        threshold_stability = self._compute_threshold_stability(
            anemia_risk, decision_threshold
        )

        # ── 4. ROI confidence ───────────────────────────────────────────────
        roi_conf = roi_confidence if roi_confidence is not None else 0.5

        # ── 5. Feature typicality ───────────────────────────────────────────
        feature_typicality = self._compute_feature_typicality(
            feature_vector, feature_stats
        )

        # ── 6. Calibration quality ──────────────────────────────────────────
        calibration_quality = calibration_score if calibration_score is not None else 0.7

        components = ConfidenceComponents(
            image_quality=image_quality,
            model_stability=model_stability,
            threshold_stability=threshold_stability,
            roi_confidence=roi_conf,
            feature_typicality=feature_typicality,
            calibration_quality=calibration_quality,
            diagnostics={
                "anemia_risk": round(anemia_risk, 4),
                "uncertainty": round(uncertainty, 4),
                "distance_from_threshold": round(
                    abs(anemia_risk - decision_threshold), 4
                ),
            },
        )

        # ── Composite confidence ────────────────────────────────────────────
        composite = self._compute_composite(components)

        # ── Tier classification ─────────────────────────────────────────────
        tier = self._classify_tier(composite)

        # ── Recommendation ──────────────────────────────────────────────────
        recommendation = self._get_recommendation(tier, components)
        review_required = tier in ("low", "very_low")
        can_auto_act = tier == "high"
        explanation = self._build_explanation(tier, components, anemia_risk)

        return ConfidenceResult(
            composite_confidence=round(composite, 3),
            components=components,
            confidence_tier=tier,
            recommendation=recommendation,
            review_required=review_required,
            can_auto_act=can_auto_act,
            explanation=explanation,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Component computation methods
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_image_quality_confidence(
        quality_metrics: dict[str, float] | None,
    ) -> float:
        """Compute confidence from image quality metrics."""
        if not quality_metrics:
            return 0.5  # Neutral when no quality info

        scores = []

        # Blur
        if "blur_score" in quality_metrics:
            blur = quality_metrics["blur_score"]
            scores.append(min(blur / 200.0, 1.0))

        # Brightness
        bright = quality_metrics.get("brightness_raw", quality_metrics.get("brightness"))
        if bright is not None:
            if bright > 1.0:
                bright = bright / 255.0
            scores.append(max(0.0, 1.0 - abs(bright - 0.35) / 0.35))

        # Contrast
        contrast = quality_metrics.get("contrast_raw", quality_metrics.get("contrast"))
        if contrast is not None:
            if contrast > 1.0:
                contrast = contrast / 255.0
            scores.append(min(contrast / 0.25, 1.0))

        # Noise
        if "noise_level" in quality_metrics:
            noise = quality_metrics["noise_level"]
            scores.append(max(0.0, 1.0 - noise / 40.0))

        # Overall quality score if available
        if "overall_quality_score" in quality_metrics:
            scores.append(quality_metrics["overall_quality_score"])

        if not scores:
            return 0.5

        return float(np.clip(np.mean(scores), 0.0, 1.0))

    @staticmethod
    def _compute_model_stability(
        uncertainty: float,
        ensemble_agreement: float | None = None,
    ) -> float:
        """Compute model stability from uncertainty and agreement."""
        # Base: inverse of uncertainty
        base = 1.0 - uncertainty

        if ensemble_agreement is not None:
            # Blend uncertainty and agreement
            stability = base * 0.6 + ensemble_agreement * 0.4
        else:
            stability = base

        return float(np.clip(stability, 0.0, 1.0))

    @staticmethod
    def _compute_threshold_stability(
        anemia_risk: float,
        decision_threshold: float,
    ) -> float:
        """
        Compute confidence based on distance from decision threshold.

        Far from threshold = high confidence in classification.
        Near threshold = borderline case, low confidence.
        """
        distance = abs(anemia_risk - decision_threshold)

        # Map distance to confidence:
        # distance=0 → confidence=0.2 (right on boundary)
        # distance=0.1 → confidence=0.5
        # distance=0.3+ → confidence=0.95
        if distance >= 0.3:
            return 0.95
        confidence = 0.2 + (distance / 0.3) * 0.75
        return float(np.clip(confidence, 0.2, 0.95))

    @staticmethod
    def _compute_feature_typicality(
        feature_vector: np.ndarray | None,
        feature_stats: dict[str, dict[str, float]] | None,
    ) -> float:
        """
        Compute how typical the input features are relative to training data.

        Uses Mahalanobis-like distance (per-feature z-score average).
        """
        if feature_vector is None or feature_stats is None:
            return 0.5  # Neutral

        try:
            z_scores = []
            for i, (feat_name, stats) in enumerate(feature_stats.items()):
                if i >= len(feature_vector):
                    break
                feat_mean = stats.get("mean", 0.0)
                feat_std = stats.get("std", 1.0)
                if feat_std < 1e-6:
                    feat_std = 1.0
                z = abs((feature_vector[i] - feat_mean) / feat_std)
                z_scores.append(z)

            if not z_scores:
                return 0.5

            avg_z = np.mean(z_scores)
            # Map z-score to typicality:
            # avg_z=0 → typicality=1.0 (perfectly typical)
            # avg_z=2 → typicality=0.5 (moderately unusual)
            # avg_z=4+ → typicality=0.1 (very unusual)
            typicality = max(0.1, 1.0 - avg_z / 4.0)
            return float(np.clip(typicality, 0.1, 1.0))
        except Exception:
            return 0.5

    # ──────────────────────────────────────────────────────────────────────
    # Composite scoring and classification
    # ──────────────────────────────────────────────────────────────────────

    def _compute_composite(self, components: ConfidenceComponents) -> float:
        """Compute weighted composite confidence."""
        total = 0.0
        weight_sum = 0.0

        for component_name, weight in self.WEIGHTS.items():
            value = getattr(components, component_name, 0.5)
            total += value * weight
            weight_sum += weight

        if weight_sum > 0:
            return total / weight_sum
        return 0.5

    def _classify_tier(self, composite: float) -> str:
        """Classify composite into tier."""
        if composite >= self.TIER_HIGH:
            return "high"
        if composite >= self.TIER_MEDIUM:
            return "medium"
        if composite >= self.TIER_LOW:
            return "low"
        return "very_low"

    @staticmethod
    def _get_recommendation(
        tier: str,
        components: ConfidenceComponents,
    ) -> str:
        """Generate actionable recommendation from confidence tier."""
        if tier == "high":
            return "Result is reliable and can be used for screening decisions."
        if tier == "medium":
            if components.image_quality < 0.5:
                return "Result is usable but image quality could be improved. Consider retaking with better lighting."
            if components.model_stability < 0.5:
                return "Model confidence is moderate. Results should be interpreted with some caution."
            return "Result is reasonably reliable. Follow up with clinical confirmation if needed."
        if tier == "low":
            if components.image_quality < 0.4:
                return "Low confidence due to image quality. Please retake the image with better lighting and focus."
            if components.threshold_stability < 0.4:
                return "Borderline result near the decision threshold. Clinical correlation recommended."
            return "Low confidence result. Clinical confirmation strongly recommended."
        return "Very low confidence. Result is not reliable for screening. Please retake with optimal conditions."

    @staticmethod
    def _build_explanation(
        tier: str,
        components: ConfidenceComponents,
        anemia_risk: float,
    ) -> str:
        """Build human-readable confidence explanation."""
        parts = [f"Confidence tier: {tier}."]

        # Image quality
        if components.image_quality >= 0.7:
            parts.append("Image quality is good.")
        elif components.image_quality < 0.4:
            parts.append("Image quality is below optimal, reducing reliability.")

        # Model stability
        if components.model_stability >= 0.7:
            parts.append("Model predictions are stable and consistent.")
        elif components.model_stability < 0.4:
            parts.append("Model predictions show notable uncertainty.")

        # Threshold proximity
        if components.threshold_stability >= 0.7:
            if anemia_risk > 0.5:
                parts.append("Result is clearly above the screening threshold.")
            else:
                parts.append("Result is clearly below the screening threshold.")
        elif components.threshold_stability < 0.4:
            parts.append("Result is near the decision boundary, making the classification borderline.")

        return " ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience
# ─────────────────────────────────────────────────────────────────────────────

_default_scorer: ModelConfidenceScorer | None = None


def get_confidence_scorer() -> ModelConfidenceScorer:
    """Get or create the singleton confidence scorer."""
    global _default_scorer
    if _default_scorer is None:
        _default_scorer = ModelConfidenceScorer()
    return _default_scorer


def compute_confidence(
    anemia_risk: float,
    uncertainty: float,
    decision_threshold: float = 0.5,
    quality_metrics: dict[str, float] | None = None,
    roi_confidence: float | None = None,
    ensemble_agreement: float | None = None,
) -> ConfidenceResult:
    """Convenience function to compute confidence."""
    return get_confidence_scorer().compute(
        anemia_risk=anemia_risk,
        uncertainty=uncertainty,
        decision_threshold=decision_threshold,
        quality_metrics=quality_metrics,
        roi_confidence=roi_confidence,
        ensemble_agreement=ensemble_agreement,
    )


def _quality_metrics_from_assessment(quality: QualityAssessment) -> dict[str, float]:
    framing = float(getattr(quality, "framing_score", 0.0))
    issue_penalty = min(len(getattr(quality, "issues", [])) * 0.12, 0.48)
    framing_score = min(max(framing / 2.0, 0.0), 1.0)
    overall_quality = np.mean(
        [
            min(quality.blur_score / 200.0, 1.0),
            max(0.0, 1.0 - abs(quality.brightness_score - 0.35) / 0.35),
            min(quality.contrast_score / 0.25, 1.0),
            framing_score,
            1.0 if quality.passed else 0.25,
            max(0.0, 1.0 - issue_penalty),
        ]
    )

    return {
        "blur_score": float(quality.blur_score),
        "brightness": float(quality.brightness_score),
        "contrast": float(quality.contrast_score),
        "overall_quality_score": float(np.clip(overall_quality, 0.0, 1.0)),
        "framing_score": framing_score,
    }


def _capture_quality_score(quality: QualityAssessment) -> float:
    """Legacy helper kept for tests and older call sites."""
    return float(
        get_confidence_scorer()._compute_image_quality_confidence(
            _quality_metrics_from_assessment(quality)
        )
    )


def estimate_model_confidence(
    quality: QualityAssessment,
    *,
    raw_risk: float,
    uncertainty: float,
    decision_threshold: float = 0.5,
    roi_confidence: float | None = None,
    ensemble_agreement: float | None = None,
) -> float:
    """Legacy compatibility wrapper around the composite confidence scorer."""
    result = compute_confidence(
        anemia_risk=raw_risk,
        uncertainty=uncertainty,
        decision_threshold=decision_threshold,
        quality_metrics=_quality_metrics_from_assessment(quality),
        roi_confidence=roi_confidence if roi_confidence is not None else min(max(quality.framing_score / 2.0, 0.0), 1.0),
        ensemble_agreement=ensemble_agreement,
    )
    return float(result.composite_confidence)
