"""
Offline ML integration tests.

These tests require the trained model artefact and the anemia dataset to be
present on disk — they are intentionally skipped in environments where those
files are absent (CI without model artefacts, fresh developer checkouts).

Use::

    pytest tests/test_offline_ml.py -v --no-header

to run locally after training.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

# ---------------------------------------------------------------------------
# Optional dependency guards
# ---------------------------------------------------------------------------

def _pillow_available() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def _model_artefact_present() -> bool:
    return (ROOT / "backend" / "models" / "archive_screening_model.joblib").exists()


def _efficientnet_artefact_present() -> bool:
    return (ROOT / "backend" / "models" / "efficientnet_anemia.pth").exists()


def _dataset_present() -> bool:
    return (ROOT / "archive" / "dataset anemia").exists()


requires_pillow = pytest.mark.skipif(not _pillow_available(), reason="Pillow not installed")
requires_model = pytest.mark.skipif(not _model_artefact_present(), reason="Model artefact not found")
requires_efficientnet = pytest.mark.skipif(
    not _efficientnet_artefact_present(),
    reason="EfficientNet artefact not found",
)
requires_dataset = pytest.mark.skipif(not _dataset_present(), reason="Dataset not found")


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

@requires_pillow
def test_feature_extraction_returns_expected_feature_set() -> None:
    from PIL import Image
    from app.ml.features import FEATURE_NAMES, extract_eye_features

    image = Image.new("RGB", (320, 180), color=(180, 120, 115))
    features = extract_eye_features(image)

    assert set(FEATURE_NAMES) == set(features), (
        f"Feature mismatch.\n"
        f"  Extra in output : {set(features) - set(FEATURE_NAMES)}\n"
        f"  Missing from output: {set(FEATURE_NAMES) - set(features)}"
    )
    assert features["brightness"] > 0.0, "brightness feature should be positive for a non-black image"


@requires_pillow
def test_feature_extraction_values_in_valid_ranges() -> None:
    from PIL import Image
    from app.ml.features import extract_eye_features

    image = Image.new("RGB", (320, 180), color=(180, 120, 115))
    features = extract_eye_features(image)

    for name, value in features.items():
        assert isinstance(value, (int, float)), f"Feature '{name}' is not numeric: {value!r}"
        assert not (value != value), f"Feature '{name}' is NaN"  # NaN check


# ---------------------------------------------------------------------------
# Model loading and prediction
# ---------------------------------------------------------------------------

MODEL_PATH = ROOT / "backend" / "models" / "archive_screening_model.joblib"
DATASET_PATH = ROOT / "archive" / "dataset anemia"


@requires_pillow
@requires_model
def test_archive_model_predicts_valid_probability_ranges() -> None:
    from PIL import Image
    from app.ml.archive_model import ARCHIVE_VERSION, load_archive_model, predict_with_archive_model
    from app.ml.features import extract_eye_features, load_image_path
    from app.services.conjunctiva_roi import ConjunctivaRoiExtractor

    artifact = load_archive_model(MODEL_PATH)

    sample = next(DATASET_PATH.glob("*/*/*.jpg"), None)
    if sample is None:
        pytest.skip("No JPEG images found in dataset directory")

    roi = ConjunctivaRoiExtractor().extract(load_image_path(sample)).image
    prediction = predict_with_archive_model(
        artifact,
        extract_eye_features(roi),
        source_hint="roi_original",
    )

    assert artifact["version"] == ARCHIVE_VERSION, (
        f"Artefact version mismatch: {artifact['version']} != {ARCHIVE_VERSION}"
    )
    assert 0.0 <= prediction["anemia_risk"] <= 1.0, "anemia_risk out of [0, 1]"
    assert 0.0 <= prediction["uncertainty"] <= 1.0, "uncertainty out of [0, 1]"
    assert prediction["predicted_hemoglobin"] > 5.0, (
        f"predicted_hemoglobin={prediction['predicted_hemoglobin']} is implausibly low"
    )


@requires_pillow
@requires_model
def test_archive_model_prediction_fields_all_present() -> None:
    """Regression test: ensure no required output fields are accidentally dropped."""
    from PIL import Image
    from app.ml.archive_model import load_archive_model, predict_with_archive_model
    from app.ml.features import extract_eye_features

    artifact = load_archive_model(MODEL_PATH)
    image = Image.new("RGB", (320, 180), color=(180, 120, 115))
    prediction = predict_with_archive_model(
        artifact,
        extract_eye_features(image),
        source_hint="synthetic",
    )

    required_keys = {"anemia_risk", "uncertainty", "predicted_hemoglobin"}
    missing = required_keys - set(prediction.keys())
    assert not missing, f"Prediction is missing keys: {missing}"


# ---------------------------------------------------------------------------
# Training report schema
# ---------------------------------------------------------------------------

REPORT_PATH = ROOT / "backend" / "models" / "training_report.json"
EFFICIENTNET_PATH = ROOT / "backend" / "models" / "efficientnet_anemia.pth"


@pytest.mark.skipif(not REPORT_PATH.exists(), reason="training_report.json not found")
def test_training_report_matches_archive_model_version() -> None:
    from app.ml.archive_model import ARCHIVE_VERSION
    from app.ml.efficientnet_model import EFFICIENTNET_VERSION

    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert report["primary_model"] in {ARCHIVE_VERSION, EFFICIENTNET_VERSION}, (
        f"Unexpected primary_model={report['primary_model']!r}"
    )


@pytest.mark.skipif(not REPORT_PATH.exists(), reason="training_report.json not found")
def test_training_report_minimum_dataset_size() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert report["subject_count"] >= 200, "Dataset has too few subjects to be reliable"
    assert report["record_count"] >= report["subject_count"], (
        "record_count must be >= subject_count"
    )


@pytest.mark.skipif(not REPORT_PATH.exists(), reason="training_report.json not found")
def test_training_report_metrics_meet_minimum_bar() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    metrics = report["metrics"]

    assert metrics["split_strategy"] in {"group-shuffle-repeat", "group-shuffle-balance-select"}, (
        f"Unexpected split_strategy {metrics['split_strategy']!r}"
    )
    assert metrics["validation_size"] > 30, "Validation set is too small"
    assert metrics["accuracy"] > 0.6, f"accuracy={metrics['accuracy']:.3f} below threshold"
    assert metrics["f1"] > 0.45, f"f1={metrics['f1']:.3f} below threshold"


@pytest.mark.skipif(not REPORT_PATH.exists(), reason="training_report.json not found")
def test_training_report_selected_mode_is_valid() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    valid_modes = {"roi_primary", "hybrid_dual", "efficientnet_hybrid_dual"}
    assert report["selected_mode"] in valid_modes, (
        f"selected_mode={report['selected_mode']!r} not in {valid_modes}"
    )


@requires_pillow
@requires_efficientnet
def test_efficientnet_checkpoint_loads_and_predicts() -> None:
    from PIL import Image
    from app.ml.efficientnet_model import (
        EFFICIENTNET_VERSION,
        load_efficientnet_checkpoint,
        predict_with_efficientnet_model,
    )

    bundle = load_efficientnet_checkpoint(EFFICIENTNET_PATH)
    prediction = predict_with_efficientnet_model(
        bundle,
        Image.new("RGB", (320, 180), color=(180, 120, 115)),
        mc_passes=2,
    )

    assert bundle["version"] == EFFICIENTNET_VERSION
    assert 0.0 <= prediction["anemia_risk"] <= 1.0
    assert 0.0 <= prediction["uncertainty"] <= 1.0


@requires_pillow
def test_single_pass_efficientnet_prediction_is_deterministic() -> None:
    from PIL import Image
    import torch
    from torch import nn

    from app.ml.efficientnet_model import predict_with_efficientnet_model

    class TinyDropoutModel(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.flatten = nn.Flatten()
            self.dropout = nn.Dropout(p=0.95)
            self.linear = nn.Linear(3 * 4 * 4, 2)

        def forward(self, tensor: torch.Tensor) -> torch.Tensor:
            x = self.flatten(tensor)
            x = self.dropout(x)
            return self.linear(x)

    torch.manual_seed(7)
    model = TinyDropoutModel()
    bundle = {
        "model": model,
        "device": torch.device("cpu"),
        "transform": lambda image: torch.ones((3, 4, 4), dtype=torch.float32),
        "hb_mean": 12.0,
        "hb_std": 1.0,
        "decision_threshold": 0.5,
    }
    image = Image.new("RGB", (16, 16), color=(180, 120, 115))

    first = predict_with_efficientnet_model(bundle, image, mc_passes=1)
    second = predict_with_efficientnet_model(bundle, image, mc_passes=1)

    assert first["anemia_risk"] == second["anemia_risk"]
    assert first["predicted_hemoglobin"] == second["predicted_hemoglobin"]
