from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from app.ml.archive_model import clamp
from app.ml.calibration import CompositeCalibrator

SourceHint = Literal["roi_original", "palpebral", "forniceal_palpebral"]


@dataclass
class RuntimeRiskCalibrator:
    version: str = "runtime-risk-calibrator-v1"
    method: str = "temperature"
    calibrator: CompositeCalibrator = field(
        default_factory=lambda: CompositeCalibrator(method="temperature")
    )
    blend_alpha: float = 1.0
    source_thresholds: dict[str, float] = field(default_factory=dict)
    report: dict[str, object] = field(default_factory=dict)

    def calibrate(
        self,
        probability: float,
        *,
        source_hint: SourceHint = "roi_original",
    ) -> float:
        _ = source_hint
        calibrated = float(self.calibrator.calibrate(probability))
        blended = ((1.0 - float(self.blend_alpha)) * float(probability)) + (
            float(self.blend_alpha) * calibrated
        )
        return clamp(blended, 0.0, 1.0)

    def calibrate_array(self, probabilities):
        import numpy as np

        probabilities = np.asarray(probabilities, dtype=np.float32)
        calibrated = np.asarray(
            self.calibrator.calibrate_array(probabilities),
            dtype=np.float32,
        )
        return np.clip(
            ((1.0 - float(self.blend_alpha)) * probabilities)
            + (float(self.blend_alpha) * calibrated),
            0.0,
            1.0,
        )

    def threshold_for_source(
        self,
        source_hint: SourceHint,
        *,
        fallback: float,
    ) -> float:
        return float(self.source_thresholds.get(source_hint, fallback))

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            pickle.dump(self, handle)

    @classmethod
    def load(cls, path: str | Path) -> "RuntimeRiskCalibrator":
        with Path(path).open("rb") as handle:
            return pickle.load(handle)
