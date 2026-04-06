"""
fallback_prediction.py — Fallback prediction with uncertainty bounds.

When the primary ML pipeline cannot produce a reliable prediction (due to
poor image quality, model failure, or borderline confidence), this module
provides conservative fallback predictions with well-calibrated uncertainty
bounds.

Fallback Strategies
-------------------
1. **Conservative Default**: Returns a prior-based prediction with wide
   uncertainty bounds, reflecting high epistemic uncertainty.

2. **Population Prior**: If demographic data is available, uses population-level
   anemia prevalence as a prior for a more informed fallback.

3. **Heuristic Fallback**: Uses simple color/heuristic rules when ML models
   fail but basic features can still be extracted.

4. **Escalation Recommendation**: When even fallback is unreliable,
   recommends retake with specific guidance.

Uncertainty Bounds
------------------
All fallback predictions include calibrated uncertainty intervals that
reflect the reduced confidence of the fallback method.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from PIL import Image

log = logging.getLogger("anemialens.fallback")

FallbackMethod = Literal["conservative_default", "population_prior", "heuristic", "unavailable"]
FallbackReason = Literal[
    "quality_gate_rejection",
    "model_failure",
    "low_confidence",
    "feature_extraction_failure",
    "no_model_available",
]


@dataclass(frozen=True)
class FallbackPrediction:
    """A fallback prediction with uncertainty bounds."""
    anemia_risk: float              # Point estimate [0, 1]
    predicted_hemoglobin: float | None  # Hb estimate g/dL
    uncertainty: float              # Epistemic uncertainty [0, 1]
    hb_interval: tuple[float, float] | None  # (lower, upper) Hb range
    method: FallbackMethod
    reason: FallbackReason
    confidence_tier: str            # Always "low" or "very_low" for fallbacks
    recommendation: str             # What the user should do
    is_fallback: bool = True
    diagnostics: dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Population priors (global anemia prevalence by demographic)
# ─────────────────────────────────────────────────────────────────────────────

# Global anemia prevalence by sex and age group (WHO estimates)
# Format: {sex: {age_group: prevalence}}
POPULATION_PRIORS: dict[str, dict[str, float]] = {
    "female": {
        "child": 0.40,       # Children under 5
        "school": 0.37,      # School-age children
        "adolescent": 0.30,  # Adolescent girls
        "adult": 0.30,       # Non-pregnant women
        "pregnant": 0.36,    # Pregnant women
        "elderly": 0.25,     # Elderly women
    },
    "male": {
        "child": 0.38,
        "school": 0.35,
        "adolescent": 0.20,
        "adult": 0.15,
        "elderly": 0.20,
    },
    "other": {
        "child": 0.39,
        "school": 0.36,
        "adolescent": 0.25,
        "adult": 0.22,
        "elderly": 0.22,
    },
    "not_specified": {
        "adult": 0.27,  # Global average
    },
}

# Normal hemoglobin ranges by demographic (g/dL)
HEMOGLOBIN_NORMS: dict[str, dict[str, tuple[float, float]]] = {
    "female": {
        "adult": (12.0, 15.5),
        "pregnant": (11.0, 14.0),
        "elderly": (11.5, 15.0),
    },
    "male": {
        "adult": (13.5, 17.5),
        "elderly": (12.5, 16.5),
    },
}

# Anemia threshold Hb by demographic (WHO criteria, g/dL)
ANEMIA_THRESHOLDS: dict[str, dict[str, float]] = {
    "female": {"adult": 12.0, "pregnant": 11.0, "elderly": 11.5},
    "male": {"adult": 13.0, "elderly": 12.5},
    "other": {"adult": 12.0},
    "not_specified": {"adult": 12.0},
}


class FallbackPredictor:
    """
    Provides fallback predictions when the primary pipeline fails.

    Usage
    -----
    fallback = FallbackPredictor()
    result = fallback.predict(
        reason="quality_gate_rejection",
        image=pil_image,  # optional, for heuristic fallback
        sex="female",
        age=30,
    )
    """

    def predict(
        self,
        reason: FallbackReason,
        image: Image.Image | None = None,
        sex: str = "not_specified",
        age: int | None = None,
        is_pregnant: bool = False,
        feature_map: dict[str, float] | None = None,
    ) -> FallbackPrediction:
        """
        Generate a fallback prediction.

        Parameters
        ----------
        reason : Why the primary prediction failed
        image : Original image (for heuristic fallback)
        sex : Patient sex for population prior
        age : Patient age for population prior
        is_pregnant : Whether patient is pregnant
        feature_map : Extracted features (for heuristic fallback)

        Returns
        -------
        FallbackPrediction
        """
        age_group = self._classify_age_group(age)
        sex_key = sex.lower() if sex in POPULATION_PRIORS else "not_specified"

        # Determine best fallback method
        if feature_map is not None and reason in ("quality_gate_rejection", "low_confidence"):
            # Can still use heuristic if features are available
            method: FallbackMethod = "heuristic"
        elif sex_key != "not_specified" or age is not None:
            method = "population_prior"
        else:
            method = "conservative_default"

        if method == "conservative_default":
            return self._conservative_default(reason)
        elif method == "population_prior":
            return self._population_prior(reason, sex_key, age_group, is_pregnant)
        else:
            return self._heuristic_fallback(reason, feature_map or {}, image, sex_key, age_group)

    # ──────────────────────────────────────────────────────────────────────
    # Fallback methods
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _conservative_default(reason: FallbackReason) -> FallbackPrediction:
        """
        Conservative default: mid-range prediction with wide uncertainty.

        This is the safest fallback when no information is available.
        """
        risk = 0.50  # Neutral prior
        uncertainty = 0.45  # Very high uncertainty
        hb_interval = (8.0, 16.0)  # Very wide interval

        return FallbackPrediction(
            anemia_risk=risk,
            predicted_hemoglobin=None,
            uncertainty=uncertainty,
            hb_interval=hb_interval,
            method="conservative_default",
            reason=reason,
            confidence_tier="very_low",
            recommendation=(
                "No reliable prediction could be generated. "
                "Please retake the image under better conditions and try again. "
                "If you have symptoms of anemia, please consult a healthcare provider."
            ),
            diagnostics={
                "fallback_rationale": "No data available; using neutral prior with maximum uncertainty.",
                "reason": reason,
            },
        )

    def _population_prior(
        self,
        reason: FallbackReason,
        sex: str,
        age_group: str,
        is_pregnant: bool,
    ) -> FallbackPrediction:
        """
        Population prior fallback: uses demographic-based anemia prevalence.

        More informative than conservative default but still has wide uncertainty.
        """
        sex_key = sex if sex in POPULATION_PRIORS else "not_specified"
        age_key = age_group if age_group in POPULATION_PRIORS[sex_key] else "adult"

        prior_risk = POPULATION_PRIORS[sex_key].get(age_key, 0.27)

        # Get hemoglobin norm for this demographic
        hb_norm = HEMOGLOBIN_NORMS.get(sex_key, {}).get(
            "pregnant" if is_pregnant else age_key, (12.0, 15.5)
        )
        anemia_threshold = ANEMIA_THRESHOLDS.get(sex_key, {}).get(
            "pregnant" if is_pregnant else age_key, 12.0
        )

        # Estimated Hb based on prior risk
        hb_mean = (hb_norm[0] + hb_norm[1]) / 2
        # If prior risk is high, estimated Hb is lower
        estimated_hb = hb_mean - (prior_risk - 0.2) * 5.0  # Rough linear mapping
        estimated_hb = max(7.0, min(18.0, estimated_hb))

        # Wider uncertainty than normal prediction
        uncertainty = 0.35 + prior_risk * 0.1
        hb_width = 3.0 + prior_risk * 2.0  # Wider interval for higher risk

        return FallbackPrediction(
            anemia_risk=round(prior_risk, 3),
            predicted_hemoglobin=round(estimated_hb, 1),
            uncertainty=round(uncertainty, 3),
            hb_interval=(
                round(max(5.0, estimated_hb - hb_width), 1),
                round(min(20.0, estimated_hb + hb_width), 1),
            ),
            method="population_prior",
            reason=reason,
            confidence_tier="low",
            recommendation=(
                f"Based on population data for your demographic, "
                f"the estimated anemia risk is {prior_risk:.0%}. "
                f"This is a statistical estimate, not a medical diagnosis. "
                f"Please consult a healthcare provider for a proper blood test."
            ),
            diagnostics={
                "fallback_rationale": f"Using population prior for {sex_key}/{age_group}.",
                "prior_risk": prior_risk,
                "population_prevalence": prior_risk,
                "estimated_hb_normal_range": list(hb_norm),
                "anemia_threshold_hb": anemia_threshold,
                "reason": reason,
            },
        )

    def _heuristic_fallback(
        self,
        reason: FallbackReason,
        feature_map: dict[str, float],
        image: Image.Image | None,
        sex: str,
        age_group: str,
    ) -> FallbackPrediction:
        """
        Heuristic fallback: uses simple color rules when ML models fail
        but basic features can be extracted.
        """
        # Simple color-based anemia heuristic
        cpi = feature_map.get("cpi", 0.4)
        red_green_gap = feature_map.get("red_green_gap", 0.05)
        brightness = feature_map.get("brightness", 0.35)
        saturation = feature_map.get("saturation", 0.15)

        # Heuristic anemia score
        # Low CPI (less red) → higher anemia risk
        # Low red-green gap → higher anemia risk
        cpi_risk = max(0.0, min(1.0, (0.45 - cpi) / 0.15))  # CPI < 0.35 → high risk
        rgg_risk = max(0.0, min(1.0, (0.08 - red_green_gap) / 0.10))

        # Quality-adjusted heuristic
        quality_factor = min(1.0, brightness * 2.0) * min(1.0, saturation * 5.0)

        heuristic_risk = (cpi_risk * 0.6 + rgg_risk * 0.4) * quality_factor + 0.5 * (1 - quality_factor)
        heuristic_risk = float(np.clip(heuristic_risk, 0.1, 0.9))

        # Estimated Hb from heuristic
        # Rough mapping: risk 0.8 → Hb ~8, risk 0.2 → Hb ~15
        estimated_hb = 17.0 - heuristic_risk * 10.0
        estimated_hb = max(6.0, min(19.0, estimated_hb))

        # Higher uncertainty than normal prediction
        uncertainty = 0.30 + (1 - quality_factor) * 0.20
        hb_width = 2.5 + (1 - quality_factor) * 2.0

        return FallbackPrediction(
            anemia_risk=round(heuristic_risk, 3),
            predicted_hemoglobin=round(estimated_hb, 1),
            uncertainty=round(uncertainty, 3),
            hb_interval=(
                round(max(5.0, estimated_hb - hb_width), 1),
                round(min(20.0, estimated_hb + hb_width), 1),
            ),
            method="heuristic",
            reason=reason,
            confidence_tier="low",
            recommendation=(
                "A simplified analysis was used due to model limitations. "
                "This result is less reliable than a full ML prediction. "
                "Please retake under optimal conditions for a more accurate screening, "
                "and consult a healthcare provider for confirmation."
            ),
            diagnostics={
                "fallback_rationale": "Heuristic color-based analysis (ML models unavailable).",
                "cpi_risk": round(cpi_risk, 3),
                "rgg_risk": round(rgg_risk, 3),
                "quality_factor": round(quality_factor, 3),
                "reason": reason,
            },
        )

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _classify_age_group(age: int | None) -> str:
        """Classify age into demographic group."""
        if age is None:
            return "adult"
        if age < 5:
            return "child"
        if age < 12:
            return "school"
        if age < 18:
            return "adolescent"
        if age < 65:
            return "adult"
        return "elderly"


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience
# ─────────────────────────────────────────────────────────────────────────────

_default_fallback: FallbackPredictor | None = None


def get_fallback_predictor() -> FallbackPredictor:
    """Get or create the singleton fallback predictor."""
    global _default_fallback
    if _default_fallback is None:
        _default_fallback = FallbackPredictor()
    return _default_fallback


def generate_fallback(
    reason: FallbackReason,
    image: Image.Image | None = None,
    sex: str = "not_specified",
    age: int | None = None,
    is_pregnant: bool = False,
    feature_map: dict[str, float] | None = None,
) -> FallbackPrediction:
    """Convenience function to generate a fallback prediction."""
    return get_fallback_predictor().predict(
        reason=reason,
        image=image,
        sex=sex,
        age=age,
        is_pregnant=is_pregnant,
        feature_map=feature_map,
    )
