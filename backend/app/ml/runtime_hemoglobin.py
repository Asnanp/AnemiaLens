from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from app.schemas import QualityAssessment

V8_RUNTIME_HB_FEATURE_NAMES = [
    "raw_predicted_hemoglobin",
    "anemia_risk",
    "classifier_probability",
    "regressor_risk",
    "uncertainty",
    "hb_interval_low",
    "hb_interval_high",
    "lighting_score",
    "glare_risk",
    "shadow_risk",
    "blur_score",
    "brightness_score",
    "contrast_score",
    "framing_score",
    "lighting_balanced",
    "lighting_overexposed",
    "lighting_glare_heavy",
    "lighting_shadow_heavy",
    "age",
    "sex_female",
    "sex_male",
]


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, float(value)))


def build_v8_runtime_hb_features(
    *,
    archive_prediction: dict[str, float],
    quality: QualityAssessment,
    age: int | None = None,
    sex: str = "not_specified",
) -> dict[str, float]:
    lighting_condition = str(getattr(quality, "lighting_condition", "unknown")).strip().lower()
    predicted_hemoglobin = float(archive_prediction.get("predicted_hemoglobin", 13.0))
    hb_interval_low = float(archive_prediction.get("hb_interval_low", predicted_hemoglobin))
    hb_interval_high = float(archive_prediction.get("hb_interval_high", predicted_hemoglobin))
    normalised_sex = str(sex or "not_specified").strip().lower()

    return {
        "raw_predicted_hemoglobin": predicted_hemoglobin,
        "anemia_risk": float(archive_prediction.get("anemia_risk", 0.0)),
        "classifier_probability": float(archive_prediction.get("classifier_probability", 0.0)),
        "regressor_risk": float(archive_prediction.get("regressor_risk", 0.0)),
        "uncertainty": float(archive_prediction.get("uncertainty", 0.5)),
        "hb_interval_low": hb_interval_low,
        "hb_interval_high": hb_interval_high,
        "lighting_score": float(getattr(quality, "lighting_score", 0.0)),
        "glare_risk": float(getattr(quality, "glare_risk", 0.0)),
        "shadow_risk": float(getattr(quality, "shadow_risk", 0.0)),
        "blur_score": float(getattr(quality, "blur_score", 0.0)),
        "brightness_score": float(getattr(quality, "brightness_score", 0.0)),
        "contrast_score": float(getattr(quality, "contrast_score", 0.0)),
        "framing_score": float(getattr(quality, "framing_score", 0.0)),
        "lighting_balanced": 1.0 if lighting_condition == "balanced" else 0.0,
        "lighting_overexposed": 1.0 if lighting_condition == "overexposed" else 0.0,
        "lighting_glare_heavy": 1.0 if lighting_condition == "glare_heavy" else 0.0,
        "lighting_shadow_heavy": 1.0 if lighting_condition == "shadow_heavy" else 0.0,
        "age": float(age or 0.0),
        "sex_female": 1.0 if normalised_sex == "female" else 0.0,
        "sex_male": 1.0 if normalised_sex == "male" else 0.0,
    }


@dataclass
class RuntimeHemoglobinCalibrator:
    version: str = "runtime-hemoglobin-calibrator-v8"
    method: str = "hist-gradient-boosting"
    model: object | None = None
    feature_names: list[str] = field(default_factory=lambda: list(V8_RUNTIME_HB_FEATURE_NAMES))
    min_hb: float = 4.5
    max_hb: float = 19.5
    report: dict[str, object] = field(default_factory=dict)

    def predict(self, features: dict[str, float]) -> float:
        if self.model is None:
            raw_value = float(features.get("raw_predicted_hemoglobin", 13.0))
            return _clamp(raw_value, self.min_hb, self.max_hb)
        row = np.asarray(
            [[float(features.get(name, 0.0)) for name in self.feature_names]],
            dtype=np.float32,
        )
        value = float(self.model.predict(row)[0])
        return _clamp(value, self.min_hb, self.max_hb)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            pickle.dump(self, handle)

    @classmethod
    def load(cls, path: str | Path) -> "RuntimeHemoglobinCalibrator":
        with Path(path).open("rb") as handle:
            return pickle.load(handle)
