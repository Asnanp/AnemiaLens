from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from app.ml.archive_model import clamp

FEATURE_ORDER: tuple[str, ...] = (
    "base_anemia_risk",
    "predicted_hemoglobin",
    "uncertainty",
    "classifier_probability",
    "regressor_risk",
    "blend_signal",
    "brightness_score",
    "contrast_score",
    "blur_score",
    "framing_score",
    "lighting_score",
    "glare_risk",
    "shadow_risk",
    "center_cpi",
    "center_red_green_gap",
    "pallor_score",
    "rgb_entropy",
    "center_contrast",
    "center_blur_score",
)


@dataclass
class UltimateRuntimeRefiner:
    version: str = "ultimate-runtime-refiner-v1"
    method: str = "gradient-boosting-compatibility"
    threshold: float = 0.35
    feature_order: tuple[str, ...] = FEATURE_ORDER
    feature_means: dict[str, float] = field(default_factory=dict)
    feature_stds: dict[str, float] = field(default_factory=dict)
    model: Any = None
    report: dict[str, object] = field(default_factory=dict)

    def remap_ultimate_features(
        self,
        feature_map: dict[str, float],
        *,
        archive_feature_names: list[str],
        expected_means: dict[str, float],
        expected_stds: dict[str, float],
    ) -> dict[str, float]:
        remapped: dict[str, float] = {}
        for name in archive_feature_names:
            current_value = float(feature_map.get(name, expected_means.get(name, 0.0)))
            current_mean = float(self.feature_means.get(name, current_value))
            current_std = max(float(self.feature_stds.get(name, 1.0)), 1e-6)
            standardized = (current_value - current_mean) / current_std
            remapped[name] = float(
                expected_means.get(name, 0.0)
                + (standardized * expected_stds.get(name, 1.0))
            )
        return remapped

    def _feature_vector(
        self,
        *,
        base_prediction: dict[str, float],
        quality,
        base_feature_map: dict[str, float],
    ) -> list[float]:
        predicted_hemoglobin = base_prediction.get("predicted_hemoglobin")
        return [
            float(base_prediction.get("anemia_risk", 0.5)),
            float(predicted_hemoglobin if predicted_hemoglobin is not None else 13.2),
            float(base_prediction.get("uncertainty", 0.5)),
            float(base_prediction.get("classifier_probability", 0.5)),
            float(base_prediction.get("regressor_risk", 0.5)),
            float(base_prediction.get("blend_signal", 0.5)),
            float(getattr(quality, "brightness_score", 0.0)),
            float(getattr(quality, "contrast_score", 0.0)),
            float(getattr(quality, "blur_score", 0.0)),
            float(getattr(quality, "framing_score", 0.0)),
            float(getattr(quality, "lighting_score", 0.0)),
            float(getattr(quality, "glare_risk", 0.0)),
            float(getattr(quality, "shadow_risk", 0.0)),
            float(base_feature_map.get("center_cpi", 0.0)),
            float(base_feature_map.get("center_red_green_gap", 0.0)),
            float(base_feature_map.get("pallor_score", 0.0)),
            float(base_feature_map.get("rgb_entropy", 0.0)),
            float(base_feature_map.get("center_contrast", 0.0)),
            float(base_feature_map.get("center_blur_score", 0.0)),
        ]

    def refine(
        self,
        *,
        base_prediction: dict[str, float],
        quality,
        base_feature_map: dict[str, float],
    ) -> float:
        if self.model is None:
            return clamp(float(base_prediction.get("anemia_risk", 0.5)), 0.0, 1.0)
        vector = np.asarray(
            [
                self._feature_vector(
                    base_prediction=base_prediction,
                    quality=quality,
                    base_feature_map=base_feature_map,
                )
            ],
            dtype=np.float32,
        )
        probability = float(self.model.predict_proba(vector)[0, 1])
        return clamp(probability, 0.0, 1.0)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            pickle.dump(self, handle)

    @classmethod
    def load(cls, path: str | Path) -> "UltimateRuntimeRefiner":
        with Path(path).open("rb") as handle:
            return pickle.load(handle)
