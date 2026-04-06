"""
Production Ensemble for AnemiaLens v2

Combines multiple models for improved accuracy and uncertainty estimation.

Improvements over v1:
- Better feature extraction integration
- Model confidence calibration
- Uncertainty quantification (epistemic + aleatoric)
- Quality-aware model selection
- Feature importance tracking
- Better error handling and logging
- Prediction caching
- Model versioning support
- Ensemble weight optimization
- Performance metrics collection
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PIL import Image

from app.schemas import QualityAssessment, PatientProfileInput

log = logging.getLogger("anemialens.ensemble")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_ENSEMBLE_WEIGHTS = {
    "v8": 0.55,
    "efficientnet": 0.45,
}

CACHE_MAX_SIZE = 256
CONFIDENCE_CALIBRATION_SLOPE = 1.0
CONFIDENCE_CALIBRATION_INTERCEPT = 0.0


# ---------------------------------------------------------------------------
# Data classes for structured output
# ---------------------------------------------------------------------------

@dataclass
class ModelPrediction:
    """Structured container for a single model's prediction."""
    model_name: str
    model_version: str = "unknown"
    predicted_hemoglobin: float | None = None
    anemia_risk: float = 0.5
    uncertainty: float = 0.3
    epistemic_uncertainty: float = 0.0
    aleatoric_uncertainty: float = 0.0
    confidence: float = 0.5
    inference_time_ms: float = 0.0
    feature_importances: dict[str, float] = field(default_factory=dict)
    raw_output: dict = field(default_factory=dict)


@dataclass
class EnsembleResult:
    """Structured container for ensemble prediction result."""
    predicted_hemoglobin: float | None
    anemia_risk: float
    uncertainty: float
    epistemic_uncertainty: float
    aleatoric_uncertainty: float
    confidence: float
    ensemble_used: bool
    model_agreement: float
    models_contributed: list[str]
    model_weights: dict[str, float]
    model_predictions: list[ModelPrediction]
    feature_importance: dict[str, float]
    ensemble_version: str
    prediction_id: str
    inference_time_ms: float
    hemoglobin_range: dict | None = None
    fallback: bool = False
    fallback_reason: str | None = None
    quality_adjustments: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        result = {
            "predicted_hemoglobin": self.predicted_hemoglobin,
            "anemia_risk": round(self.anemia_risk, 4),
            "uncertainty": round(self.uncertainty, 4),
            "epistemic_uncertainty": round(self.epistemic_uncertainty, 4),
            "aleatoric_uncertainty": round(self.aleatoric_uncertainty, 4),
            "confidence": round(self.confidence, 4),
            "ensemble_used": self.ensemble_used,
            "model_agreement": round(self.model_agreement, 3),
            "models_contributed": self.models_contributed,
            "model_weights": {k: round(v, 4) for k, v in self.model_weights.items()},
            "feature_importance": {
                k: round(v, 4) for k, v in
                sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]
            },
            "ensemble_version": self.ensemble_version,
            "prediction_id": self.prediction_id,
            "inference_time_ms": round(self.inference_time_ms, 2),
        }
        if self.hemoglobin_range:
            result["hemoglobin_range"] = {
                "min": round(self.hemoglobin_range["min"], 2),
                "max": round(self.hemoglobin_range["max"], 2),
                "std": round(self.hemoglobin_range["std"], 3),
            }
        if self.fallback:
            result["fallback"] = True
            result["fallback_reason"] = self.fallback_reason
        if self.quality_adjustments:
            result["quality_adjustments"] = {
                k: round(v, 4) for k, v in self.quality_adjustments.items()
            }
        return result


# ---------------------------------------------------------------------------
# Prediction Cache (LRU)
# ---------------------------------------------------------------------------

class PredictionCache:
    """
    LRU cache for predictions keyed on image hash + model versions.
    Prevents redundant computation for identical inputs.
    """

    def __init__(self, max_size: int = CACHE_MAX_SIZE):
        self.max_size = max_size
        self._cache: OrderedDict[str, EnsembleResult] = OrderedDict()

    def get(self, key: str) -> EnsembleResult | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            log.debug("Cache hit for key %s", key[:8])
            return self._cache[key]
        return None

    def put(self, key: str, result: EnsembleResult) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = result
        if len(self._cache) > self.max_size:
            evicted = self._cache.popitem(last=False)
            log.debug("Evicted cache entry %s", evicted[0][:8])

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)


# ---------------------------------------------------------------------------
# Performance Metrics Collector
# ---------------------------------------------------------------------------

