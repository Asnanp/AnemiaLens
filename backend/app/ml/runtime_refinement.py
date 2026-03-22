from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from app.ml.archive_model import clamp

FEATURE_ORDER: tuple[str, ...] = (
    "base_anemia_risk",
    "uncertainty",
    "predicted_hemoglobin",
    "predicted_hemoglobin_missing",
    "brightness_score",
    "contrast_score",
    "blur_score",
    "framing_score",
    "lighting_score",
    "glare_risk",
    "shadow_risk",
    "lighting_balanced",
    "lighting_overexposed",
    "lighting_glare_heavy",
    "lighting_shadow_heavy",
    "lighting_flat_contrast",
    "lighting_dim",
    "base_likely",
)


@dataclass
class RuntimeScreeningRefiner:
    version: str = "runtime-screening-refiner-v1"
    method: str = "logistic-regression"
    threshold: float = 0.53
    feature_order: tuple[str, ...] = FEATURE_ORDER
    model: Any = None
    report: dict[str, object] = field(default_factory=dict)

    def _feature_vector(
        self,
        *,
        base_anemia_risk: float,
        uncertainty: float,
        predicted_hemoglobin: float | None,
        quality,
        base_likely: bool,
    ) -> list[float]:
        hb_missing = predicted_hemoglobin is None
        hb_value = 13.5 if predicted_hemoglobin is None else float(predicted_hemoglobin)
        lighting = str(getattr(quality, "lighting_condition", "balanced"))
        return [
            float(base_anemia_risk),
            float(uncertainty),
            hb_value,
            float(hb_missing),
            float(getattr(quality, "brightness_score", 0.0)),
            float(getattr(quality, "contrast_score", 0.0)),
            float(getattr(quality, "blur_score", 0.0)),
            float(getattr(quality, "framing_score", 0.0)),
            float(getattr(quality, "lighting_score", 0.0)),
            float(getattr(quality, "glare_risk", 0.0)),
            float(getattr(quality, "shadow_risk", 0.0)),
            float(lighting == "balanced"),
            float(lighting == "overexposed"),
            float(lighting == "glare_heavy"),
            float(lighting == "shadow_heavy"),
            float(lighting == "flat_contrast"),
            float(lighting == "dim"),
            float(base_likely),
        ]

    def refine(
        self,
        *,
        base_anemia_risk: float,
        uncertainty: float,
        predicted_hemoglobin: float | None,
        quality,
        base_likely: bool,
    ) -> float:
        if self.model is None:
            return clamp(float(base_anemia_risk), 0.0, 1.0)
        vector = np.asarray(
            [
                self._feature_vector(
                    base_anemia_risk=base_anemia_risk,
                    uncertainty=uncertainty,
                    predicted_hemoglobin=predicted_hemoglobin,
                    quality=quality,
                    base_likely=base_likely,
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
    def load(cls, path: str | Path) -> "RuntimeScreeningRefiner":
        with Path(path).open("rb") as handle:
            return pickle.load(handle)
