from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image
from torch import nn
from torchvision import transforms
from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0


EFFICIENTNET_VERSION = "efficientnet-b0-ft"
IMAGE_SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def build_efficientnet_model(*, pretrained: bool = True) -> nn.Module:
    weights = EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None
    model = efficientnet_b0(weights=weights)
    model.classifier = nn.Sequential(
        nn.Dropout(0.4),
        nn.Linear(1280, 256),
        nn.ReLU(),
        nn.Dropout(0.2),
        nn.Linear(256, 2),
    )

    for param in model.features.parameters():
        param.requires_grad = False
    for name, param in model.features.named_parameters():
        if name.startswith(("6", "7", "8")):
            param.requires_grad = True
    for param in model.classifier.parameters():
        param.requires_grad = True
    return model


def build_train_transform() -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
            transforms.RandomRotation(15),
            transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )


def build_val_transform() -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )


def load_efficientnet_checkpoint(
    path: str | Path,
    *,
    map_location: str | torch.device = "cpu",
) -> dict[str, Any]:
    checkpoint = torch.load(path, map_location=map_location)
    model = build_efficientnet_model(pretrained=False)
    state_dict = checkpoint["state_dict"] if "state_dict" in checkpoint else checkpoint
    model.load_state_dict(state_dict)
    device = torch.device(map_location)
    model.to(device)
    model.eval()
    return {
        "version": checkpoint.get("version", EFFICIENTNET_VERSION),
        "created_at": checkpoint.get("created_at"),
        "decision_threshold": float(checkpoint.get("decision_threshold", 0.5)),
        "hb_mean": float(checkpoint.get("hb_mean", 0.0)),
        "hb_std": float(checkpoint.get("hb_std", 1.0)),
        "val_metrics": checkpoint.get("val_metrics"),
        "model": model,
        "device": device,
        "transform": build_val_transform(),
    }


def predict_with_efficientnet_model(
    bundle: dict[str, Any],
    image: Image.Image,
    *,
    mc_passes: int = 10,
) -> dict[str, float]:
    model: nn.Module = bundle["model"]
    device: torch.device = bundle["device"]
    transform = bundle["transform"]
    tensor = transform(image.convert("RGB")).unsqueeze(0).to(device)
    hb_mean = float(bundle.get("hb_mean", 0.0))
    hb_std_scale = max(float(bundle.get("hb_std", 1.0)), 1e-6)

    probabilities: list[float] = []
    hemoglobin_values: list[float] = []

    with torch.no_grad():
        for _ in range(max(mc_passes, 1)):
            model.eval()
            if mc_passes > 1:
                _enable_dropout(model)
            output = model(tensor)
            probabilities.append(float(torch.sigmoid(output[:, 0]).item()))
            hemoglobin_values.append(float((output[:, 1].item() * hb_std_scale) + hb_mean))

    mean_probability = float(np.mean(probabilities))
    mean_hemoglobin = float(np.mean(hemoglobin_values))
    probability_std = float(np.std(probabilities))
    hemoglobin_std = float(np.std(hemoglobin_values))
    margin_uncertainty = 1.0 - min(1.0, abs(mean_probability - 0.5) * 2.0)
    uncertainty = clamp(
        (probability_std * 2.4)
        + (min(hemoglobin_std / 2.5, 1.0) * 0.35)
        + (margin_uncertainty * 0.2),
        0.05,
        0.95,
    )

    model.eval()
    return {
        "anemia_risk": mean_probability,
        "predicted_hemoglobin": mean_hemoglobin,
        "uncertainty": uncertainty,
        "decision_threshold": float(bundle.get("decision_threshold", 0.5)),
        "probability_std": probability_std,
        "hemoglobin_std": hemoglobin_std,
    }


def _enable_dropout(model: nn.Module) -> None:
    for module in model.modules():
        if isinstance(module, nn.Dropout):
            module.train()
