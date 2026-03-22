from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


EFFICIENTNET_VERSION = "efficientnet-b0-ft-v2"
IMAGE_SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def build_efficientnet_model(*, pretrained: bool = True):
    from torch import nn
    from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0

    weights = EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None
    model = efficientnet_b0(weights=weights)
    model.classifier = nn.Sequential(
        nn.Dropout(0.35),
        nn.Linear(1280, 512),
        nn.GELU(),
        nn.Dropout(0.25),
        nn.Linear(512, 128),
        nn.GELU(),
        nn.Dropout(0.15),
        nn.Linear(128, 2),
    )

    for param in model.features.parameters():
        param.requires_grad = False
    for name, param in model.features.named_parameters():
        if name.startswith(("4", "5", "6", "7", "8")):
            param.requires_grad = True
    for param in model.classifier.parameters():
        param.requires_grad = True
    return model


def build_train_transform():
    from torchvision import transforms

    return transforms.Compose(
        [
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(p=0.15),
            transforms.ColorJitter(
                brightness=0.4,
                contrast=0.4,
                saturation=0.3,
                hue=0.05,
            ),
            transforms.RandomRotation(20),
            transforms.RandomAffine(
                degrees=0,
                translate=(0.12, 0.12),
                scale=(0.88, 1.12),
            ),
            transforms.RandomPerspective(distortion_scale=0.15, p=0.3),
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
            transforms.RandomErasing(
                p=0.25,
                scale=(0.02, 0.12),
                ratio=(0.3, 3.3),
            ),
        ]
    )


def build_val_transform():
    from torchvision import transforms

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
    map_location: str = "cpu",
) -> dict[str, Any]:
    import torch

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
    import torch

    model = bundle["model"]
    device = bundle["device"]
    transform = bundle["transform"]
    hb_mean = float(bundle.get("hb_mean", 0.0))
    hb_std_scale = max(float(bundle.get("hb_std", 1.0)), 1e-6)

    rgb = image.convert("RGB")
    tta_images = [
        rgb,
        rgb.transpose(Image.FLIP_LEFT_RIGHT),
    ]

    probabilities: list[float] = []
    hemoglobin_values: list[float] = []

    with torch.no_grad():
        for tta_img in tta_images:
            tensor = transform(tta_img).unsqueeze(0).to(device)
            for _ in range(max(mc_passes, 1)):
                model.eval()
                if mc_passes > 1:
                    _enable_dropout(model)
                output = model(tensor)
                probabilities.append(float(torch.sigmoid(output[:, 0]).item()))
                hemoglobin_values.append(
                    float((output[:, 1].item() * hb_std_scale) + hb_mean)
                )

    mean_probability = float(np.mean(probabilities))
    mean_hemoglobin = float(np.mean(hemoglobin_values))
    probability_std = float(np.std(probabilities))
    hemoglobin_std = float(np.std(hemoglobin_values))

    margin_uncertainty = 1.0 - min(1.0, abs(mean_probability - 0.5) * 2.5)
    uncertainty = clamp(
        (probability_std * 2.2)
        + (min(hemoglobin_std / 2.0, 1.0) * 0.30)
        + (margin_uncertainty * 0.18),
        0.04,
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


def _enable_dropout(model) -> None:
    from torch import nn

    for module in model.modules():
        if isinstance(module, nn.Dropout):
            module.train()
