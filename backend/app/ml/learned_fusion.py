"""
Learned feature fusion for AnemiaLens.

Replaces the static 55/45 image/symptom weighting with a small
3-layer MLP trained on historical screening data.

Pure numpy — no torch dependency. CPU-safe, <1ms inference.

Input features (5):
  [image_risk, uncertainty, symptom_score, symptom_count, has_severe_symptoms]

Architecture:
  Linear(5→16) → ReLU → Linear(16→8) → ReLU → Linear(8→1) → Sigmoid
"""
from __future__ import annotations

import math
import pickle
from pathlib import Path
from typing import NamedTuple

import numpy as np


# ---------------------------------------------------------------------------
# MLP Layers (pure numpy)
# ---------------------------------------------------------------------------

class _Linear:
    def __init__(self, w: np.ndarray, b: np.ndarray) -> None:
        self.w = w  # (out, in)
        self.b = b  # (out,)

    def forward(self, x: np.ndarray) -> np.ndarray:
        return x @ self.w.T + self.b


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0.0, x)


def _sigmoid_np(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -88, 88)))


# ---------------------------------------------------------------------------
# Learned Fusion Model
# ---------------------------------------------------------------------------

class LearnedFusionModel:
    """
    Tiny MLP for image+symptom fusion.
    Falls back to static weights if not trained.
    """

    INPUT_DIM = 5
    STATIC_IMAGE_WEIGHT = 0.55
    STATIC_SYMPTOM_WEIGHT = 0.45

    def __init__(self) -> None:
        self._layers: list[_Linear] | None = None
        self.trained = False
        self.feature_names = [
            "image_risk",
            "uncertainty",
            "symptom_score",
            "symptom_count",
            "has_severe_symptoms",
        ]
        # Normalisation stats (set during training)
        self._mean = np.zeros(self.INPUT_DIM, dtype=np.float32)
        self._std = np.ones(self.INPUT_DIM, dtype=np.float32)

    def predict(
        self,
        image_risk: float,
        uncertainty: float,
        symptom_score: float,
        symptom_count: int,
        has_severe_symptoms: bool,
    ) -> float:
        """Returns fused risk score in [0, 1]."""
        if not self.trained or self._layers is None:
            return self._static_fusion(image_risk, symptom_score)

        x = np.array(
            [image_risk, uncertainty, symptom_score, float(symptom_count), float(has_severe_symptoms)],
            dtype=np.float32,
        )
        x = (x - self._mean) / (self._std + 1e-8)

        h = x
        for i, layer in enumerate(self._layers):
            h = layer.forward(h)
            if i < len(self._layers) - 1:
                h = _relu(h)
        return float(_sigmoid_np(h)[0])

    def _static_fusion(self, image_risk: float, symptom_score: float) -> float:
        return float(np.clip(
            image_risk * self.STATIC_IMAGE_WEIGHT + symptom_score * self.STATIC_SYMPTOM_WEIGHT,
            0.0, 1.0,
        ))

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: str | Path) -> "LearnedFusionModel":
        with open(path, "rb") as f:
            return pickle.load(f)

    def summary(self) -> dict[str, object]:
        return {
            "trained": self.trained,
            "input_features": self.feature_names,
            "architecture": "Linear(5→16)→ReLU→Linear(16→8)→ReLU→Linear(8→1)→Sigmoid",
        }


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

class FusionSample(NamedTuple):
    image_risk: float
    uncertainty: float
    symptom_score: float
    symptom_count: int
    has_severe_symptoms: bool
    label: float  # ground truth anemia probability (0 or 1)