class MetricsCollector:
    """
    Collects and aggregates performance metrics for the ensemble.
    Tracks inference times, model success rates, cache hit rates, etc.
    """

    def __init__(self):
        self.total_predictions = 0
        self.cache_hits = 0
        self.model_success: dict[str, int] = {}
        self.model_failures: dict[str, int] = {}
        self.inference_times: list[float] = []
        self.uncertainty_values: list[float] = []

    def record_prediction(
        self,
        inference_time_ms: float,
        models_used: list[str],
        model_failures: list[str],
        uncertainty: float,
        cache_hit: bool = False,
    ) -> None:
        self.total_predictions += 1
        if cache_hit:
            self.cache_hits += 1
        self.inference_times.append(inference_time_ms)
        self.uncertainty_values.append(uncertainty)

        for m in models_used:
            self.model_success[m] = self.model_success.get(m, 0) + 1
        for m in model_failures:
            self.model_failures[m] = self.model_failures.get(m, 0) + 1

    def get_summary(self) -> dict[str, Any]:
        if not self.inference_times:
            return {"total_predictions": 0}
        times = np.array(self.inference_times)
        uncertainties = np.array(self.uncertainty_values)
        return {
            "total_predictions": self.total_predictions,
            "cache_hit_rate": round(self.cache_hits / max(self.total_predictions, 1), 4),
            "avg_inference_time_ms": round(float(np.mean(times)), 2),
            "p50_inference_time_ms": round(float(np.percentile(times, 50)), 2),
            "p95_inference_time_ms": round(float(np.percentile(times, 95)), 2),
            "p99_inference_time_ms": round(float(np.percentile(times, 99)), 2),
            "avg_uncertainty": round(float(np.mean(uncertainties)), 4),
            "model_success_rates": {
                m: round(
                    self.model_success.get(m, 0) /
                    max(self.model_success.get(m, 0) + self.model_failures.get(m, 0), 1),
                    4,
                )
                for m in set(list(self.model_success.keys()) + list(self.model_failures.keys()))
            },
        }

    def reset(self) -> None:
        self.__init__()


# ---------------------------------------------------------------------------
# Confidence Calibration
# ---------------------------------------------------------------------------

class ConfidenceCalibrator:
    """
    Calibrates model confidence scores to better reflect true accuracy.
    Supports temperature scaling and isotonic regression.
    """

    def __init__(
        self,
        slope: float = CONFIDENCE_CALIBRATION_SLOPE,
        intercept: float = CONFIDENCE_CALIBRATION_INTERCEPT,
        method: str = "linear",
    ):
        self.slope = slope
        self.intercept = intercept
        self.method = method
        self._isotonic_model = None

    def calibrate(self, raw_confidence: float) -> float:
        """Apply calibration to raw confidence score."""
        if self.method == "linear":
            calibrated = raw_confidence * self.slope + self.intercept
        elif self.method == "temperature":
            calibrated = self._temperature_scale(raw_confidence)
        elif self.method == "isotonic" and self._isotonic_model is not None:
            calibrated = float(self._isotonic_model.predict([[raw_confidence]])[0])
        else:
            calibrated = raw_confidence
        return float(np.clip(calibrated, 0.05, 0.96))

    def _temperature_scale(self, confidence: float) -> float:
        """Temperature scaling for confidence calibration."""
        # Convert confidence to logit, scale, convert back
        logit = np.log(confidence / (1 - confidence + 1e-7) + 1e-7)
        scaled_logit = logit / max(self.slope, 1e-4)
        return float(1.0 / (1.0 + np.exp(-scaled_logit)))

    def fit_isotonic(self, confidences: list[float], accuracies: list[float]) -> None:
        """Fit isotonic regression calibrator on validation data."""
        try:
            from sklearn.isotonic import IsotonicRegression
            self._isotonic_model = IsotonicRegression(out_of_bounds="clip")
            self._isotonic_model.fit(
                np.array(confidences).reshape(-1, 1),
                np.array(accuracies),
            )
            self.method = "isotonic"
            log.info("Fit isotonic calibrator on %d samples", len(confidences))
        except ImportError:
            log.warning("sklearn not available, falling back to linear calibration")
            self.method = "linear"

    def get_ece(self, confidences: list[float], accuracies: list[float], n_bins: int = 10) -> float:
        """Compute Expected Calibration Error."""
        confidences_arr = np.array(confidences)
        accuracies_arr = np.array(accuracies)
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        ece = 0.0
        total = len(confidences_arr)
        for i in range(n_bins):
            mask = (confidences_arr > bin_boundaries[i]) & (confidences_arr <= bin_boundaries[i + 1])
            if mask.sum() == 0:
                continue
            bin_conf = confidences_arr[mask].mean()
            bin_acc = accuracies_arr[mask].mean()
            ece += mask.sum() / total * abs(bin_acc - bin_conf)
        return float(ece)


