"""
Model artifact loading — infrastructure for loading ML model checkpoints.

This module centralizes all model file I/O so that the prediction service
can compose models without knowing about file paths, formats, or load
mechanisms.

Usage:
    loader = ModelLoader(settings)
    archive = loader.load_archive_model(path)
    bundle = loader.load_efficientnet_bundle(path)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.domain.exceptions import ModelLoadError

log = logging.getLogger("anemialens.infrastructure.ml.models")


@dataclass(frozen=True)
class ModelPaths:
    """
    Canonical paths for all ML model artifacts.

    These paths are resolved from settings/config and passed to
    the ModelLoader so that model loading is decoupled from
    configuration details.
    """
    archive_model: Path
    efficientnet_model: Path
    runtime_risk_calibrator: Path
    runtime_hb_calibrator: Path
    runtime_screening_refiner: Path
    ultimate_runtime_refiner: Path


@dataclass
class ModelLoader:
    """
    Loads ML model artifacts from disk with lazy caching.

    Each load method returns the loaded artifact (or None) and caches
    the result so that subsequent calls do not re-hit the filesystem.
    Failed loads are also cached to prevent repeated failed I/O.
    """

    paths: ModelPaths
    enable_efficientnet: bool = True

    # Loaded artifacts (cached)
    _archive_model: dict[str, object] | None = field(default=None, repr=False)
    _efficientnet_bundle: dict[str, object] | None = field(default=None, repr=False)
    _runtime_risk_calibrator: object | None = field(default=None, repr=False)
    _runtime_hb_calibrator: object | None = field(default=None, repr=False)
    _runtime_screening_refiner: object | None = field(default=None, repr=False)
    _ultimate_runtime_refiner: object | None = field(default=None, repr=False)

    # Load attempt flags (prevent re-attempting failed loads)
    _archive_attempted: bool = False
    _efficientnet_attempted: bool = False
    _risk_calibrator_attempted: bool = False
    _hb_calibrator_attempted: bool = False
    _screening_refiner_attempted: bool = False
    _ultimate_refiner_attempted: bool = False

    # ------------------------------------------------------------------
    # Public load methods
    # ------------------------------------------------------------------

    def load_archive_model(self) -> dict[str, object] | None:
        """Load the archive screening model (joblib/sklearn pipeline)."""
        if self._archive_model is not None:
            return self._archive_model
        if self._archive_attempted:
            return None

        self._archive_attempted = True
        path = self.paths.archive_model
        if not path.exists():
            log.debug("Archive model not found at %s", path)
            return None

        try:
            from app.ml.archive_model import load_archive_model as _load
            self._archive_model = _load(path)
            log.info("Loaded archive model from %s", path)
            return self._archive_model
        except Exception as exc:
            log.warning("Failed to load archive model: %s", exc)
            raise ModelLoadError(
                f"Archive model load failed: {type(exc).__name__}: {exc}",
                details={"path": str(path)},
            ) from exc

    def load_efficientnet_bundle(self) -> dict[str, object] | None:
        """Load the EfficientNet-B0 fine-tuned model checkpoint."""
        if not self.enable_efficientnet:
            return None
        if self._efficientnet_bundle is not None:
            return self._efficientnet_bundle
        if self._efficientnet_attempted:
            return None

        self._efficientnet_attempted = True
        path = self.paths.efficientnet_model
        if not path.exists():
            log.debug("EfficientNet bundle not found at %s", path)
            return None

        try:
            from app.ml.efficientnet_model import load_efficientnet_checkpoint as _load
            self._efficientnet_bundle = _load(path)
            log.info("Loaded EfficientNet bundle from %s", path)
            return self._efficientnet_bundle
        except Exception as exc:
            log.warning("Failed to load EfficientNet bundle: %s", exc)
            raise ModelLoadError(
                f"EfficientNet bundle load failed: {type(exc).__name__}: {exc}",
                details={"path": str(path)},
            ) from exc

    def load_runtime_risk_calibrator(self) -> object | None:
        """Load the runtime risk calibrator (probability calibration)."""
        if self._runtime_risk_calibrator is not None:
            return self._runtime_risk_calibrator
        if self._risk_calibrator_attempted:
            return None

        self._risk_calibrator_attempted = True
        path = self.paths.runtime_risk_calibrator
        if not path.exists():
            log.debug("Runtime risk calibrator not found at %s", path)
            return None

        try:
            from app.ml.runtime_calibration import RuntimeRiskCalibrator
            calibrator = RuntimeRiskCalibrator.load(path)
            self._runtime_risk_calibrator = calibrator
            log.info("Loaded runtime risk calibrator from %s", path)
            return calibrator
        except Exception as exc:
            log.warning("Failed to load runtime risk calibrator: %s", exc)
            return None

    def load_runtime_hb_calibrator(self) -> object | None:
        """Load the runtime hemoglobin calibrator."""
        if self._runtime_hb_calibrator is not None:
            return self._runtime_hb_calibrator
        if self._hb_calibrator_attempted:
            return None

        self._hb_calibrator_attempted = True
        path = self.paths.runtime_hb_calibrator
        if not path.exists():
            log.debug("Runtime HB calibrator not found at %s", path)
            return None

        try:
            from app.ml.runtime_hemoglobin import RuntimeHemoglobinCalibrator
            calibrator = RuntimeHemoglobinCalibrator.load(path)
            self._runtime_hb_calibrator = calibrator
            log.info("Loaded runtime HB calibrator from %s", path)
            return calibrator
        except Exception as exc:
            log.warning("Failed to load runtime HB calibrator: %s", exc)
            return None

    def load_runtime_screening_refiner(self) -> object | None:
        """Load the runtime screening refiner."""
        if self._runtime_screening_refiner is not None:
            return self._runtime_screening_refiner
        if self._screening_refiner_attempted:
            return None

        self._screening_refiner_attempted = True
        path = self.paths.runtime_screening_refiner
        if not path.exists():
            log.debug("Runtime screening refiner not found at %s", path)
            return None

        try:
            from app.ml.runtime_refinement import RuntimeScreeningRefiner
            refiner = RuntimeScreeningRefiner.load(path)
            self._runtime_screening_refiner = refiner
            log.info("Loaded runtime screening refiner from %s", path)
            return refiner
        except Exception as exc:
            log.warning("Failed to load runtime screening refiner: %s", exc)
            return None

    def load_ultimate_runtime_refiner(self) -> object | None:
        """Load the ultimate runtime refiner (v7 ultimate clinical)."""
        if self._ultimate_runtime_refiner is not None:
            return self._ultimate_runtime_refiner
        if self._ultimate_refiner_attempted:
            return None

        self._ultimate_refiner_attempted = True
        path = self.paths.ultimate_runtime_refiner
        if not path.exists():
            log.debug("Ultimate runtime refiner not found at %s", path)
            return None

        try:
            from app.ml.ultimate_runtime_refinement import UltimateRuntimeRefiner
            refiner = UltimateRuntimeRefiner.load(path)
            self._ultimate_runtime_refiner = refiner
            log.info("Loaded ultimate runtime refiner from %s", path)
            return refiner
        except Exception as exc:
            log.warning("Failed to load ultimate runtime refiner: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Status queries
    # ------------------------------------------------------------------

    @property
    def archive_model(self) -> dict[str, object] | None:
        return self._archive_model

    @property
    def efficientnet_bundle(self) -> dict[str, object] | None:
        return self._efficientnet_bundle

    @property
    def runtime_risk_calibrator(self) -> object | None:
        return self._runtime_risk_calibrator

    @property
    def runtime_hb_calibrator(self) -> object | None:
        return self._runtime_hb_calibrator

    @property
    def runtime_screening_refiner(self) -> object | None:
        return self._runtime_screening_refiner

    @property
    def ultimate_runtime_refiner(self) -> object | None:
        return self._ultimate_runtime_refiner

    def is_ready(self) -> bool:
        """True if at least one model pipeline is available."""
        return (
            self._archive_model is not None
            or self._efficientnet_bundle is not None
        )

    def get_load_error(self) -> str | None:
        """Returns the last load error message, if any."""
        # Check which load attempt failed last
        if self._archive_attempted and self._archive_model is None:
            return f"Archive model not found at {self.paths.archive_model}"
        if self._efficientnet_attempted and self._efficientnet_bundle is None:
            if self.enable_efficientnet:
                return f"EfficientNet bundle not found at {self.paths.efficientnet_model}"
        return None
