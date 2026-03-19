"""
Lightweight fallback model for AnemiaLens.

Used when:
- Available RAM < 512MB (Render free tier)
- Inference time budget is tight
- Primary model artifacts are unavailable

Strategy: MobileNetV2-based shallow CNN (torchvision) with a minimal head.
Falls back to feature-only heuristic if torch is unavailable.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


# ---------------------------------------------------------------------------
# Memory / Budget Detection
# ---------------------------------------------------------------------------

def available_memory_mb() -> float:
    """Estimate available RAM in MB. Returns 9999 if psutil not installed."""
    try:
        import psutil
        return psutil.virtual_memory().available / (1024 * 1024)
    except ImportError:
        return 9999.0


def should_use_lightweight(
    available_memory_mb_val: float | None = None,
    inference_time_budget_ms: float = 5000,
) -> bool:
    """
    Returns True if the lightweight model should be used.

    Triggers when:
    - Available RAM < 512MB, OR
    - Inference budget is very tight (< 800ms)
    """
    mem = available_memory_mb_val if available_memory_mb_val is not None else available_memory_mb()
    if mem < 512:
        return True
    if inference_time_budget_ms < 800:
        return True
    return False


# ---------------------------------------------------------------------------
# Lightweight Model (MobileNetV2-based)
# ---------------------------------------------------------------------------

LIGHTWEIGHT_VERSION = "mobilenetv2-anemia-v1"
_LIGHTWEIGHT_IMAGE_SIZE = 160  # smaller than EfficientNet's 224


def build_lightweight_model() -> "Any":
    """Build a MobileNetV2 model with a minimal anemia-screening head."""
    import torch
    from torch import nn
    from torchvision.models import MobileNet_V2_Weights, mobilenet_v2

    model = mobilenet_v2(weights=MobileNet_V2_Weights.IMAGENET1K_V1)

    # Freeze all backbone layers
    for param in model.parameters():
        param.requires_grad = False

    # Unfreeze last 2 inverted residual blocks for fine-tuning
    for name, param in model.features.named_parameters():
        if name.startswith(("17", "18")):
            param.requires_grad = True

    # Replace classifier: 1280 → 64 → 2 (risk + Hb)
    model.classifier = nn.Sequential(
        nn.Dropout(0.25),
        nn.Linear(1280, 64),
        nn.ReLU(),
        nn.Linear(64, 2),
    )
    return model


def load_lightweight_model(
    path: str | Path,
    *,
    map_location: str = "cpu",
) -> dict[str, Any] | None:
    """Load a saved lightweight model checkpoint. Returns None if not found."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        import torch
        from torchvision import transforms

        checkpoint = torch.load(path, map_location=map_location)
        model = build_lightweight_model()
        state = checkpoint.get("state_dict", checkpoint)
        model.load_state_dict(state, strict=False)
        model.eval()

        transform = transforms.Compose([
            transforms.Resize((_LIGHTWEIGHT_IMAGE_SIZE, _LIGHTWEIGHT_IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

        return {
            "version": checkpoint.get("version", LIGHTWEIGHT_VERSION),
            "model": model,
            "transform": transform,
            "hb_mean": float(checkpoint.get("hb_mean", 12.5)),
            "hb_std": float(checkpoint.get("hb_std", 2.0)),
            "decision_threshold": float(checkpoint.get("decision_threshold", 0.5)),
            "device": torch.device(map_location),
        }
    except Exception:
        return None


def predict_lightweight(
    image: Image.Image,
    bundle: dict[str, Any],
) -> dict[str, float]:
    """Fast inference using the lightweight model."""
    import torch

    model = bundle["model"]
    transform = bundle["transform"]
    hb_mean = float(bundle.get("hb_mean", 12.5))
    hb_std = float(bundle.get("hb_std", 2.0))
    device = bundle["device"]

    rgb = image.convert("RGB")
    tensor = transform(rgb).unsqueeze(0).to(device)

    with torch.no_grad():
        out = model(tensor)
        risk = float(torch.sigmoid(out[:, 0]).item())
        hb = float(out[:, 1].item() * max(hb_std, 1e-6) + hb_mean)

    # Lightweight model has higher base uncertainty
    margin_uncertainty = 1.0 - min(1.0, abs(risk - 0.5) * 2.0)
    uncertainty = float(np.clip(0.15 + margin_uncertainty * 0.35, 0.15, 0.75))

    return {
        "anemia_risk": float(np.clip(risk, 0.0, 1.0)),
        "predicted_hemoglobin": float(np.clip(hb, 6.0, 18.0)),
        "uncertainty": uncertainty,
        "decision_threshold": float(bundle.get("decision_threshold", 0.5)),
        "model_source": bundle.get("version", LIGHTWEIGHT_VERSION),
    }


# ---------------------------------------------------------------------------
# Feature-Only Heuristic Fallback (no torch required)
# ---------------------------------------------------------------------------

def predict_heuristic(feature_map: dict[str, float], symptom_score: float = 0.0) -> dict[str, float]:
    """
    Pure feature-based heuristic when no model is available at all.
    Uses CPI (Conjunctival Pallor Index) and red-green gap as primary signals.
    Incorporates symptom_score to adjust Hb estimate when symptoms are present.
    This is a last-resort fallback — uncertainty is always high.
    """
    cpi = feature_map.get("cpi", feature_map.get("mean_r", 0.4))
    center_cpi = feature_map.get("center_cpi", feature_map.get("center_mean_r", 0.4))
    rg_gap = feature_map.get("red_green_gap", 0.0)
    center_rg_gap = feature_map.get("center_red_green_gap", 0.0)
    brightness = feature_map.get("brightness", 0.3)

    # Pallor signal: low CPI + low R-G gap → anemia likely
    # Normal CPI ~ 0.38-0.45; anemic < 0.35
    pallor_signal = max(0.0, (0.40 - center_cpi) / 0.15)
    rg_signal = max(0.0, (0.04 - center_rg_gap) / 0.08)

    # Brightness penalty: very dark images are unreliable
    brightness_ok = 0.08 <= brightness <= 0.55
    quality_factor = 0.7 if brightness_ok else 0.4

    raw_risk = float(np.clip((pallor_signal * 0.6 + rg_signal * 0.4) * quality_factor, 0.0, 1.0))

    # Symptom-adjusted risk: symptoms can push risk up even if image is ambiguous
    # symptom_score of 1.0 (all symptoms) adds up to 0.35 to raw_risk
    combined_risk = float(np.clip(raw_risk * 0.65 + symptom_score * 0.35, 0.0, 1.0))

    # Heuristic Hb estimate: linear mapping from CPI + symptom adjustment
    # CPI 0.45 → ~14 g/dL, CPI 0.30 → ~9 g/dL
    # Symptoms lower the Hb estimate: all symptoms → up to -2.5 g/dL adjustment
    image_hb = float(np.clip(9.0 + (center_cpi - 0.30) / 0.15 * 5.0, 6.0, 18.0))
    symptom_hb_penalty = symptom_score * 2.5  # max -2.5 g/dL when all symptoms present
    estimated_hb = float(np.clip(image_hb - symptom_hb_penalty, 6.0, 18.0))

    return {
        "anemia_risk": combined_risk,
        "predicted_hemoglobin": estimated_hb,
        "uncertainty": 0.55,  # slightly lower than before — symptoms add signal
        "decision_threshold": 0.5,
        "model_source": "heuristic-cpi-v1",
    }


class LightweightScreeningModel:
    """
    Unified interface for the lightweight inference path.
    Tries MobileNetV2 first, falls back to CPI heuristic.
    """

    def __init__(self, artifact_path: str | Path | None = None) -> None:
        self._bundle: dict[str, Any] | None = None
        if artifact_path is not None:
            self._bundle = load_lightweight_model(artifact_path)

    @property
    def is_ready(self) -> bool:
        return self._bundle is not None

    def predict(self, image: Image.Image, feature_map: dict[str, float], symptom_score: float = 0.0) -> dict[str, float]:
        if self._bundle is not None:
            try:
                return predict_lightweight(image, self._bundle)
            except Exception:
                pass
        return predict_heuristic(feature_map, symptom_score=symptom_score)

    def version(self) -> str:
        if self._bundle is not None:
            return str(self._bundle.get("version", LIGHTWEIGHT_VERSION))
        return "heuristic-cpi-v1"