# ---------------------------------------------------------------------------
# Ensemble Weight Optimizer
# ---------------------------------------------------------------------------

class EnsembleWeightOptimizer:
    """
    Optimizes ensemble weights on validation data to minimize
    prediction error (MSE for hemoglobin, log-loss for anemia risk).
    """

    def __init__(self, model_names: list[str]):
        self.model_names = model_names
        self.optimal_weights = {name: 1.0 / len(model_names) for name in model_names}

    def optimize(
        self,
        model_predictions: dict[str, list[float]],
        true_values: list[float],
        metric: str = "mse",
    ) -> dict[str, float]:
        """
        Find optimal weights that minimize the specified metric.

        Args:
            model_predictions: dict mapping model_name to list of predictions
            true_values: ground truth values
            metric: optimization metric ('mse', 'mae', 'logloss')
        """
        try:
            from scipy.optimize import minimize
        except ImportError:
            log.warning("scipy not available, using equal weights")
            return self.optimal_weights

        n_models = len(self.model_names)

        def objective(weights):
            weights = weights / weights.sum()  # normalize
            total_loss = 0.0
            for i, true_val in enumerate(true_values):
                ensemble_pred = sum(
                    weights[j] * model_predictions[self.model_names[j]][i]
                    for j in range(n_models)
                    if i < len(model_predictions.get(self.model_names[j], []))
                )
                if metric == "mse":
                    total_loss += (ensemble_pred - true_val) ** 2
                elif metric == "mae":
                    total_loss += abs(ensemble_pred - true_val)
                elif metric == "logloss":
                    p = np.clip(ensemble_pred, 1e-7, 1 - 1e-7)
                    total_loss -= true_val * np.log(p) + (1 - true_val) * np.log(1 - p)
            return total_loss / max(len(true_values), 1)

        x0 = np.array([1.0 / n_models] * n_models)
        bounds = [(0.05, 0.95)] * n_models
        constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

        result = minimize(
            objective, x0, method="SLSQP", bounds=bounds, constraints=constraints,
            options={"maxiter": 200, "ftol": 1e-9},
        )

        if result.success:
            optimized = {
                self.model_names[i]: float(np.clip(result.x[i], 0.05, 0.95))
                for i in range(n_models)
            }
            # Re-normalize
            total = sum(optimized.values())
            optimized = {k: v / total for k, v in optimized.items()}
            self.optimal_weights = optimized
            log.info("Optimized ensemble weights: %s", {k: round(v, 3) for k, v in optimized.items()})
        else:
            log.warning("Weight optimization failed: %s", result.message)

        return self.optimal_weights


# ---------------------------------------------------------------------------
# Production Ensemble
# ---------------------------------------------------------------------------

