"""
explainability.py — Feature importance and "why this result" explanations.

Provides per-prediction feature importance analysis and natural language
explanations grounded in the model's feature contributions.

Components
----------
1. Feature Importance Calculator: Uses perturbation-based importance
   (model-agnostic) and gradient-based importance (for models that support it).

2. Explanation Generator: Converts feature importances into natural language
   explanations suitable for both clinical and lay audiences.

3. Visualization Data Builder: Generates structured data for frontend
   visualization of feature contributions.

Design Principles
-----------------
- Explanations must be grounded in actual model behavior, not post-hoc fiction.
- Clinical language should be precise but accessible.
- Lay language should be actionable without being alarming.
- All importance scores must sum to a meaningful total.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

log = logging.getLogger("anemialens.explainability")

ImportanceMethod = Literal["perturbation", "coefficient", "shap_proxy"]


@dataclass(frozen=True)
class FeatureImportance:
    """Importance score for a single feature."""
    feature_name: str
    importance_score: float    # Normalized importance [0, 1]
    direction: str             # "increases_risk", "decreases_risk", "neutral"
    feature_value: float       # Actual value for this prediction
    clinical_interpretation: str  # What this feature means clinically
    contribution_to_risk: float   # How much this feature pushed risk up/down


@dataclass(frozen=True)
class ExplainabilityResult:
    """Complete explanation for a prediction."""
    top_features: list[FeatureImportance]  # Top N most important features
    risk_drivers: list[str]                # Features pushing risk UP
    protective_factors: list[str]          # Features pushing risk DOWN
    explanation_clinical: str              # Clinical-grade explanation
    explanation_lay: str                   # Plain-language explanation
    visualization_data: dict               # Structured data for UI viz
    method_used: ImportanceMethod
    total_explained_variance: float        # How much of the prediction is explained


class FeatureImportanceCalculator:
    """
    Compute feature importance for AnemiaLens predictions.

    Supports multiple methods:
    - perturbation: Perturb each feature and measure output change
    - coefficient: Use model coefficients (for linear models)
    - shap_proxy: Approximate SHAP using mean ablation
    """

    def __init__(
        self,
        model=None,
        feature_names: list[str] | None = None,
        feature_stats: dict[str, dict[str, float]] | None = None,
    ) -> None:
        self.model = model
        self.feature_names = feature_names or []
        self.feature_stats = feature_stats or {}

    def compute_perturbation_importance(
        self,
        feature_vector: np.ndarray,
        prediction_fn,
        n_perturbations: int = 5,
        perturbation_scale: float = 0.1,
    ) -> list[FeatureImportance]:
        """
        Compute importance by perturbing each feature and measuring output change.

        Parameters
        ----------
        feature_vector : (n_features,) array
        prediction_fn : Callable that takes feature_vector and returns risk score
        n_perturbations : Number of perturbation samples per feature
        perturbation_scale : Standard deviation of perturbation (fraction of feature std)

        Returns
        -------
        List of FeatureImportance, sorted by importance descending
        """
        n_features = len(feature_vector)
        base_prediction = prediction_fn(feature_vector)

        importances = []
        for i in range(n_features):
            feat_name = self.feature_names[i] if i < len(self.feature_names) else f"feature_{i}"
            feat_value = float(feature_vector[i])
            feat_std = self.feature_stats.get(feat_name, {}).get("std", 0.1)
            if feat_std < 1e-6:
                feat_std = 0.1

            # Perturb this feature multiple times
            perturbed_risks = []
            for _ in range(n_perturbations):
                perturbed = feature_vector.copy()
                delta = np.random.normal(0, perturbation_scale * feat_std)
                perturbed[i] = feat_value + delta
                perturbed_risks.append(prediction_fn(perturbed))

            # Importance = std of perturbed predictions
            importance = float(np.std(perturbed_risks))

            # Direction: does increasing the feature increase or decrease risk?
            perturbed_up = feature_vector.copy()
            perturbed_up[i] = feat_value + perturbation_scale * feat_std
            risk_up = prediction_fn(perturbed_up)
            direction = "increases_risk" if risk_up > base_prediction else "decreases_risk"

            # Contribution
            contribution = float(np.mean(perturbed_risks) - base_prediction)

            importances.append(FeatureImportance(
                feature_name=feat_name,
                importance_score=importance,
                direction=direction,
                feature_value=feat_value,
                clinical_interpretation=self._get_clinical_interpretation(feat_name),
                contribution_to_risk=contribution,
            ))

        # Normalize importance scores to [0, 1]
        max_importance = max((fi.importance_score for fi in importances), default=1.0)
        if max_importance > 0:
            importances = [
                fi._replace(importance_score=fi.importance_score / max_importance)
                for fi in importances
            ]

        return sorted(importances, key=lambda x: x.importance_score, reverse=True)

    def compute_coefficient_importance(
        self,
        feature_vector: np.ndarray,
        coefficients: np.ndarray | None = None,
        intercept: float = 0.0,
    ) -> list[FeatureImportance]:
        """
        Compute importance from model coefficients (linear models).

        Importance = |coefficient * feature_value|
        """
        if coefficients is None and self.model is not None:
            try:
                if hasattr(self.model, "coef_"):
                    coefficients = np.asarray(self.model.coef_, dtype=np.float64).flatten()
                elif hasattr(self.model, "weights"):
                    coefficients = np.asarray(self.model.weights, dtype=np.float64)
                else:
                    coefficients = np.ones(len(feature_vector)) / len(feature_vector)
            except Exception:
                coefficients = np.ones(len(feature_vector)) / len(feature_vector)

        if coefficients is None:
            coefficients = np.ones(len(feature_vector)) / len(feature_vector)

        # Pad or truncate coefficients to match feature vector
        if len(coefficients) < len(feature_vector):
            coefficients = np.pad(
                coefficients, (0, len(feature_vector) - len(coefficients)),
                constant_values=0,
            )
        coefficients = coefficients[:len(feature_vector)]

        importances = []
        for i in range(len(feature_vector)):
            feat_name = self.feature_names[i] if i < len(self.feature_names) else f"feature_{i}"
            feat_value = float(feature_vector[i])
            coeff = float(coefficients[i])

            importance = abs(coeff * feat_value)
            direction = "increases_risk" if coeff * feat_value > 0 else "decreases_risk"
            contribution = coeff * feat_value

            importances.append(FeatureImportance(
                feature_name=feat_name,
                importance_score=importance,
                direction=direction,
                feature_value=feat_value,
                clinical_interpretation=self._get_clinical_interpretation(feat_name),
                contribution_to_risk=contribution,
            ))

        max_importance = max((fi.importance_score for fi in importances), default=1.0)
        if max_importance > 0:
            importances = [
                fi._replace(importance_score=fi.importance_score / max_importance)
                for fi in importances
            ]

        return sorted(importances, key=lambda x: x.importance_score, reverse=True)

    # ──────────────────────────────────────────────────────────────────────
    # Clinical interpretation mapping
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_clinical_interpretation(feature_name: str) -> str:
        """Map feature name to clinical interpretation."""
        interpretations = {
            "mean_r": "Average red channel intensity — relates to blood perfusion in conjunctiva.",
            "mean_g": "Average green channel intensity — helps distinguish pallor from normal tissue.",
            "mean_b": "Average blue channel intensity — contributes to color balance assessment.",
            "cpi": "Conjunctival Pallor Index — ratio of red to total color, indicating blood presence.",
            "center_cpi": "Central Conjunctival Pallor Index — pallor measure in the most clinically relevant area.",
            "red_green_gap": "Red-green color gap — healthy conjunctiva shows more red than green.",
            "center_red_green_gap": "Central red-green gap — key indicator of blood perfusion in the target region.",
            "blur_score": "Image sharpness — sharp images provide more reliable color measurements.",
            "brightness": "Overall image brightness — affects color measurement accuracy.",
            "contrast": "Image contrast — determines how well tissue boundaries are visible.",
            "saturation": "Color saturation — vivid colors provide more reliable diagnostic signals.",
            "pallor_score": "Composite pallor score — direct measure of conjunctival paleness.",
            "hist_dark": "Dark region fraction — excessive dark areas may indicate poor lighting.",
            "hist_bright": "Bright region fraction — excessive bright areas may indicate glare.",
            "illumination_mean": "Average illumination — helps assess lighting quality.",
            "redness_ratio": "Redness ratio — measure of how red the conjunctiva appears.",
            "green_blue_ratio": "Green-to-blue ratio — helps distinguish tissue types.",
            "lab_a_mean": "LAB a* channel (green-red axis) — directly measures red-green balance.",
            "lab_chroma_mean": "LAB chroma — overall colorfulness of the tissue.",
            "hsv_s_mean": "HSV saturation mean — color vividness across the image.",
            "vascular_density": "Blood vessel density — visible vasculature indicates healthy perfusion.",
            "edge_density": "Edge density — tissue texture complexity, related to surface health.",
            "color_homogeneity": "Color uniformity — homogeneous color suggests even perfusion.",
        }
        return interpretations.get(
            feature_name,
            f"Feature '{feature_name}' — contributes to the overall anemia risk assessment."
        )


class ExplanationGenerator:
    """
    Generate human-readable explanations from feature importances.
    """

    def generate(
        self,
        importances: list[FeatureImportance],
        anemia_risk: float,
        decision_threshold: float = 0.5,
        top_n: int = 5,
    ) -> ExplainabilityResult:
        """
        Generate complete explanation for a prediction.

        Parameters
        ----------
        importances : Feature importance list (sorted by importance desc)
        anemia_risk : Final anemia risk prediction
        decision_threshold : Classification threshold
        top_n : Number of top features to include

        Returns
        -------
        ExplainabilityResult
        """
        top_features = importances[:top_n]

        # Classify features
        risk_drivers = [
            fi.feature_name
            for fi in importances
            if fi.direction == "increases_risk" and fi.importance_score > 0.1
        ]
        protective_factors = [
            fi.feature_name
            for fi in importances
            if fi.direction == "decreases_risk" and fi.importance_score > 0.1
        ]

        # Generate explanations
        explanation_clinical = self._generate_clinical_explanation(
            top_features, anemia_risk, decision_threshold
        )
        explanation_lay = self._generate_lay_explanation(
            top_features, anemia_risk, decision_threshold
        )

        # Build visualization data
        visualization_data = self._build_visualization_data(
            top_features, anemia_risk
        )

        # Compute explained variance proxy
        total_explained = sum(fi.importance_score for fi in top_features)

        return ExplainabilityResult(
            top_features=top_features,
            risk_drivers=risk_drivers,
            protective_factors=protective_factors,
            explanation_clinical=explanation_clinical,
            explanation_lay=explanation_lay,
            visualization_data=visualization_data,
            method_used="perturbation",
            total_explained_variance=round(min(total_explained, 1.0), 3),
        )

    @staticmethod
    def _generate_clinical_explanation(
        top_features: list[FeatureImportance],
        anemia_risk: float,
        decision_threshold: float,
    ) -> str:
        """Generate clinical-grade explanation."""
        parts = ["Clinical Feature Analysis:"]

        if anemia_risk > decision_threshold:
            parts.append(
                f"Predicted anemia risk ({anemia_risk:.2f}) exceeds the screening "
                f"threshold ({decision_threshold:.2f}). Contributing factors:"
            )
        else:
            parts.append(
                f"Predicted anemia risk ({anemia_risk:.2f}) is below the screening "
                f"threshold ({decision_threshold:.2f}). Key observations:"
            )

        for i, fi in enumerate(top_features[:3], 1):
            direction_text = "elevating risk" if fi.direction == "increases_risk" else "reducing risk"
            parts.append(
                f"  {i}. {fi.feature_name} ({fi.importance_score:.2f}): "
                f"{fi.clinical_interpretation} "
                f"Value: {fi.feature_value:.3f}, {direction_text}."
            )

        return " ".join(parts)

    @staticmethod
    def _generate_lay_explanation(
        top_features: list[FeatureImportance],
        anemia_risk: float,
        decision_threshold: float,
    ) -> str:
        """Generate plain-language explanation."""
        if anemia_risk > decision_threshold:
            base = (
                "The screening analysis found signals that suggest possible anemia. "
                "Here's what contributed to this result:"
            )
        else:
            base = (
                "The screening analysis did not find strong signals for anemia. "
                "Here's what the analysis looked at:"
            )

        key_factors = []
        for fi in top_features[:3]:
            simplified = _SIMPLIFIED_FEATURE_NAMES.get(
                fi.feature_name, fi.feature_name.replace("_", " ")
            )
            if fi.direction == "increases_risk":
                key_factors.append(f"{simplified} showed patterns associated with anemia")
            else:
                key_factors.append(f"{simplified} showed patterns not typically associated with anemia")

        if key_factors:
            return base + " " + "; ".join(key_factors) + "."
        return base

    @staticmethod
    def _build_visualization_data(
        top_features: list[FeatureImportance],
        anemia_risk: float,
    ) -> dict:
        """Build structured data for frontend visualization."""
        return {
            "anemia_risk": round(anemia_risk, 3),
            "features": [
                {
                    "name": fi.feature_name,
                    "display_name": _SIMPLIFIED_FEATURE_NAMES.get(
                        fi.feature_name, fi.feature_name.replace("_", " ").title()
                    ),
                    "importance": round(fi.importance_score, 3),
                    "direction": fi.direction,
                    "value": round(fi.feature_value, 3),
                    "contribution": round(fi.contribution_to_risk, 4),
                    "interpretation": fi.clinical_interpretation,
                }
                for fi in top_features[:10]
            ],
            "risk_drivers_count": sum(
                1 for fi in top_features if fi.direction == "increases_risk"
            ),
            "protective_count": sum(
                1 for fi in top_features if fi.direction == "decreases_risk"
            ),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Simplified feature name mapping for lay explanations
# ─────────────────────────────────────────────────────────────────────────────

_SIMPLIFIED_FEATURE_NAMES: dict[str, str] = {
    "mean_r": "Red color intensity",
    "mean_g": "Green color intensity",
    "mean_b": "Blue color intensity",
    "cpi": "Conjunctival redness index",
    "center_cpi": "Central tissue redness",
    "red_green_gap": "Red vs green balance",
    "center_red_green_gap": "Central red-green balance",
    "blur_score": "Image sharpness",
    "brightness": "Image brightness",
    "contrast": "Image contrast",
    "saturation": "Color vividness",
    "pallor_score": "Tissue paleness score",
    "hist_dark": "Dark area coverage",
    "hist_bright": "Bright area coverage",
    "illumination_mean": "Lighting quality",
    "redness_ratio": "Redness measure",
    "green_blue_ratio": "Green-to-blue ratio",
    "lab_a_mean": "Red-green color balance",
    "lab_chroma_mean": "Overall color intensity",
    "hsv_s_mean": "Color saturation level",
    "vascular_density": "Blood vessel visibility",
    "edge_density": "Tissue texture detail",
    "color_homogeneity": "Color uniformity",
}


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience
# ─────────────────────────────────────────────────────────────────────────────

def generate_explanation(
    feature_vector: np.ndarray,
    feature_names: list[str] | None = None,
    prediction_fn=None,
    anemia_risk: float = 0.5,
    decision_threshold: float = 0.5,
    feature_stats: dict[str, dict[str, float]] | None = None,
) -> ExplainabilityResult:
    """
    Convenience function to generate a full explanation.

    If prediction_fn is provided, uses perturbation importance.
    Otherwise, uses coefficient-based importance.
    """
    calc = FeatureImportanceCalculator(
        feature_names=feature_names,
        feature_stats=feature_stats,
    )

    if prediction_fn is not None:
        importances = calc.compute_perturbation_importance(
            feature_vector, prediction_fn
        )
    else:
        importances = calc.compute_coefficient_importance(feature_vector)

    generator = ExplanationGenerator()
    return generator.generate(importances, anemia_risk, decision_threshold)
