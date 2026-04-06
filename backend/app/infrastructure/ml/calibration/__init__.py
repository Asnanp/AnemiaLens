"""
Calibration layer — risk calibration, hemoglobin calibration, refinement.

This module isolates all probability calibration logic from the
prediction service so that:
- Calibration methods can be swapped without touching inference
- Calibrators can be tested in isolation
- New calibration strategies (e.g., v8, v9) can be added cleanly

Usage:
    calibrator = RiskCalibrator(model_loader)
    calibrated_risk = calibrator.calibrate_risk(raw_risk, source_hint="roi_original")
"""

from __future__ import annotations

import logging
from typing import Literal

from app.schemas import QualityAssessment

log = logging.getLogger("anemialens.infrastructure.ml.calibration")

SourceHint = Literal["roi_original", "palpebral", "forniceal_palpebral"]


def clamp(value: float, low: float, high: float) -> float:
    """Clamp a float to [low, high]."""
    return max(low, min(high, value))


class RiskCalibrator:
    """
    Wraps runtime risk calibrators to provide a uniform calibration API.

    The underlying calibrator may be a RuntimeRiskCalibrator,
    UltimateRuntimeRefiner, or any other calibrator that supports
    a ``calibrate`` method.
    """

    def __init__(self, calibrator: object | None = None) -> None:
        self._calibrator = calibrator

    def calibrate(
        self,
        raw_risk: float,
        *,
        source_hint: SourceHint = "roi_original",
    ) -> float:
        """
        Calibrate a raw anemia risk score.

        Returns the calibrated risk in [0, 1], or the raw risk if
        no calibrator is available.
        """
        if self._calibrator is None:
            return raw_risk

        try:
            calibrate = getattr(self._calibrator, "calibrate", None)
            if calibrate is not None:
                result = calibrate(raw_risk, source_hint=source_hint)
                return clamp(float(result), 0.0, 1.0)
        except Exception as exc:
            log.warning("Risk calibration failed, using raw risk: %s", exc)

        return raw_risk

    def threshold_for_source(
        self,
        source_hint: SourceHint,
        *,
        fallback: float = 0.5,
    ) -> float:
        """Get the decision threshold for a given source hint."""
        if self._calibrator is None:
            return fallback

        try:
            method = getattr(self._calibrator, "threshold_for_source", None)
            if method is not None:
                return float(method(source_hint, fallback=fallback))
        except Exception as exc:
            log.warning("Threshold lookup failed: %s", exc)

        return fallback

    @property
    def method(self) -> str:
        """Name of the calibration method, if available."""
        if self._calibrator is None:
            return "none"
        return str(getattr(self._calibrator, "method", "unknown"))


class HemoglobinCalibrator:
    """
    Wraps the runtime hemoglobin calibrator for hemoglobin adjustment.
    """

    def __init__(self, calibrator: object | None = None) -> None:
        self._calibrator = calibrator

    def calibrate(
        self,
        raw_hemoglobin: float,
        *,
        quality: QualityAssessment | None = None,
        patient_profile: object | None = None,
    ) -> float | None:
        """
        Calibrate a raw hemoglobin estimate.

        Returns the calibrated hemoglobin value, or None if calibration
        is not available or should be suppressed.
        """
        if self._calibrator is None:
            return raw_hemoglobin

        try:
            calibrate = getattr(self._calibrator, "calibrate", None)
            if calibrate is not None:
                result = calibrate(raw_hemoglobin)
                if result is not None:
                    return float(result)
        except Exception as exc:
            log.warning("Hemoglobin calibration failed: %s", exc)

        return raw_hemoglobin


class ScreeningRefiner:
    """
    Wraps runtime screening refiners for post-inference risk adjustment.
    """

    def __init__(self, refiner: object | None = None) -> None:
        self._refiner = refiner

    def refine(
        self,
        *,
        base_anemia_risk: float,
        uncertainty: float,
        predicted_hemoglobin: float | None,
        quality: QualityAssessment,
        base_likely: bool,
    ) -> float:
        """
        Refine the base anemia risk score using the refiner.

        Returns the refined risk, or the base risk if no refiner is available.
        """
        if self._refiner is None:
            return base_anemia_risk

        try:
            refine = getattr(self._refiner, "refine", None)
            if refine is not None:
                result = refine(
                    base_anemia_risk=base_anemia_risk,
                    uncertainty=uncertainty,
                    predicted_hemoglobin=predicted_hemoglobin,
                    quality=quality,
                    base_likely=base_likely,
                )
                return clamp(float(result), 0.0, 1.0)
        except Exception as exc:
            log.warning("Screening refinement failed, using base risk: %s", exc)

        return base_anemia_risk

    @property
    def method(self) -> str:
        """Name of the refinement method, if available."""
        if self._refiner is None:
            return "none"
        return str(getattr(self._refiner, "method", "unknown"))


class UltimateRefiner:
    """
    Wraps the ultimate runtime refiner (v7 ultimate clinical) for
    feature remapping and risk correction.
    """

    def __init__(self, refiner: object | None = None) -> None:
        self._refiner = refiner

    def refine(
        self,
        *,
        base_prediction: dict[str, float],
        quality: QualityAssessment,
        base_feature_map: dict[str, float],
    ) -> float:
        """
        Apply ultimate refinement to a base prediction.

        Returns the corrected anemia risk score.
        """
        if self._refiner is None:
            return float(base_prediction.get("anemia_risk", 0.5))

        try:
            refine = getattr(self._refiner, "refine", None)
            if refine is not None:
                result = refine(
                    base_prediction=base_prediction,
                    quality=quality,
                    base_feature_map=base_feature_map,
                )
                return clamp(float(result), 0.0, 1.0)
        except Exception as exc:
            log.warning("Ultimate refinement failed: %s", exc)

        return float(base_prediction.get("anemia_risk", 0.5))

    def remap_features(
        self,
        feature_map: dict[str, float],
        *,
        archive_feature_names: list[str],
        expected_means: dict[str, float],
        expected_stds: dict[str, float],
    ) -> dict[str, float]:
        """Remap features to align with the archive model's expected distribution."""
        if self._refiner is None:
            return feature_map

        try:
            remap = getattr(self._refiner, "remap_ultimate_features", None)
            if remap is not None:
                return remap(
                    feature_map,
                    archive_feature_names=archive_feature_names,
                    expected_means=expected_means,
                    expected_stds=expected_stds,
                )
        except Exception as exc:
            log.warning("Feature remapping failed, using original features: %s", exc)

        return feature_map

    @property
    def threshold(self) -> float:
        """Decision threshold for the ultimate refiner."""
        if self._refiner is None:
            return 0.5
        return float(getattr(self._refiner, "threshold", 0.5))

    @property
    def method(self) -> str:
        """Name of the refinement method, if available."""
        if self._refiner is None:
            return "none"
        return str(getattr(self._refiner, "method", "unknown"))
