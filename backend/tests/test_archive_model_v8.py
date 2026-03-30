from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.archive_model_v8 import predict_with_archive_model_v8
from app.ml.features import V8_CLINICAL_FEATURE_NAMES, extract_v8_clinical_features


class _FixedClassifier:
    def __init__(self, positive_probability: float) -> None:
        self.positive_probability = float(positive_probability)

    def predict_proba(self, rows):
        import numpy as np

        negative = 1.0 - self.positive_probability
        return np.asarray([[negative, self.positive_probability] for _ in range(len(rows))], dtype=float)


class _FixedRegressor:
    def __init__(self, value: float) -> None:
        self.value = float(value)

    def predict(self, rows):
        import numpy as np

        return np.asarray([self.value for _ in range(len(rows))], dtype=float)


def test_extract_v8_clinical_features_returns_expected_shape() -> None:
    feature_map = extract_v8_clinical_features(
        Image.new("RGB", (320, 180), color=(182, 126, 120)),
        None,
        age=28,
        sex="female",
        source_hint="roi_original",
    )

    assert set(feature_map) == set(V8_CLINICAL_FEATURE_NAMES)
    assert feature_map["source_roi_original"] == 1.0
    assert 0.0 <= feature_map["lighting_score"] <= 1.0


def test_predict_with_archive_model_v8_returns_risk_payload() -> None:
    scaler = StandardScaler().fit([[0.0] * len(V8_CLINICAL_FEATURE_NAMES), [1.0] * len(V8_CLINICAL_FEATURE_NAMES)])
    artifact = {
        "version": "archive-fusion-v8-clinical-robust",
        "feature_names": V8_CLINICAL_FEATURE_NAMES,
        "models": {
            "hgb_clf": _FixedClassifier(0.24),
            "et_clf": _FixedClassifier(0.21),
            "hgb_reg": _FixedRegressor(13.6),
            "ridge_reg": _FixedRegressor(13.2),
        },
        "scalers": {"linear": scaler},
        "scaled_models": ["ridge_reg"],
        "classifier_weights": {"et_clf": 0.45, "hgb_clf": 0.55},
        "regressor_weights": {"hgb_reg": 0.65, "ridge_reg": 0.35},
        "calibration": {
            "hb_threshold": 11.5,
            "hb_scale": 1.0,
            "classifier_weight": 0.62,
            "blend_threshold": 0.48,
            "risk_scale": 0.14,
        },
    }
    feature_map = {name: 0.2 for name in V8_CLINICAL_FEATURE_NAMES}
    feature_map["lighting_score"] = 0.78
    feature_map["glare_risk"] = 0.08
    feature_map["shadow_risk"] = 0.05

    prediction = predict_with_archive_model_v8(artifact, feature_map, source_hint="roi_original")

    assert 0.0 <= prediction["anemia_risk"] <= 1.0
    assert 0.0 <= prediction["uncertainty"] <= 1.0
    assert prediction["predicted_hemoglobin"] > 12.5
    assert prediction["decision_threshold"] == 0.48
