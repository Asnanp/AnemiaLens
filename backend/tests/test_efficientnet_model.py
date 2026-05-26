from __future__ import annotations

import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml import efficientnet_model


class _FakeEfficientNetModel:
    def __init__(self, architecture: str) -> None:
        self.architecture = architecture
        self.loaded = False
        self.device = None
        self.eval_called = False

    def load_state_dict(self, state_dict, strict: bool = True):
        detected = efficientnet_model._detect_checkpoint_architecture(state_dict)
        if detected != self.architecture:
            raise RuntimeError(f"expected {self.architecture}, got {detected}")
        self.loaded = True

    def to(self, device):
        self.device = device
        return self

    def eval(self):
        self.eval_called = True
        return self


def test_detect_checkpoint_architecture_recognizes_legacy_shape() -> None:
    state_dict = {
        "features.spatial_attention.conv.weight": torch.zeros((1, 2, 7, 7)),
        "classifier.9.weight": torch.zeros((2, 128)),
    }

    architecture = efficientnet_model._detect_checkpoint_architecture(state_dict)

    assert architecture == efficientnet_model.EFFICIENTNET_ARCHITECTURE_LEGACY


def test_load_efficientnet_checkpoint_uses_legacy_compatibility_path(monkeypatch) -> None:
    state_dict = {
        "features.spatial_attention.conv.weight": torch.zeros((1, 2, 7, 7)),
        "classifier.9.weight": torch.zeros((2, 128)),
    }
    checkpoint = {
        "version": efficientnet_model.EFFICIENTNET_VERSION,
        "state_dict": state_dict,
        "decision_threshold": 0.68,
        "hb_mean": 12.1,
        "hb_std": 1.7,
    }

    monkeypatch.setattr(efficientnet_model.torch, "load", lambda *args, **kwargs: checkpoint)
    monkeypatch.setattr(
        efficientnet_model,
        "build_efficientnet_model",
        lambda *, pretrained, architecture: _FakeEfficientNetModel(architecture),
    )

    bundle = efficientnet_model.load_efficientnet_checkpoint("legacy-checkpoint.pth")

    assert bundle["architecture"] == efficientnet_model.EFFICIENTNET_ARCHITECTURE_LEGACY
    assert bundle["decision_threshold"] == 0.68
    assert bundle["hb_mean"] == 12.1
    assert bundle["hb_std"] == 1.7
    assert bundle["model"].loaded is True
    assert bundle["model"].eval_called is True