def train_fusion_model(
    samples: list[FusionSample],
    *,
    epochs: int = 300,
    lr: float = 0.01,
    random_state: int = 42,
) -> LearnedFusionModel:
    """
    Train the fusion MLP using mini-batch SGD with Adam-style updates.
    Requires at least 20 samples; falls back to static weights otherwise.
    """
    model = LearnedFusionModel()

    if len(samples) < 20:
        return model  # not enough data, use static fallback

    rng = np.random.default_rng(random_state)

    X = np.array(
        [[s.image_risk, s.uncertainty, s.symptom_score, float(s.symptom_count), float(s.has_severe_symptoms)]
         for s in samples],
        dtype=np.float32,
    )
    y = np.array([s.label for s in samples], dtype=np.float32)

    # Normalise
    mean = X.mean(axis=0)
    std = X.std(axis=0) + 1e-8
    X_norm = (X - mean) / std

    # Initialise weights (He init)
    def _he(fan_in: int, fan_out: int) -> tuple[np.ndarray, np.ndarray]:
        scale = math.sqrt(2.0 / fan_in)
        return rng.normal(0, scale, (fan_out, fan_in)).astype(np.float32), np.zeros(fan_out, dtype=np.float32)

    w1, b1 = _he(5, 16)
    w2, b2 = _he(16, 8)
    w3, b3 = _he(8, 1)

    # Adam state
    params = [w1, b1, w2, b2, w3, b3]
    m = [np.zeros_like(p) for p in params]
    v = [np.zeros_like(p) for p in params]
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    t = 0

    n = len(X_norm)
    batch_size = min(32, n)

    for epoch in range(epochs):
        idx = rng.permutation(n)
        for start in range(0, n, batch_size):
            batch_idx = idx[start: start + batch_size]
            xb = X_norm[batch_idx]
            yb = y[batch_idx]

            # Forward
            z1 = xb @ w1.T + b1
            a1 = np.maximum(0, z1)
            z2 = a1 @ w2.T + b2
            a2 = np.maximum(0, z2)
            z3 = a2 @ w3.T + b3
            out = _sigmoid_np(z3).squeeze(-1)

            # BCE loss gradient
            dout = (out - yb) / len(yb)  # (batch,)

            # Backprop layer 3
            dz3 = dout[:, None]  # (batch, 1)
            dw3 = dz3.T @ a2
            db3 = dz3.sum(axis=0)
            da2 = dz3 @ w3

            # Backprop layer 2
            dz2 = da2 * (z2 > 0)
            dw2 = dz2.T @ a1
            db2 = dz2.sum(axis=0)
            da1 = dz2 @ w2

            # Backprop layer 1
            dz1 = da1 * (z1 > 0)
            dw1 = dz1.T @ xb
            db1 = dz1.sum(axis=0)

            grads = [dw1, db1, dw2, db2, dw3, db3]
            t += 1
            for i, (p, g) in enumerate(zip(params, grads)):
                m[i] = beta1 * m[i] + (1 - beta1) * g
                v[i] = beta2 * v[i] + (1 - beta2) * g ** 2
                m_hat = m[i] / (1 - beta1 ** t)
                v_hat = v[i] / (1 - beta2 ** t)
                p -= lr * m_hat / (np.sqrt(v_hat) + eps)

    model._layers = [_Linear(w1, b1), _Linear(w2, b2), _Linear(w3, b3)]
    model._mean = mean
    model._std = std
    model.trained = True
    return model


# ---------------------------------------------------------------------------
# Fusion Explainer
# ---------------------------------------------------------------------------

class FusionExplainer:
    """
    Returns approximate feature importance via input perturbation.
    Works for both trained and untrained (static) models.
    """

    def explain(
        self,
        model: LearnedFusionModel,
        image_risk: float,
        uncertainty: float,
        symptom_score: float,
        symptom_count: int,
        has_severe_symptoms: bool,
        *,
        delta: float = 0.05,
    ) -> dict[str, float]:
        base = model.predict(image_risk, uncertainty, symptom_score, symptom_count, has_severe_symptoms)
        inputs = [image_risk, uncertainty, symptom_score, float(symptom_count), float(has_severe_symptoms)]
        importances: dict[str, float] = {}

        for i, name in enumerate(model.feature_names):
            perturbed = inputs.copy()
            perturbed[i] = min(1.0, inputs[i] + delta)
            perturbed_score = model.predict(*perturbed[:3], int(perturbed[3]), bool(perturbed[4]))
            importances[name] = round(abs(perturbed_score - base) / delta, 4)

        # Normalise to sum to 1
        total = sum(importances.values()) + 1e-9
        return {k: round(v / total, 4) for k, v in importances.items()}
