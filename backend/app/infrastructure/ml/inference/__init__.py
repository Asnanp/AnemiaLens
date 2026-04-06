"""
Inference pipeline — running predictions through loaded models.

This module isolates model inference execution from the prediction
service so that:
- Inference can be tested with mock models
- New model architectures can be integrated by adding new predictors
- The orchestration logic in ScreeningPredictor can delegate to
  clean, testable inference units

Usage:
    predictor = ArchiveModelPredictor(model_artifact)
    result = predictor.predict(feature_map, source_hint="roi_original")
"""

from __future__ import annotations

import logging
from typing import Literal

from app.ml.archive_model import clamp

log = logging.getLogger("anemialens.infrastructure.ml.inference")

SourceHint = Literal["roi_original", "palpebral", "forniceal_palpebral"]


class ArchiveModelPredictor:
    """
    Runs inference through an archive (sklearn-based) screening model.

    The archive model expects a feature map (dict of name -> float)
    and returns a prediction dict with at least:
    - anemia_risk: float in [0, 1]
    - uncertainty: float in [0, 1]
    """

    def __init__(self, artifact: dict[str, object]) -> None:
        self._artifact = artifact

    def predict(
        self,
        feature_map: dict[str, float],
        *,
        source_hint: SourceHint = "roi_original",
    ) -> dict[str, float]:
        """
        Run prediction through the archive model.

        Parameters
        ----------
        feature_map : dict[str, float]
            Extracted features from the image.
        source_hint : SourceHint
            Which ROI source produced the features.

        Returns
        -------
        dict[str, float]
            Prediction dict with anemia_risk, uncertainty, etc.
        """
        from app.ml.archive_model import predict_with_archive_model

        return predict_with_archive_model(
            self._artifact,
            feature_map,
            source_hint=source_hint,
        )

    @property
    def version(self) -> str:
        """Model version string from the artifact metadata."""
        version = self._artifact.get("version")
        return str(version or "unknown")

    @property
    def feature_names(self) -> list[str]:
        """Expected feature names for this model."""
        names = self._artifact.get("feature_names")
        if isinstance(names, list) and names:
            return [str(n) for n in names]
        return []

    @property
    def scaler_stats(self) -> tuple[dict[str, float], dict[str, float]]:
        """
        Returns (expected_means, expected_stds) for feature normalization.

        If the artifact has no scaler, returns zero/one defaults.
        """
        feature_names = self.feature_names
        if not feature_names:
            return {}, {}

        scaler = self._artifact.get("scaler")
        if scaler is None or not hasattr(scaler, "mean_") or not hasattr(scaler, "scale_"):
            return (
                {name: 0.0 for name in feature_names},
                {name: 1.0 for name in feature_names},
            )

        means = {
            name: float(value)
            for name, value in zip(feature_names, scaler.mean_, strict=False)
        }
        stds = {
            name: max(float(value), 1e-6)
            for name, value in zip(feature_names, scaler.scale_, strict=False)
        }
        return means, stds

    def uses_ultimate_features(self) -> bool:
        """True if this model expects v7 ultimate clinical features."""
        return self.version.startswith("archive-fusion-v7-ultimate-clinical")

    def uses_v8_features(self) -> bool:
        """True if this model expects v8 clinical robust features."""
        return self.version.startswith("archive-fusion-v8-clinical-robust")


class EfficientNetPredictor:
    """
    Runs inference through the EfficientNet-B0 fine-tuned model.

    Uses Monte Carlo dropout passes to estimate uncertainty.
    """

    def __init__(self, bundle: dict[str, object]) -> None:
        self._bundle = bundle

    def predict(
        self,
        image,
        *,
        mc_passes: int = 10,
    ) -> dict[str, float]:
        """
        Run prediction with Monte Carlo dropout for uncertainty estimation.

        Parameters
        ----------
        image : PIL.Image.Image
            The eye image to classify.
        mc_passes : int
            Number of MC dropout passes (higher = more stable uncertainty).

        Returns
        -------
        dict[str, float]
            Prediction dict with anemia_risk, uncertainty, etc.
        """
        from app.ml.efficientnet_model import predict_with_efficientnet_model

        return predict_with_efficientnet_model(
            self._bundle,
            image,
            mc_passes=mc_passes,
        )

    @property
    def version(self) -> str:
        """Model version string."""
        return str(self._bundle.get("version", "efficientnet-b0-ft"))


def build_runtime_stack(
    archive_prediction: dict[str, float],
    *,
    efficientnet_prediction: dict[str, float] | None,
    source_hint: SourceHint,
) -> dict[str, float]:
    """
    Combine archive model and EfficientNet predictions into a
    unified runtime stack prediction.

    This delegates to the existing runtime_stack module for the
    fusion logic.
    """
    from app.ml.runtime_stack import build_runtime_stack_prediction

    return build_runtime_stack_prediction(
        archive_prediction,
        efficientnet_prediction=efficientnet_prediction,
        source_hint=source_hint,
    )


def decision_threshold_for_source(source_hint: SourceHint) -> float:
    """Get the default decision threshold for a given source hint."""
    from app.ml.runtime_stack import decision_threshold_for_source

    return float(decision_threshold_for_source(source_hint))