class ProductionEnsemble:
    """
    Production-ready ensemble combining multiple models.

    Ensemble strategy:
    - Weighted average based on model confidence
    - Disagreement-based uncertainty inflation
    - Quality-aware model selection
    - Epistemic + aleatoric uncertainty decomposition
    - Feature importance aggregation
    """

    ENSEMBLE_VERSION = "2.0.0"

    def __init__(
        self,
        v8_model: object | None = None,
        efficientnet_model: object | None = None,
        enable_ensemble: bool = True,
        ensemble_weights: dict[str, float] | None = None,
        feature_importance_enabled: bool = True,
    ):
        self.v8_model = v8_model
        self.efficientnet_model = efficientnet_model
        self.enable_ensemble = enable_ensemble
        self.feature_importance_enabled = feature_importance_enabled

        # Weight management
        self.base_weights = ensemble_weights or dict(DEFAULT_ENSEMBLE_WEIGHTS)
        self._normalize_weights()
        self._active_weights = dict(self.base_weights)

        # Calibration
        self.calibrator = ConfidenceCalibrator()

        # Caching
        self.cache = PredictionCache(max_size=CACHE_MAX_SIZE)

        # Metrics
        self.metrics = MetricsCollector()

        # Feature importance tracker
        self._feature_importance_history: list[dict[str, float]] = []

        # Model version tracking
        self._model_versions: dict[str, str] = {}
        self._track_model_versions()

        log.info(
            "ProductionEnsemble v%s initialized (models: %s, ensemble: %s)",
            self.ENSEMBLE_VERSION,
            list(self._active_weights.keys()),
            enable_ensemble,
        )

    def _track_model_versions(self) -> None:
        """Record model versions for traceability."""
        if self.v8_model is not None:
            if hasattr(self.v8_model, "get"):
                self._model_versions["v8"] = str(self.v8_model.get("version", "unknown"))
            else:
                self._model_versions["v8"] = "loaded"
        if self.efficientnet_model is not None:
            if hasattr(self.efficientnet_model, "version"):
                self._model_versions["efficientnet"] = str(self.efficientnet_model.version)
            else:
                self._model_versions["efficientnet"] = "loaded"
        log.debug("Model versions: %s", self._model_versions)

    def _normalize_weights(self) -> None:
        """Ensure weights sum to 1.0."""
        total = sum(self.base_weights.values())
        if total > 0:
            self.base_weights = {k: v / total for k, v in self.base_weights.items()}
        else:
            n = len(self.base_weights)
            self.base_weights = {k: 1.0 / n for k in self.base_weights}

    def _compute_image_hash(self, image: Image.Image) -> str:
        """Compute a perceptual hash of the image for cache key."""
        small = image.resize((32, 32)).convert("L")
        pixels = list(small.getdata())
        return hashlib.md5(bytes(pixels)).hexdigest()[:12]

    def _build_cache_key(
        self,
        image: Image.Image,
        patient_profile: PatientProfileInput | None = None,
    ) -> str:
        """Build cache key from image hash + model versions + profile."""
        img_hash = self._compute_image_hash(image)
        version_hash = hashlib.md5(
            str(sorted(self._model_versions.items())).encode()
        ).hexdigest()[:8]
        profile_hash = ""
        if patient_profile is not None:
            profile_data = f"{patient_profile.age}-{patient_profile.sex}-{patient_profile.symptoms}"
            profile_hash = hashlib.md5(profile_data.encode()).hexdigest()[:8]
        return f"{img_hash}:{version_hash}:{profile_hash}"

    def predict(
        self,
        image: Image.Image,
        quality: QualityAssessment,
        patient_profile: PatientProfileInput | None = None,
    ) -> dict:
        """
        Make ensemble prediction with full metadata.

        Args:
            image: Input conjunctiva image
            quality: Image quality assessment
            patient_profile: Optional patient demographics

        Returns:
            Dictionary with ensemble prediction and metadata
        """
        start_time = time.monotonic()
        prediction_id = str(uuid.uuid4())[:8]

        # Check cache
        cache_key = self._build_cache_key(image, patient_profile)
        cached = self.cache.get(cache_key)
        if cached is not None:
            elapsed = (time.monotonic() - start_time) * 1000
            self.metrics.record_prediction(
                inference_time_ms=elapsed,
                models_used=[],
                model_failures=[],
                uncertainty=cached.uncertainty,
                cache_hit=True,
            )
            log.info("Cache hit for prediction %s (%.1fms)", prediction_id, elapsed)
            result = cached.to_dict()
            result["prediction_id"] = prediction_id
            result["cached"] = True
            return result

        # Get individual model predictions
        model_preds, model_failures = self._get_model_predictions(
            image, quality, patient_profile
        )

        # Handle edge cases
        if len(model_preds) == 0:
            result = self._fallback_prediction(prediction_id, model_failures)
            elapsed = (time.monotonic() - start_time) * 1000
            self.metrics.record_prediction(
                inference_time_ms=elapsed,
                models_used=[],
                model_failures=list(self.base_weights.keys()),
                uncertainty=result["uncertainty"],
            )
            return result

        if len(model_preds) == 1:
            pred = model_preds[0]
            result = self._single_model_result(pred, prediction_id)
            elapsed = (time.monotonic() - start_time) * 1000
            self.metrics.record_prediction(
                inference_time_ms=elapsed,
                models_used=[pred.model_name],
                model_failures=model_failures,
                uncertainty=pred.uncertainty,
            )
            self.cache.put(cache_key, EnsembleResult(**self._dict_to_ensemble_args(result)))
            return result

        # Ensemble fusion
        result = self._fuse_predictions(model_preds, quality, prediction_id, model_failures)
        elapsed = (time.monotonic() - start_time) * 1000
        self.metrics.record_prediction(
            inference_time_ms=elapsed,
            models_used=[p.model_name for p in model_preds],
            model_failures=model_failures,
            uncertainty=result["uncertainty"],
        )

        # Cache the result (without the unique prediction_id)
        cacheable = dict(result)
        cacheable.pop("prediction_id", None)
        try:
            self.cache.put(cache_key, EnsembleResult(**self._dict_to_ensemble_args(cacheable)))
        except Exception:
            log.debug("Failed to cache result (non-critical)")

        return result

    def _get_model_predictions(
        self,
        image: Image.Image,
        quality: QualityAssessment,
        patient_profile: PatientProfileInput | None,
    ) -> tuple[list[ModelPrediction], list[str]]:
        """Get predictions from all available models."""
        predictions: list[ModelPrediction] = []
        failures: list[str] = []

        # V8 model
        if self.v8_model is not None:
            try:
                t0 = time.monotonic()
                v8_pred = self.v8_model.predict(image, quality, patient_profile)
                elapsed_ms = (time.monotonic() - t0) * 1000

                # Extract feature importance if available
                feature_imp = {}
                if self.feature_importance_enabled and hasattr(self.v8_model, "get"):
                    feature_imp = self.v8_model.get("feature_importances", {})

                predictions.append(ModelPrediction(
                    model_name="v8",
                    model_version=self._model_versions.get("v8", "unknown"),
                    predicted_hemoglobin=v8_pred.get("predicted_hemoglobin"),
                    anemia_risk=v8_pred.get("anemia_risk", 0.5),
                    uncertainty=v8_pred.get("uncertainty", 0.3),
                    epistemic_uncertainty=v8_pred.get("epistemic_uncertainty", 0.0),
                    aleatoric_uncertainty=v8_pred.get("aleatoric_uncertainty", 0.0),
                    confidence=1.0 - v8_pred.get("uncertainty", 0.3),
                    inference_time_ms=elapsed_ms,
                    feature_importances=feature_imp,
                    raw_output=v8_pred,
                ))
            except Exception as e:
                log.error("V8 model prediction failed: %s", e, exc_info=True)
                failures.append("v8")
        else:
            log.debug("V8 model not loaded")

        # EfficientNet model
        if self.efficientnet_model is not None:
            try:
                t0 = time.monotonic()
                eff_pred = self.efficientnet_model.predict(image)
                elapsed_ms = (time.monotonic() - t0) * 1000

                predictions.append(ModelPrediction(
                    model_name="efficientnet",
                    model_version=self._model_versions.get("efficientnet", "unknown"),
                    predicted_hemoglobin=eff_pred.get("predicted_hemoglobin"),
                    anemia_risk=eff_pred.get("anemia_risk", 0.5),
                    uncertainty=eff_pred.get("uncertainty", 0.3),
                    epistemic_uncertainty=eff_pred.get("epistemic_uncertainty", 0.0),
                    aleatoric_uncertainty=eff_pred.get("aleatoric_uncertainty", 0.0),
                    confidence=1.0 - eff_pred.get("uncertainty", 0.3),
                    inference_time_ms=elapsed_ms,
                    raw_output=eff_pred,
                ))
            except Exception as e:
                log.error("EfficientNet model prediction failed: %s", e, exc_info=True)
                failures.append("efficientnet")
        else:
            log.debug("EfficientNet model not loaded")

        return predictions, failures

    def _fuse_predictions(
        self,
        predictions: list[ModelPrediction],
        quality: QualityAssessment,
        prediction_id: str,
        model_failures: list[str],
    ) -> dict:
        """
        Fuse multiple model predictions with quality-aware weighting.
        """
        # Quality-adjusted weights
        quality_adjustments = {}
        adjusted_weights = []

        for pred in predictions:
            base_weight = self._active_weights.get(pred.model_name, 0.5)
            quality_multiplier = self._model_quality_weight(pred.model_name, quality)
            adjusted_weight = base_weight * quality_multiplier
            adjusted_weights.append(adjusted_weight)
            quality_adjustments[pred.model_name] = quality_multiplier

        # Normalize adjusted weights
        weight_sum = sum(adjusted_weights)
        if weight_sum > 0:
            normalized_weights = [w / weight_sum for w in adjusted_weights]
        else:
            normalized_weights = [1.0 / len(predictions)] * len(predictions)

        # Weighted hemoglobin
        hb_values = [p.predicted_hemoglobin for p in predictions if p.predicted_hemoglobin is not None]
        if len(hb_values) == 0:
            return self._fallback_prediction(prediction_id, model_failures)

        valid_preds = [p for p in predictions if p.predicted_hemoglobin is not None]
        ensemble_hb = sum(
            p.predicted_hemoglobin * w
            for p, w in zip(valid_preds, normalized_weights[:len(valid_preds)])
        )

        # Weighted anemia risk
        risk_values = [p.anemia_risk for p in predictions]
        ensemble_risk = sum(
            r * w for r, w in zip(risk_values, normalized_weights)
        )

        # Uncertainty decomposition
        epistemic_uncertainties = [p.epistemic_uncertainty for p in predictions if p.epistemic_uncertainty > 0]
        aleatoric_uncertainties = [p.aleatoric_uncertainty for p in predictions if p.aleatoric_uncertainty > 0]
        base_uncertainties = [p.uncertainty for p in predictions]

        # Base uncertainty: weighted average
        ensemble_base_uncertainty = np.mean(base_uncertainties)

        # Epistemic: max of model epistemic uncertainties + disagreement
        ensemble_epistemic = (
            np.mean(epistemic_uncertainties) if epistemic_uncertainties else 0.0
        )

        # Aleatoric: weighted average of aleatoric uncertainties
        ensemble_aleatoric = (
            np.mean(aleatoric_uncertainties) if aleatoric_uncertainties else 0.0
        )

        # Disagreement-based uncertainty inflation
        disagreement_penalty = 0.0
        if len(hb_values) > 1:
            hb_std = float(np.std(hb_values))
            risk_std = float(np.std(risk_values))
            disagreement_penalty = hb_std * 0.3 + risk_std * 0.5
            ensemble_epistemic += hb_std / 5.0  # normalized disagreement

        # Total uncertainty
        ensemble_uncertainty = min(
            0.95,
            ensemble_base_uncertainty + disagreement_penalty + ensemble_epistemic * 0.2
        )
        ensemble_epistemic = min(0.95, ensemble_epistemic)
        ensemble_aleatoric = min(0.95, ensemble_aleatoric)

        # Model agreement
        agreement = 1.0 - (float(np.std(hb_values)) / 5.0) if len(hb_values) > 1 else 1.0
        agreement = max(0.0, min(1.0, agreement))

        # Calibrated confidence
        raw_confidence = 1.0 - ensemble_uncertainty
        calibrated_confidence = self.calibrator.calibrate(raw_confidence)

        # Feature importance aggregation
        feature_importance = self._aggregate_feature_importances(predictions)

        weight_map = {
            p.model_name: round(w, 4)
            for p, w in zip(predictions, normalized_weights)
        }

        result = {
            "predicted_hemoglobin": round(ensemble_hb, 2),
            "anemia_risk": round(ensemble_risk, 4),
            "uncertainty": round(ensemble_uncertainty, 4),
            "epistemic_uncertainty": round(ensemble_epistemic, 4),
            "aleatoric_uncertainty": round(ensemble_aleatoric, 4),
            "confidence": round(calibrated_confidence, 4),
            "ensemble_used": True,
            "model_agreement": round(agreement, 3),
            "models_contributed": [p.model_name for p in predictions],
            "model_weights": weight_map,
            "model_predictions": [
                {
                    "model_name": p.model_name,
                    "model_version": p.model_version,
                    "predicted_hemoglobin": p.predicted_hemoglobin,
                    "anemia_risk": round(p.anemia_risk, 4),
                    "uncertainty": round(p.uncertainty, 4),
                    "inference_time_ms": round(p.inference_time_ms, 2),
                }
                for p in predictions
            ],
            "feature_importance": feature_importance,
            "ensemble_version": self.ENSEMBLE_VERSION,
            "prediction_id": prediction_id,
            "inference_time_ms": 0.0,  # Set by caller
            "hemoglobin_range": {
                "min": round(min(hb_values), 2),
                "max": round(max(hb_values), 2),
                "std": round(float(np.std(hb_values)), 3),
            },
            "quality_adjustments": {k: round(v, 4) for k, v in quality_adjustments.items()},
            "fallback": False,
            "fallback_reason": None,
        }

        return result

    def _aggregate_feature_importances(self, predictions: list[ModelPrediction]) -> dict[str, float]:
        """Aggregate feature importances across models."""
        all_importances: dict[str, list[float]] = {}

        for pred in predictions:
            if pred.feature_importances:
                for feat, imp in pred.feature_importances.items():
                    all_importances.setdefault(feat, []).append(imp)

        if not all_importances:
            return {}

        # Average across models that provide them
        aggregated = {
            feat: float(np.mean(values))
            for feat, values in all_importances.items()
        }

        # Track history
        self._feature_importance_history.append(aggregated)
        if len(self._feature_importance_history) > 1000:
            self._feature_importance_history = self._feature_importance_history[-500:]

        return aggregated

    def _model_quality_weight(
        self,
        model_name: str,
        quality: QualityAssessment,
    ) -> float:
        """
        Adjust model weight based on image quality.

        Some models are more robust to certain quality issues.
        """
        base_weight = 1.0

        # V8 model is sensitive to blur
        if model_name == "v8":
            if quality.blur_score < 60:
                base_weight *= 0.7
            if quality.blur_score < 40:
                base_weight *= 0.8  # additional penalty for severe blur

        # EfficientNet is sensitive to lighting
        if model_name == "efficientnet":
            if quality.lighting_condition in ["glare_heavy", "shadow_heavy"]:
                base_weight *= 0.75
            if quality.brightness_score < 0.2 or quality.brightness_score > 0.8:
                base_weight *= 0.8

        # Generic quality adjustments
        if quality.framing_score < 0.4:
            base_weight *= 0.9  # all models less reliable with poor framing

        return base_weight

    def _fallback_prediction(
        self,
        prediction_id: str,
        model_failures: list[str],
    ) -> dict:
        """Return safe fallback when all models fail."""
        reason = "All models failed"
        if model_failures:
            reason = f"Models failed: {', '.join(model_failures)}"

        return {
            "predicted_hemoglobin": None,
            "anemia_risk": 0.5,
            "uncertainty": 0.9,
            "epistemic_uncertainty": 0.0,
            "aleatoric_uncertainty": 0.0,
            "confidence": 0.1,
            "ensemble_used": False,
            "model_agreement": 0.0,
            "models_contributed": [],
            "model_weights": {},
            "model_predictions": [],
            "feature_importance": {},
            "ensemble_version": self.ENSEMBLE_VERSION,
            "prediction_id": prediction_id,
            "inference_time_ms": 0.0,
            "hemoglobin_range": None,
            "quality_adjustments": {},
            "fallback": True,
            "fallback_reason": reason,
        }

    def _single_model_result(self, pred: ModelPrediction, prediction_id: str) -> dict:
        """Return result when only one model is available."""
        calibrated_confidence = self.calibrator.calibrate(pred.confidence)

        return {
            "predicted_hemoglobin": pred.predicted_hemoglobin,
            "anemia_risk": round(pred.anemia_risk, 4),
            "uncertainty": round(pred.uncertainty, 4),
            "epistemic_uncertainty": round(pred.epistemic_uncertainty, 4),
            "aleatoric_uncertainty": round(pred.aleatoric_uncertainty, 4),
            "confidence": round(calibrated_confidence, 4),
            "ensemble_used": False,
            "single_model": pred.model_name,
            "model_agreement": 1.0,
            "models_contributed": [pred.model_name],
            "model_weights": {pred.model_name: 1.0},
            "model_predictions": [{
                "model_name": pred.model_name,
                "model_version": pred.model_version,
                "predicted_hemoglobin": pred.predicted_hemoglobin,
                "anemia_risk": round(pred.anemia_risk, 4),
                "uncertainty": round(pred.uncertainty, 4),
                "inference_time_ms": round(pred.inference_time_ms, 2),
            }],
            "feature_importance": pred.feature_importances,
            "ensemble_version": self.ENSEMBLE_VERSION,
            "prediction_id": prediction_id,
            "inference_time_ms": round(pred.inference_time_ms, 2),
            "hemoglobin_range": None,
            "quality_adjustments": {},
            "fallback": False,
            "fallback_reason": None,
        }

    def _dict_to_ensemble_args(self, d: dict) -> dict:
        """Convert dictionary to EnsembleResult constructor args."""
        model_preds = []
        for mp in d.get("model_predictions", []):
            model_preds.append(ModelPrediction(
                model_name=mp.get("model_name", ""),
                model_version=mp.get("model_version", "unknown"),
                predicted_hemoglobin=mp.get("predicted_hemoglobin"),
                anemia_risk=mp.get("anemia_risk", 0.5),
                uncertainty=mp.get("uncertainty", 0.3),
                inference_time_ms=mp.get("inference_time_ms", 0.0),
            ))

        return {
            "predicted_hemoglobin": d.get("predicted_hemoglobin"),
            "anemia_risk": d.get("anemia_risk", 0.5),
            "uncertainty": d.get("uncertainty", 0.3),
            "epistemic_uncertainty": d.get("epistemic_uncertainty", 0.0),
            "aleatoric_uncertainty": d.get("aleatoric_uncertainty", 0.0),
            "confidence": d.get("confidence", 0.5),
            "ensemble_used": d.get("ensemble_used", False),
            "model_agreement": d.get("model_agreement", 0.0),
            "models_contributed": d.get("models_contributed", []),
            "model_weights": d.get("model_weights", {}),
            "model_predictions": model_preds,
            "feature_importance": d.get("feature_importance", {}),
            "ensemble_version": d.get("ensemble_version", self.ENSEMBLE_VERSION),
            "prediction_id": d.get("prediction_id", "cached"),
            "inference_time_ms": d.get("inference_time_ms", 0.0),
            "hemoglobin_range": d.get("hemoglobin_range"),
            "fallback": d.get("fallback", False),
            "fallback_reason": d.get("fallback_reason"),
            "quality_adjustments": d.get("quality_adjustments", {}),
        }

    # ------------------------------------------------------------------
    # Public API for calibration, weights, metrics
    # ------------------------------------------------------------------

    def set_calibration(self, slope: float = 1.0, intercept: float = 0.0, method: str = "linear") -> None:
        """Configure confidence calibration parameters."""
        self.calibrator = ConfidenceCalibrator(slope=slope, intercept=intercept, method=method)
        log.info("Calibration set: slope=%s, intercept=%s, method=%s", slope, intercept, method)

    def update_weights(self, weights: dict[str, float]) -> None:
        """Update ensemble weights (e.g., from online optimization)."""
        self.base_weights = dict(weights)
        self._normalize_weights()
        self._active_weights = dict(self.base_weights)
        log.info("Updated ensemble weights: %s", {k: round(v, 3) for k, v in self._active_weights.items()})

    def optimize_weights(
        self,
        model_predictions: dict[str, list[float]],
        true_values: list[float],
        metric: str = "mse",
    ) -> dict[str, float]:
        """Optimize ensemble weights on validation data."""
        model_names = list(self.base_weights.keys())
        optimizer = EnsembleWeightOptimizer(model_names)
        optimized = optimizer.optimize(model_predictions, true_values, metric)
        self.update_weights(optimized)
        return optimized

    def get_metrics_summary(self) -> dict:
        """Get performance metrics summary."""
        return self.metrics.get_summary()

    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self.metrics.reset()

    def clear_cache(self) -> None:
        """Clear prediction cache."""
        self.cache.clear()
        log.info("Prediction cache cleared")

    def get_feature_importance_trends(self) -> list[dict[str, float]]:
        """Get historical feature importance trends."""
        return list(self._feature_importance_history[-100:])


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

