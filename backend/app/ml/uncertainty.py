"""
Uncertainty estimation for AnemiaLens.

Provides:
- MCDropoutEstimator: lightweight MC Dropout (4-8 passes, CPU-safe)
- EnsembleUncertainty: variance across tree estimators (already in archive_model)
- UncertaintyAggregator: combines multiple uncertainty signals into one score
- should_trigger_retake(): decision function for image quality gating
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from torch import nn


# ---------------------------------------------------------------------------
# MC Dropout Estimator
# ---------------------------------------------------------------------------

class MCDropoutEstimator:
    """
    Runs N forward passes with dropout enabled to estimate epistemic uncertainty.
    Designed for CPU: keep n_passes <= 8 to stay under ~200ms overhead.
    """

    def __init__(self, n_passes: int = 6) -> None:
        self.n_passes = max(2, min(n_passes, 16))

    def estimate(
        self,
        model: "nn.Module",
        tensor: "object",  # torch.Tensor
        *,
        hb_mean: float = 0.0,
        hb_std: float = 1.0,
    ) -> dict[str, float]:
        """
        Returns mean prediction + uncertainty metrics.
        Caller must pass a pre-transformed tensor (1, C, H, W).
        """
        import torch

        probs: list[float] = []
        hbs: list[float] = []

        _enable_dropout(model)
        with torch.no_grad():
            for _ in range(self.n_passes):
                out = model(tensor)
                probs.append(float(torch.sigmoid(out[:, 0]).item()))
                hbs.append(float(out[:, 1].item() * max(hb_std, 1e-6) + hb_mean))

        model.eval()

        mean_prob = float(np.mean(probs))
        std_prob = float(np.std(probs))
        mean_hb = float(np.mean(hbs))
        std_hb = float(np.std(hbs))

        # Margin uncertainty: how far from the decision boundary
        margin_uncertainty = 1.0 - min(1.0, abs(mean_prob - 0.5) * 2.5)

        # Combined epistemic uncertainty
        epistemic = float(np.clip(
            std_prob * 2.2 + (min(std_hb / 2.0, 1.0) * 0.30) + (margin_uncertainty * 0.18),
            0.04, 0.95,
        ))

        return {
            "mean_prob": mean_prob,
            "std_prob": std_prob,
            "mean_hb": mean_hb,
            "std_hb": std_hb,
            "margin_uncertainty": margin_uncertainty,
            "epistemic_uncertainty": epistemic,
        }


# ---------------------------------------------------------------------------
# Ensemble Uncertainty (tree-based, no torch needed)
# ---------------------------------------------------------------------------

class EnsembleUncertainty:
    """
    Computes prediction variance across ExtraTrees estimators.
    Works with archive_model's regressor/classifier directly.
    """

    @staticmethod
    def from_regressor(regressor: object, row: np.ndarray) -> float:
        """Std of per-tree Hb predictions, normalised to [0, 1]."""
        tree_preds = np.array([t.predict(row) for t in regressor.estimators_], dtype=np.float32)
        std = float(np.std(tree_preds))
        # Normalise: std of ~2 g/dL → uncertainty ~0.5
        return float(np.clip(std / 4.0, 0.0, 1.0))

    @staticmethod
    def from_classifier(classifier: object, row: np.ndarray) -> float:
        """Std of per-tree anemia probability predictions."""
        tree_probs = np.array([t.predict_proba(row)[:, 1] for t in classifier.estimators_], dtype=np.float32)
        std = float(np.std(tree_probs))
        return float(np.clip(std * 2.0, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Uncertainty Aggregator
# ---------------------------------------------------------------------------

class UncertaintyAggregator:
    """
    Combines multiple uncertainty signals into a single calibrated score.

    Signals (all in [0, 1]):
    - mc_uncertainty: from MC Dropout or ensemble variance
    - margin_uncertainty: distance from decision boundary
    - model_disagreement: |image_risk - symptom_risk| or |archive - efficientnet|
    - quality_penalty: from image quality assessment
    """

    # Weights sum to 1.0
    _W_MC = 0.40
    _W_MARGIN = 0.25
    _W_DISAGREEMENT = 0.20
    _W_QUALITY = 0.15

    def aggregate(
        self,
        *,
        mc_uncertainty: float,
        margin_uncertainty: float,
        model_disagreement: float = 0.0,
        quality_penalty: float = 0.0,
    ) -> float:
        raw = (
            mc_uncertainty * self._W_MC
            + margin_uncertainty * self._W_MARGIN
            + model_disagreement * self._W_DISAGREEMENT
            + quality_penalty * self._W_QUALITY
        )
        return float(np.clip(raw, 0.04, 0.95))

    def confidence_from_uncertainty(self, uncertainty: float) -> float:
        return float(np.clip(1.0 - uncertainty, 0.05, 0.96))


# ---------------------------------------------------------------------------
# Retake Decision
# ---------------------------------------------------------------------------

def should_trigger_retake(
    uncertainty: float,
    margin: float,
    quality_score: float,
    *,
    uncertainty_threshold: float = 0.72,
    margin_threshold: float = 0.06,
    quality_threshold: float = 0.35,
) -> bool:
    """
    Returns True if the system should ask the user to retake the photo.

    Triggers when:
    - Uncertainty is very high (model is confused), OR
    - Decision margin is razor-thin AND quality is poor
    """
    if uncertainty >= uncertainty_threshold:
        return True
    if margin < margin_threshold and quality_score < quality_threshold:
        return True
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enable_dropout(model: "nn.Module") -> None:
    """Set all Dropout layers to train mode (enables stochastic dropout)."""
    try:
        from torch import nn
        for module in model.modules():
            if isinstance(module, nn.Dropout):
                module.train()
    except ImportError:
        pass
