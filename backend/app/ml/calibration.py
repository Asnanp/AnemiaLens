"""
Probability calibration for AnemiaLens.

Implements:
- Temperature scaling (post-hoc, single parameter, no data leakage)
- Isotonic regression calibration (sklearn-based, more flexible)
- Platt scaling (logistic regression on raw scores)
- Reliability diagram computation for diagnostics

Temperature scaling is the default — it's the most reliable for medical
screening because it preserves ranking while correcting overconfidence.
"""
from __future__ import annotations

import math
import pickle
from pathlib import Path
from typing import Literal

import numpy as np


# ---------------------------------------------------------------------------
# Temperature Scaling
# ---------------------------------------------------------------------------

class TemperatureScaler:
    """
    Single-parameter post-hoc calibration.
    T > 1 → softer (less confident), T < 1 → sharper.
    Fit on a held-out calibration set using NLL minimisation.
    """

    def __init__(self, temperature: float = 1.0) -> None:
        self.temperature = max(temperature, 1e-4)

    def fit(self, logits: np.ndarray, labels: np.ndarray) -> "TemperatureScaler":
        """
        Fit temperature by minimising NLL on calibration logits.
        logits: raw pre-sigmoid scores, shape (N,)
        labels: binary ground truth, shape (N,)
        """
        best_t = 1.0
        best_nll = float("inf")
        for t in np.linspace(0.1, 5.0, 490):
            probs = _sigmoid(logits / t)
            probs = np.clip(probs, 1e-7, 1 - 1e-7)
            nll = -float(np.mean(labels * np.log(probs) + (1 - labels) * np.log(1 - probs)))
            if nll < best_nll:
                best_nll = nll
                best_t = float(t)
        self.temperature = best_t
        return self

    def calibrate(self, probability: float) -> float:
        """Apply temperature scaling to a single probability."""
        logit = _logit(probability)
        return float(_sigmoid(np.array([logit / self.temperature]))[0])

    def calibrate_array(self, probabilities: np.ndarray) -> np.ndarray:
        logits = _logit_array(probabilities)
        return _sigmoid(logits / self.temperature)

    def to_dict(self) -> dict[str, float]:
        return {"temperature": self.temperature}

    @classmethod
    def from_dict(cls, d: dict[str, float]) -> "TemperatureScaler":
        return cls(temperature=float(d["temperature"]))


# ---------------------------------------------------------------------------
# Isotonic Regression Calibration
# ---------------------------------------------------------------------------

class IsotonicCalibrator:
    """
    Non-parametric calibration using isotonic regression.
    More flexible than temperature scaling but needs more calibration data.
    Requires sklearn.
    """

    def __init__(self) -> None:
        self._model: object | None = None

    def fit(self, probabilities: np.ndarray, labels: np.ndarray) -> "IsotonicCalibrator":
        from sklearn.isotonic import IsotonicRegression
        self._model = IsotonicRegression(out_of_bounds="clip")
        self._model.fit(probabilities, labels)
        return self

    def calibrate(self, probability: float) -> float:
        if self._model is None:
            return probability
        return float(self._model.predict([probability])[0])

    def calibrate_array(self, probabilities: np.ndarray) -> np.ndarray:
        if self._model is None:
            return probabilities
        return np.array(self._model.predict(probabilities), dtype=np.float32)

    def to_bytes(self) -> bytes:
        return pickle.dumps(self._model)

    @classmethod
    def from_bytes(cls, data: bytes) -> "IsotonicCalibrator":
        obj = cls()
        obj._model = pickle.loads(data)
        return obj


# ---------------------------------------------------------------------------
# Platt Scaling
# ---------------------------------------------------------------------------

class PlattScaler:
    """
    Logistic regression on raw scores — good when you have ~50+ calibration samples.
    """

    def __init__(self, a: float = 1.0, b: float = 0.0) -> None:
        self.a = a
        self.b = b

    def fit(self, scores: np.ndarray, labels: np.ndarray) -> "PlattScaler":
        from sklearn.linear_model import LogisticRegression
        lr = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000)
        lr.fit(scores.reshape(-1, 1), labels)
        self.a = float(lr.coef_[0][0])
        self.b = float(lr.intercept_[0])
        return self

    def calibrate(self, score: float) -> float:
        return float(_sigmoid(np.array([self.a * score + self.b]))[0])

    def to_dict(self) -> dict[str, float]:
        return {"a": self.a, "b": self.b}

    @classmethod
    def from_dict(cls, d: dict[str, float]) -> "PlattScaler":
        return cls(a=float(d["a"]), b=float(d["b"]))


