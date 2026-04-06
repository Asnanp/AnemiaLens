from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.calibration import (  # noqa: E402
    CompositeCalibrator,
    PlattScaler,
)


def test_platt_scaler_calibrate_array_returns_probabilities() -> None:
    scaler = PlattScaler(a=2.0, b=-0.5)
    scores = np.asarray([0.1, 0.4, 0.9], dtype=np.float32)

    calibrated = scaler.calibrate_array(scores)

    assert calibrated.shape == scores.shape
    assert np.all(calibrated >= 0.0)
    assert np.all(calibrated <= 1.0)
    assert calibrated[0] < calibrated[1] < calibrated[2]


def test_composite_calibrator_platt_supports_array_calibration() -> None:
    probabilities = np.asarray([0.08, 0.12, 0.21, 0.64, 0.78, 0.91], dtype=np.float32)
    labels = np.asarray([0, 0, 0, 1, 1, 1], dtype=np.int32)

    calibrator = CompositeCalibrator(method="platt").fit(probabilities, labels)
    calibrated = calibrator.calibrate_array(probabilities)

    assert calibrated.shape == probabilities.shape
    assert np.all(calibrated >= 0.0)
    assert np.all(calibrated <= 1.0)
    assert calibrated[0] < calibrated[1] < calibrated[2]
    assert calibrated[2] < calibrated[3] < calibrated[4] < calibrated[5]


def test_temperature_scaler_preserves_probability_shape() -> None:
    probabilities = np.asarray([0.11, 0.42, 0.87], dtype=np.float32)
    labels = np.asarray([0, 0, 1], dtype=np.int32)

    calibrator = CompositeCalibrator(method="temperature").fit(probabilities, labels)
    calibrated = calibrator.calibrate_array(probabilities)

    assert calibrated.shape == probabilities.shape
    assert np.all(calibrated >= 0.0)
    assert np.all(calibrated <= 1.0)