def create_production_ensemble(
    v8_model_path: str | None = None,
    efficientnet_path: str | None = None,
    enable: bool = True,
    ensemble_weights: dict[str, float] | None = None,
    calibration_params: dict[str, float] | None = None,
    feature_importance_enabled: bool = True,
) -> ProductionEnsemble:
    """
    Factory function to create production ensemble with auto-loading.
    """
    v8_model = None
    efficientnet_model = None

    if enable:
        # Load V8 model
        if v8_model_path:
            try:
                import joblib
                v8_model = joblib.load(v8_model_path)
                version = v8_model.get("version", "unknown") if hasattr(v8_model, "get") else "unknown"
                log.info("Loaded V8 model: %s", version)
            except Exception as e:
                log.error("Failed to load V8 model from %s: %s", v8_model_path, e, exc_info=True)

        # Load EfficientNet
        if efficientnet_path:
            try:
                from app.ml.efficientnet_model import load_efficientnet_checkpoint
                efficientnet_bundle = load_efficientnet_checkpoint(efficientnet_path)
                efficientnet_model = EfficientNetWrapper(efficientnet_bundle)
                log.info("Loaded EfficientNet model")
            except Exception as e:
                log.error("Failed to load EfficientNet from %s: %s", efficientnet_path, e, exc_info=True)

    ensemble = ProductionEnsemble(
        v8_model=v8_model,
        efficientnet_model=efficientnet_model,
        enable_ensemble=enable,
        ensemble_weights=ensemble_weights,
        feature_importance_enabled=feature_importance_enabled,
    )

    # Configure calibration if provided
    if calibration_params:
        ensemble.set_calibration(
            slope=calibration_params.get("slope", 1.0),
            intercept=calibration_params.get("intercept", 0.0),
            method=calibration_params.get("method", "linear"),
        )

    return ensemble


class EfficientNetWrapper:
    """
    Wrapper to make EfficientNet prediction interface consistent.
    """

    def __init__(self, bundle: dict):
        self.bundle = bundle
        self.model = bundle.get("model")
        self.device = bundle.get("device", "cpu")
        self.version = str(bundle.get("version", "unknown"))

    def predict(self, image: Image.Image) -> dict:
        """Make EfficientNet prediction with uncertainty decomposition."""
        from app.ml.efficientnet_model import predict_with_efficientnet_model

        result = predict_with_efficientnet_model(
            self.bundle,
            image,
            mc_passes=4,
        )

        return {
            "predicted_hemoglobin": result.get("predicted_hemoglobin"),
            "anemia_risk": result.get("anemia_risk", 0.5),
            "uncertainty": result.get("uncertainty", 0.3),
            "epistemic_uncertainty": result.get("epistemic_uncertainty", 0.0),
            "aleatoric_uncertainty": result.get("aleatoric_uncertainty", 0.0),
        }