# ---------------------------------------------------------------------------
# Calibration Diagnostics
# ---------------------------------------------------------------------------

def expected_calibration_error(
    probabilities: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 10,
) -> dict[str, object]:
    """
    Compute ECE and reliability diagram data.
    Returns ECE score + per-bin (confidence, accuracy, count).
    """
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    bin_indices = np.digitize(probabilities, bins) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)

    ece = 0.0
    diagram: list[dict[str, float]] = []
    n = len(labels)

    for b in range(n_bins):
        mask = bin_indices == b
        count = int(np.sum(mask))
        if count == 0:
            continue
        avg_conf = float(np.mean(probabilities[mask]))
        avg_acc = float(np.mean(labels[mask]))
        ece += (count / n) * abs(avg_conf - avg_acc)
        diagram.append({"confidence": avg_conf, "accuracy": avg_acc, "count": count})

    return {"ece": round(ece, 4), "diagram": diagram, "n_bins": n_bins}


# ---------------------------------------------------------------------------
# Composite Calibrator — wraps the pipeline
# ---------------------------------------------------------------------------

CalibrationMethod = Literal["temperature", "isotonic", "platt", "none"]


class CompositeCalibrator:
    """
    Drop-in calibration wrapper for the AnemiaLens inference pipeline.

    Usage:
        # At training time:
        cal = CompositeCalibrator(method="temperature")
        cal.fit(raw_probs, labels)
        cal.save("artifacts/calibrator.pkl")

        # At inference time:
        cal = CompositeCalibrator.load("artifacts/calibrator.pkl")
        calibrated_risk = cal.calibrate(raw_risk)
    """

    def __init__(self, method: CalibrationMethod = "temperature") -> None:
        self.method = method
        self._scaler: TemperatureScaler | IsotonicCalibrator | PlattScaler | None = None
        self.ece_before: float | None = None
        self.ece_after: float | None = None

    def fit(
        self,
        probabilities: np.ndarray,
        labels: np.ndarray,
        *,
        logits: np.ndarray | None = None,
    ) -> "CompositeCalibrator":
        diag_before = expected_calibration_error(probabilities, labels)
        self.ece_before = diag_before["ece"]

        if self.method == "temperature":
            if logits is None:
                logits = _logit_array(probabilities)
            self._scaler = TemperatureScaler().fit(logits, labels)
            calibrated = self._scaler.calibrate_array(probabilities)
        elif self.method == "isotonic":
            self._scaler = IsotonicCalibrator().fit(probabilities, labels)
            calibrated = self._scaler.calibrate_array(probabilities)
        elif self.method == "platt":
            self._scaler = PlattScaler().fit(probabilities, labels)
            calibrated = np.array([self._scaler.calibrate(p) for p in probabilities])
        else:
            calibrated = probabilities

        diag_after = expected_calibration_error(calibrated, labels)
        self.ece_after = diag_after["ece"]
        return self

    def calibrate(self, probability: float) -> float:
        if self._scaler is None:
            return probability
        return self._scaler.calibrate(probability)

    def calibrate_array(self, probabilities: np.ndarray) -> np.ndarray:
        if self._scaler is None:
            return probabilities
        return self._scaler.calibrate_array(probabilities)

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: str | Path) -> "CompositeCalibrator":
        with open(path, "rb") as f:
            return pickle.load(f)

    def summary(self) -> dict[str, object]:
        return {
            "method": self.method,
            "ece_before": self.ece_before,
            "ece_after": self.ece_after,
            "temperature": self._scaler.temperature if isinstance(self._scaler, TemperatureScaler) else None,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -88, 88)))


def _logit(p: float) -> float:
    p = max(1e-7, min(1 - 1e-7, p))
    return math.log(p / (1 - p))


def _logit_array(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-7, 1 - 1e-7)
    return np.log(p / (1 - p))
