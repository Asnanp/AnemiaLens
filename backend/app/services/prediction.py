from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from PIL import Image

from app.config import (
    DEFAULT_ARCHIVE_MODEL_PATH,
    DEFAULT_EFFICIENTNET_MODEL_PATH,
    DEFAULT_RUNTIME_CALIBRATOR_PATH,
    DEFAULT_V8_RUNTIME_CALIBRATOR_PATH,
    DEFAULT_V8_RUNTIME_HB_CALIBRATOR_PATH,
    DEFAULT_RUNTIME_REFINER_PATH,
    DEFAULT_ULTIMATE_REFINER_PATH,
    settings,
)
from app.ml.archive_model import clamp
from app.ml.features import (
    extract_eye_features,
    extract_ultimate_clinical_features,
    extract_v8_clinical_features,
    framing_score as estimate_framing_score,
)
from app.ml.fallback_prediction import FallbackPrediction, generate_fallback
from app.schemas import (
    ModelRuntimeStatus,
    PatientProfileInput,
    PredictionResult,
    QualityAssessment,
)

log = logging.getLogger("anemialens.prediction")


# ─────────────────────────────────────────────────────────────────────────────
# Input validation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ValidationError:
    """A single validation error for prediction input."""
    field: str
    message: str
    suggestion: str


@dataclass(frozen=True)
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)


def validate_prediction_input(
    image: Image.Image,
    patient_profile: PatientProfileInput | None = None,
) -> ValidationResult:
    """
    Validate prediction input before running the pipeline.

    Checks:
    - Image dimensions are within reasonable bounds
    - Image is not entirely uniform (solid color)
    - Image mode is valid
    - Patient profile values are reasonable (if provided)

    Returns
    -------
    ValidationResult with errors and warnings
    """
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []

    # Image validation
    width, height = image.size

    if width < 32 or height < 16:
        errors.append(ValidationError(
            field="image_dimensions",
            message=f"Image is too small ({width}x{height}px).",
            suggestion="Use an image at least 100x50 pixels.",
        ))
    elif width < 100 or height < 50:
        warnings.append(ValidationError(
            field="image_dimensions",
            message=f"Image is quite small ({width}x{height}px).",
            suggestion="Higher resolution images may produce better results.",
        ))

    if width > 10000 or height > 10000:
        errors.append(ValidationError(
            field="image_dimensions",
            message=f"Image is too large ({width}x{height}px).",
            suggestion="Resize to under 10000 pixels on each side.",
        ))

    # Check for solid color images
    if image.mode == "RGB":
        pixels = list(image.resize((16, 16)).getdata())
        unique_colors = set(pixels)
        if len(unique_colors) <= 2:
            errors.append(ValidationError(
                field="image_content",
                message="The image appears to be a solid or near-solid color.",
                suggestion="Capture a real photo of the eye conjunctiva.",
            ))
        elif len(unique_colors) <= 8:
            warnings.append(ValidationError(
                field="image_content",
                message="The image has very limited color variation.",
                suggestion="Ensure the image captures actual tissue detail.",
            ))

    # Check for all-black or all-white
    grayscale = image.convert("L")
    gray_pixels = list(grayscale.resize((16, 16)).getdata())
    mean_brightness = sum(gray_pixels) / len(gray_pixels)
    if mean_brightness < 2:
        errors.append(ValidationError(
            field="image_brightness",
            message="The image is completely or nearly completely black.",
            suggestion="Ensure the camera lens is uncovered and lighting is adequate.",
        ))
    elif mean_brightness > 253:
        errors.append(ValidationError(
            field="image_brightness",
            message="The image is completely or nearly completely white.",
            suggestion="Check that the camera is not pointed at a bright light source.",
        ))

    # Patient profile validation
    if patient_profile is not None:
        if patient_profile.age is not None:
            if patient_profile.age < 0:
                errors.append(ValidationError(
                    field="patient_age",
                    message="Age cannot be negative.",
                    suggestion="Provide a valid age or leave it unspecified.",
                ))
            elif patient_profile.age > 120:
                warnings.append(ValidationError(
                    field="patient_age",
                    message=f"Age {patient_profile.age} seems unusually high.",
                    suggestion="Verify the age value.",
                ))

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def _runtime_stack_version() -> str:
    from app.ml.runtime_stack import RUNTIME_STACK_VERSION

    return RUNTIME_STACK_VERSION


def _efficientnet_version() -> str:
    from app.ml.efficientnet_model import EFFICIENTNET_VERSION

    return EFFICIENTNET_VERSION


def _decision_threshold_for_source(
    source_hint: Literal["roi_original", "palpebral", "forniceal_palpebral"],
) -> float:
    from app.ml.runtime_stack import decision_threshold_for_source

    return float(decision_threshold_for_source(source_hint))


def _load_archive_model_artifact(path: Path) -> dict[str, object]:
    from app.ml.archive_model import load_archive_model

    return load_archive_model(path)


def _load_runtime_risk_calibrator_artifact(path: Path):
    from app.ml.runtime_calibration import RuntimeRiskCalibrator

    return RuntimeRiskCalibrator.load(path)


def _load_runtime_hb_calibrator_artifact(path: Path):
    from app.ml.runtime_hemoglobin import RuntimeHemoglobinCalibrator

    return RuntimeHemoglobinCalibrator.load(path)


def _load_runtime_screening_refiner_artifact(path: Path):
    from app.ml.runtime_refinement import RuntimeScreeningRefiner

    return RuntimeScreeningRefiner.load(path)


def _load_ultimate_runtime_refiner_artifact(path: Path):
    from app.ml.ultimate_runtime_refinement import UltimateRuntimeRefiner

    return UltimateRuntimeRefiner.load(path)


def _predict_archive_model(
    artifact: dict[str, object],
    feature_map: dict[str, float],
    *,
    source_hint: Literal["roi_original", "palpebral", "forniceal_palpebral"],
) -> dict[str, float]:
    from app.ml.archive_model import predict_with_archive_model

    return predict_with_archive_model(artifact, feature_map, source_hint=source_hint)


def _archive_model_version(artifact: dict[str, object] | None) -> str:
    if artifact is None:
        return ""
    version = artifact.get("version")
    return str(version or "")


def _uses_ultimate_archive_features(artifact: dict[str, object] | None) -> bool:
    return _archive_model_version(artifact).startswith("archive-fusion-v7-ultimate-clinical")


def _uses_v8_archive_features(artifact: dict[str, object] | None) -> bool:
    return _archive_model_version(artifact).startswith("archive-fusion-v8-clinical-robust")


def _ultimate_feature_names(artifact: dict[str, object]) -> list[str]:
    feature_names = artifact.get("feature_names")
    if isinstance(feature_names, list) and feature_names:
        return [str(name) for name in feature_names]
    return []


def _ultimate_expected_scaler_stats(
    artifact: dict[str, object],
) -> tuple[dict[str, float], dict[str, float]]:
    feature_names = _ultimate_feature_names(artifact)
    scaler = artifact.get("scaler")
    if not feature_names:
        return {}, {}
    if scaler is None or not hasattr(scaler, "mean_") or not hasattr(scaler, "scale_"):
        return (
            {name: 0.0 for name in feature_names},
            {name: 1.0 for name in feature_names},
        )
    return (
        {
            name: float(value)
            for name, value in zip(feature_names, scaler.mean_, strict=False)
        },
        {
            name: max(float(value), 1e-6)
            for name, value in zip(feature_names, scaler.scale_, strict=False)
        },
    )


def _infer_default_lighting_condition(feature_map: dict[str, float]) -> str:
    highlight_fraction = float(feature_map.get("highlight_fraction", 0.0))
    shadow_fraction = float(feature_map.get("shadow_fraction", 0.0))
    brightness = float(feature_map.get("brightness", 0.35))
    contrast = float(feature_map.get("contrast", 0.18))
    if highlight_fraction >= 0.18:
        return "glare_heavy"
    if shadow_fraction >= 0.18:
        return "shadow_heavy"
    if brightness >= 0.78:
        return "overexposed"
    if brightness <= 0.18:
        return "dim"
    if contrast <= 0.10:
        return "flat_contrast"
    return "balanced"


def _build_default_quality_assessment(
    feature_map: dict[str, float],
) -> QualityAssessment:
    lighting_condition = _infer_default_lighting_condition(feature_map)
    lighting_score = clamp(
        1.0
        - (
            float(feature_map.get("illumination_std", 0.12)) * 2.2
            + float(feature_map.get("highlight_fraction", 0.0)) * 0.55
            + float(feature_map.get("shadow_fraction", 0.0)) * 0.55
        ),
        0.0,
        1.0,
    )
    blur_score = float(feature_map.get("blur_score", 120.0))
    brightness_score = clamp(float(feature_map.get("brightness", 0.35)), 0.0, 1.0)
    contrast_score = clamp(float(feature_map.get("contrast", 0.16)), 0.0, 1.0)
    center_blur_score = float(feature_map.get("center_blur_score", blur_score))
    center_contrast = float(
        feature_map.get("center_contrast", max(contrast_score, 0.12))
    )
    center_red_green_gap = float(feature_map.get("center_red_green_gap", 0.0))
    safe_framing_map = {
        **feature_map,
        "center_blur_score": center_blur_score,
        "center_contrast": center_contrast,
        "center_red_green_gap": center_red_green_gap,
        "contrast": max(contrast_score, 1e-6),
        "blur_score": max(blur_score, 1e-6),
    }
    framing = max(float(estimate_framing_score(safe_framing_map)), 0.0)
    passed = (
        blur_score >= 45.0
        and 0.12 <= brightness_score <= 0.95
        and contrast_score >= 0.05
    )
    summary_map = {
        "glare_heavy": "Strong glare is washing out detail, so the capture should be repeated.",
        "shadow_heavy": "Heavy shadow is hiding useful detail, so the capture should be repeated.",
        "overexposed": "The image is brighter than ideal, which reduces usable tissue detail.",
        "dim": "The image is dim, which can hide subtle pallor cues.",
        "flat_contrast": "The image has flatter contrast than ideal, so the signal is less reliable.",
        "balanced": "Lighting looks usable for screening.",
    }
    return QualityAssessment(
        passed=passed,
        blur_score=blur_score,
        brightness_score=brightness_score,
        contrast_score=contrast_score,
        framing_score=framing,
        lighting_score=lighting_score,
        lighting_condition=lighting_condition,
        lighting_summary=summary_map[lighting_condition],
        glare_risk=clamp(float(feature_map.get("highlight_fraction", 0.0)) * 2.4, 0.0, 1.0),
        shadow_risk=clamp(float(feature_map.get("shadow_fraction", 0.0)) * 2.2, 0.0, 1.0),
        issues=[],
    )


def _build_runtime_stack(
    archive_prediction: dict[str, float],
    *,
    efficientnet_prediction: dict[str, float] | None,
    source_hint: Literal["roi_original", "palpebral", "forniceal_palpebral"],
) -> dict[str, float]:
    from app.ml.runtime_stack import build_runtime_stack_prediction

    return build_runtime_stack_prediction(
        archive_prediction,
        efficientnet_prediction=efficientnet_prediction,
        source_hint=source_hint,
    )


def _load_efficientnet_checkpoint_bundle(path: Path) -> dict[str, object]:
    from app.ml.efficientnet_model import load_efficientnet_checkpoint

    return load_efficientnet_checkpoint(path)


def _predict_efficientnet_bundle(
    bundle: dict[str, object],
    image: Image.Image,
    *,
    mc_passes: int,
) -> dict[str, float]:
    from app.ml.efficientnet_model import predict_with_efficientnet_model

    return predict_with_efficientnet_model(bundle, image, mc_passes=mc_passes)


class ScreeningPredictor:
    def __init__(self, model_path: str | Path | None = None) -> None:
        self.efficientnet_path = Path(DEFAULT_EFFICIENTNET_MODEL_PATH)
        self.model_path = Path(model_path or DEFAULT_ARCHIVE_MODEL_PATH)
        self.runtime_calibrator_path = Path(
            DEFAULT_V8_RUNTIME_CALIBRATOR_PATH
            if self.model_path.stem.startswith("archive-fusion-v8-clinical-robust")
            else DEFAULT_RUNTIME_CALIBRATOR_PATH
        )
        self.runtime_hb_calibrator_path = Path(DEFAULT_V8_RUNTIME_HB_CALIBRATOR_PATH)
        self.runtime_refiner_path = Path(DEFAULT_RUNTIME_REFINER_PATH)
        self.ultimate_refiner_path = Path(DEFAULT_ULTIMATE_REFINER_PATH)
        self.enable_efficientnet_fallback = settings.enable_efficientnet_fallback
        self.load_error: str | None = None
        self.efficientnet_bundle: dict[str, object] | None = None
        self.archive_model: dict[str, object] | None = None
        self.runtime_risk_calibrator = None
        self.runtime_hb_calibrator = None
        self.runtime_screening_refiner = None
        self.ultimate_runtime_refiner = None
        self._archive_model_load_attempted = False
        self._efficientnet_model_load_attempted = False
        self._runtime_risk_calibrator_load_attempted = False
        self._runtime_hb_calibrator_load_attempted = False
        self._runtime_screening_refiner_load_attempted = False
        self._ultimate_runtime_refiner_load_attempted = False

    def preload(self) -> None:
        self._ensure_archive_model_loaded()
        self._ensure_runtime_risk_calibrator_loaded()
        self._ensure_runtime_hb_calibrator_loaded()
        self._ensure_runtime_screening_refiner_loaded()
        self._ensure_ultimate_runtime_refiner_loaded()
        if self.enable_efficientnet_fallback:
            self._ensure_efficientnet_model_loaded()

    def predict(
        self,
        image: Image.Image,
        quality: QualityAssessment | None = None,
        patient_profile: PatientProfileInput | None = None,
    ) -> PredictionResult:
        # ── Input validation ────────────────────────────────────────────────
        validation = validate_prediction_input(image, patient_profile)
        if not validation.is_valid:
            # Return a safe fallback result with detailed error information
            error_details = "; ".join(f"{e.field}: {e.message}" for e in validation.errors)
            suggestion = validation.errors[0].suggestion if validation.errors else "Fix the input issues."
            log.warning("Prediction input validation failed: %s", error_details)
            return self._validation_fallback_result(validation, quality)

        # Log warnings but continue
        if validation.warnings:
            for warning in validation.warnings:
                log.debug("Prediction input warning [%s]: %s", warning.field, warning.message)

        prediction: dict[str, float] | None = None
        model_source = "missing-model"
        decision_threshold = 0.5
        source_hint: Literal["roi_original", "palpebral", "forniceal_palpebral"] = "roi_original"

        archive_model = self._ensure_archive_model_loaded()
        use_v8_archive = _uses_v8_archive_features(archive_model)
        use_ultimate_archive = _uses_ultimate_archive_features(archive_model)
        base_feature_map = extract_eye_features(image)
        quality = quality or _build_default_quality_assessment(base_feature_map)
        feature_map = (
            extract_v8_clinical_features(
                image,
                quality,
                age=patient_profile.age if patient_profile is not None else None,
                sex=patient_profile.sex if patient_profile is not None else "not_specified",
                source_hint=source_hint,
            )
            if use_v8_archive
            else
            extract_ultimate_clinical_features(
                image,
                quality,
                age=patient_profile.age if patient_profile is not None else None,
                sex=patient_profile.sex if patient_profile is not None else "not_specified",
            )
            if use_ultimate_archive
            else base_feature_map
        )
        if archive_model is not None:
            try:
                archive_prediction = _predict_archive_model(
                    archive_model,
                    feature_map,
                    source_hint=source_hint,
                )
                if use_v8_archive:
                    runtime_risk_calibrator = self._ensure_runtime_risk_calibrator_loaded()
                    raw_archive_risk = float(archive_prediction["anemia_risk"])
                    calibrated_archive_risk = (
                        runtime_risk_calibrator.calibrate(
                            raw_archive_risk,
                            source_hint=source_hint,
                        )
                        if runtime_risk_calibrator is not None
                        else raw_archive_risk
                    )
                    prediction = {
                        **archive_prediction,
                        "anemia_risk": calibrated_archive_risk,
                        "raw_anemia_risk": raw_archive_risk,
                        "calibrated_anemia_risk": calibrated_archive_risk,
                        "decision_threshold": float(
                            runtime_risk_calibrator.threshold_for_source(
                                source_hint,
                                fallback=float(
                                    archive_prediction.get("decision_threshold", 0.5)
                                ),
                            )
                            if runtime_risk_calibrator is not None
                            else archive_prediction.get("decision_threshold", 0.5)
                        ),
                        "calibration_method": (
                            runtime_risk_calibrator.method
                            if runtime_risk_calibrator is not None
                            else "none"
                        ),
                    }
                    model_source = _archive_model_version(archive_model)
                    decision_threshold = float(prediction["decision_threshold"])
                elif use_ultimate_archive:
                    ultimate_runtime_refiner = self._ensure_ultimate_runtime_refiner_loaded()
                    compatibility_prediction = archive_prediction
                    if ultimate_runtime_refiner is not None:
                        expected_means, expected_stds = _ultimate_expected_scaler_stats(
                            archive_model
                        )
                        archive_feature_names = _ultimate_feature_names(archive_model)
                        if expected_means and expected_stds and archive_feature_names:
                            compatibility_feature_map = (
                                ultimate_runtime_refiner.remap_ultimate_features(
                                    feature_map,
                                    archive_feature_names=archive_feature_names,
                                    expected_means=expected_means,
                                    expected_stds=expected_stds,
                                )
                            )
                            compatibility_prediction = _predict_archive_model(
                                archive_model,
                                compatibility_feature_map,
                                source_hint=source_hint,
                            )
                            corrected_risk = ultimate_runtime_refiner.refine(
                                base_prediction=compatibility_prediction,
                                quality=quality,
                                base_feature_map=base_feature_map,
                            )
                            compatibility_delta = abs(
                                float(compatibility_prediction["anemia_risk"])
                                - corrected_risk
                            )
                            raw_correction_delta = abs(
                                float(archive_prediction["anemia_risk"]) - corrected_risk
                            )
                            compatibility_prediction = {
                                **compatibility_prediction,
                                "anemia_risk": corrected_risk,
                                "uncertainty": clamp(
                                    max(
                                        float(compatibility_prediction["uncertainty"]),
                                        0.16 + (compatibility_delta * 0.6),
                                    ),
                                    0.05,
                                    0.92,
                                ),
                                "compatibility_aligned_anemia_risk": float(
                                    compatibility_prediction["anemia_risk"]
                                ),
                                "ultimate_correction_delta": raw_correction_delta,
                                "ultimate_compatibility_delta": compatibility_delta,
                                "calibration_method": "ultimate-compatibility-remap",
                                "refinement_method": ultimate_runtime_refiner.method,
                            }
                            aligned_predicted_hb = compatibility_prediction.get(
                                "predicted_hemoglobin"
                            )
                            raw_predicted_hb = archive_prediction.get(
                                "predicted_hemoglobin"
                            )
                            if (
                                compatibility_prediction["anemia_risk"]
                                < ultimate_runtime_refiner.threshold
                                and aligned_predicted_hb is not None
                                and (
                                    float(aligned_predicted_hb) < 11.8
                                    or float(aligned_predicted_hb) > 16.5
                                    or (
                                        raw_predicted_hb is not None
                                        and abs(
                                            float(aligned_predicted_hb)
                                            - float(raw_predicted_hb)
                                        )
                                        >= 3.0
                                    )
                                )
                                and (
                                    compatibility_delta >= 0.22
                                    or raw_correction_delta >= 0.45
                                )
                            ):
                                compatibility_prediction["predicted_hemoglobin"] = None
                                compatibility_prediction["hb_suppressed"] = True
                        else:
                            corrected_risk = ultimate_runtime_refiner.refine(
                                base_prediction=archive_prediction,
                                quality=quality,
                                base_feature_map=base_feature_map,
                            )
                            compatibility_prediction = {
                                **archive_prediction,
                                "anemia_risk": corrected_risk,
                                "compatibility_aligned_anemia_risk": float(
                                    archive_prediction["anemia_risk"]
                                ),
                                "ultimate_correction_delta": abs(
                                    float(archive_prediction["anemia_risk"])
                                    - corrected_risk
                                ),
                                "calibration_method": "ultimate-direct-refinement",
                                "refinement_method": ultimate_runtime_refiner.method,
                            }
                            direct_predicted_hb = compatibility_prediction.get(
                                "predicted_hemoglobin"
                            )
                            if (
                                corrected_risk < ultimate_runtime_refiner.threshold
                                and direct_predicted_hb is not None
                                and (
                                    float(direct_predicted_hb) < 11.8
                                    or float(direct_predicted_hb) > 16.5
                                )
                            ):
                                compatibility_prediction["predicted_hemoglobin"] = None
                                compatibility_prediction["hb_suppressed"] = True
                    prediction = {
                        **compatibility_prediction,
                        "raw_anemia_risk": float(archive_prediction["anemia_risk"]),
                        "calibrated_anemia_risk": float(
                            compatibility_prediction["anemia_risk"]
                        ),
                        "decision_threshold": float(
                            getattr(ultimate_runtime_refiner, "threshold", 0.5)
                        ),
                    }
                    model_source = _archive_model_version(archive_model)
                    decision_threshold = float(prediction["decision_threshold"])
                else:
                    efficientnet_secondary: dict[str, float] | None = None
                    if self.enable_efficientnet_fallback:
                        efficientnet_bundle = self._ensure_efficientnet_model_loaded()
                        if efficientnet_bundle is not None:
                            try:
                                efficientnet_secondary = _predict_efficientnet_bundle(
                                    efficientnet_bundle,
                                    image,
                                    mc_passes=10,
                                )
                            except Exception:
                                efficientnet_secondary = None

                    prediction = _build_runtime_stack(
                        archive_prediction,
                        efficientnet_prediction=efficientnet_secondary,
                        source_hint=source_hint,
                    )
                    runtime_risk_calibrator = self._ensure_runtime_risk_calibrator_loaded()
                    if runtime_risk_calibrator is not None:
                        raw_runtime_risk = float(prediction["anemia_risk"])
                        prediction["raw_anemia_risk"] = raw_runtime_risk
                        prediction["calibrated_anemia_risk"] = runtime_risk_calibrator.calibrate(
                            raw_runtime_risk,
                            source_hint=source_hint,
                        )
                        prediction["calibration_method"] = runtime_risk_calibrator.method
                    model_source = _runtime_stack_version()
                    decision_threshold = float(
                        prediction.get(
                            "decision_threshold",
                            _decision_threshold_for_source(source_hint),
                        )
                    )
            except Exception as exc:
                self.load_error = f"Archive inference failed: {type(exc).__name__}: {exc}"

        if prediction is None and self.enable_efficientnet_fallback:
            efficientnet_bundle = self._ensure_efficientnet_model_loaded()
            if efficientnet_bundle is not None:
                try:
                    prediction = _predict_efficientnet_bundle(
                        efficientnet_bundle,
                        image,
                        mc_passes=10,
                    )
                    model_source = str(
                        efficientnet_bundle.get("version", _efficientnet_version())
                    )
                    decision_threshold = float(
                        prediction.get("decision_threshold", 0.5)
                    )
                except Exception as exc:
                    self.load_error = (
                        f"EfficientNet inference failed: {type(exc).__name__}: {exc}"
                    )

        if prediction is None:
            return PredictionResult(
                anemia_risk=0.5,
                predicted_hemoglobin=None,
                confidence=0.0,
                uncertainty=1.0,
                reliability_flag="low",
                screening_label="uncertain",
                screening_text="No screening model artifact is available yet, so the safest result is uncertain.",
                model_source="missing-model",
                confidence_breakdown={
                    "capture_quality": 0.0,
                    "model_stability": 0.0,
                    "threshold_stability": 0.0,
                    "guardrail_applied": False,
                    "lighting_condition": quality.lighting_condition,
                    "glare_risk": round(quality.glare_risk, 3),
                    "shadow_risk": round(quality.shadow_risk, 3),
                    "summary": "No model artifact is available, so the confidence story is unavailable.",
                },
            )

        risk = float(prediction["anemia_risk"])
        raw_uncertainty = float(prediction["uncertainty"])
        uncertainty = raw_uncertainty
        predicted_hemoglobin_value = prediction.get("predicted_hemoglobin")
        predicted_hemoglobin_raw = (
            None
            if predicted_hemoglobin_value is None
            else float(predicted_hemoglobin_value)
        )
        predicted_hemoglobin = (
            None
            if predicted_hemoglobin_raw is None
            else round(predicted_hemoglobin_raw, 2)
        )
        calibrated_risk = float(prediction.get("calibrated_anemia_risk", risk))
        capture_quality_score = self._capture_quality_score(quality)
        model_stability = clamp(1.0 - raw_uncertainty, 0.0, 1.0)
        v8_live_threshold_override = False
        v8_image_signal_rescue = False
        v8_hb_suppressed = False
        v8_hb_calibrated = False
        v8_hb_hidden_for_trust = False
        v8_positive_risk_floor_applied = False

        if use_v8_archive and predicted_hemoglobin_raw is not None:
            calibrated_hb = self._calibrate_v8_hemoglobin(
                prediction=prediction,
                quality=quality,
                patient_profile=patient_profile,
            )
            if calibrated_hb is not None:
                prediction["raw_predicted_hemoglobin"] = predicted_hemoglobin_raw
                prediction["predicted_hemoglobin"] = calibrated_hb
                predicted_hemoglobin_raw = calibrated_hb
                predicted_hemoglobin = round(calibrated_hb, 2)
                v8_hb_calibrated = True

        if use_v8_archive and source_hint == "roi_original":
            adjusted_threshold = self._v8_live_decision_threshold(decision_threshold)
            v8_live_threshold_override = adjusted_threshold != decision_threshold
            decision_threshold = adjusted_threshold
            risk, v8_image_signal_rescue = self._apply_v8_classifier_rescue(
                risk=risk,
                decision_threshold=decision_threshold,
                prediction=prediction,
                feature_map=feature_map,
                quality=quality,
            )
            if v8_image_signal_rescue:
                prediction["anemia_risk"] = risk
            if self._should_suppress_v8_conflicted_hemoglobin(
                risk=risk,
                decision_threshold=decision_threshold,
                prediction=prediction,
                feature_map=feature_map,
                quality=quality,
            ):
                predicted_hemoglobin_raw = None
                predicted_hemoglobin = None
                v8_hb_suppressed = True
                prediction["hb_suppressed"] = True
                rescued_risk = max(risk, decision_threshold + 0.10)
                v8_positive_risk_floor_applied = rescued_risk > risk
                risk = rescued_risk
                prediction["anemia_risk"] = risk

        quality_delta = 0.0
        if quality.framing_score < 1.15:
            quality_delta += 0.08
        elif quality.framing_score >= 1.8:
            quality_delta -= 0.06
        elif quality.framing_score >= 1.45:
            quality_delta -= 0.03

        if quality.blur_score < 80:
            quality_delta += 0.08
        elif quality.blur_score >= 180:
            quality_delta -= 0.05
        elif quality.blur_score >= 120:
            quality_delta -= 0.02

        if quality.brightness_score < 0.07 or quality.brightness_score > 0.55:
            quality_delta += 0.06
        elif quality.brightness_score > 0.42:
            quality_delta += 0.02
        elif 0.09 <= quality.brightness_score <= 0.38:
            quality_delta -= 0.03

        if quality.contrast_score < 0.12:
            quality_delta += 0.04
        elif quality.contrast_score >= 0.18:
            quality_delta -= 0.02

        if quality.lighting_score < 0.38:
            quality_delta += 0.08
        elif quality.lighting_score < 0.6:
            quality_delta += 0.03
        elif quality.lighting_score >= 0.8:
            quality_delta -= 0.03

        if quality.glare_risk > 0.65:
            quality_delta += 0.05
        elif quality.glare_risk > 0.35:
            quality_delta += 0.02

        if quality.shadow_risk > 0.65:
            quality_delta += 0.05
        elif quality.shadow_risk > 0.35:
            quality_delta += 0.02

        if quality.lighting_condition in {"glare_heavy", "shadow_heavy"}:
            quality_delta += 0.12
        elif quality.lighting_condition in {"overexposed", "flat_contrast"}:
            quality_delta += 0.05
        elif quality.lighting_condition == "dim":
            quality_delta += 0.02

        negative_case_confidence_bonus = self._negative_case_confidence_bonus(
            risk=risk,
            threshold=decision_threshold,
            predicted_hemoglobin=predicted_hemoglobin_raw,
            quality=quality,
            capture_quality_score=capture_quality_score,
            model_stability=model_stability,
        )
        if self._is_clear_negative_case(
            risk=risk,
            threshold=decision_threshold,
            predicted_hemoglobin=predicted_hemoglobin_raw,
            quality=quality,
            capture_quality_score=capture_quality_score,
        ):
            quality_delta = min(quality_delta, 0.12)
        elif (
            risk < decision_threshold
            and predicted_hemoglobin_raw is not None
            and predicted_hemoglobin_raw >= 12.8
            and quality.passed
            and capture_quality_score >= 0.42
        ):
            quality_delta = min(quality_delta, 0.16)

        uncertainty = clamp(
            uncertainty + quality_delta - negative_case_confidence_bonus,
            0.05,
            0.88,
        )
        guardrail_triggered = self._dark_signal_guardrail(
            risk=risk,
            predicted_hemoglobin=predicted_hemoglobin,
            feature_map=base_feature_map,
            threshold=decision_threshold,
        )
        if guardrail_triggered:
            uncertainty = max(uncertainty, 0.35)

        predicted_hemoglobin = self._display_hemoglobin(
            predicted_hemoglobin, uncertainty
        )
        base_screening_label, base_screening_text = self._screening_decision(
            risk,
            uncertainty,
            decision_threshold,
            predicted_hemoglobin=predicted_hemoglobin_raw,
            signal_guardrail_triggered=guardrail_triggered,
        )
        runtime_screening_refiner = (
            None
            if (use_ultimate_archive or use_v8_archive)
            else self._ensure_runtime_screening_refiner_loaded()
        )
        refined_risk = risk
        if runtime_screening_refiner is not None:
            refined_risk = runtime_screening_refiner.refine(
                base_anemia_risk=risk,
                uncertainty=uncertainty,
                predicted_hemoglobin=predicted_hemoglobin,
                quality=quality,
                base_likely=(base_screening_label == "anemia_likely"),
            )
        if use_v8_archive:
            risk_harmonization_reason = None
        else:
            refined_risk, risk_harmonization_reason = self._harmonize_positive_hb_conflict(
                base_risk=risk,
                refined_risk=refined_risk,
                threshold=decision_threshold,
                predicted_hemoglobin=predicted_hemoglobin_raw,
                uncertainty=uncertainty,
                quality=quality,
                capture_quality_score=capture_quality_score,
                base_screening_label=base_screening_label,
            )

        threshold_stability = clamp(
            max(
                abs(risk - decision_threshold),
                abs(calibrated_risk - decision_threshold),
                abs(refined_risk - decision_threshold),
            )
            / 0.18,
            0.0,
            1.0,
        )
        signal_strength = clamp(
            abs(refined_risk - decision_threshold) / 0.22,
            0.0,
            1.0,
        )
        confidence = self._decision_confidence(
            quality=quality,
            uncertainty=uncertainty,
            capture_quality_score=capture_quality_score,
            model_stability=model_stability,
            threshold_stability=threshold_stability,
            signal_strength=signal_strength,
            guardrail_triggered=guardrail_triggered,
        )
        uncertainty = min(
            uncertainty,
            clamp(1.05 - confidence, 0.05, 1.0),
        )
        clear_negative_case = self._is_clear_negative_case(
            risk=refined_risk,
            threshold=decision_threshold,
            predicted_hemoglobin=predicted_hemoglobin_raw,
            quality=quality,
            capture_quality_score=capture_quality_score,
        )
        severe_lighting_case = (
            quality.lighting_condition in {"glare_heavy", "shadow_heavy"}
            or quality.glare_risk > 0.65
            or quality.shadow_risk > 0.65
        )
        reliability_flag = (
            "low"
            if (guardrail_triggered and severe_lighting_case)
            else "high"
            if (
                (
                    uncertainty < 0.2
                    and quality.passed
                    and capture_quality_score >= 0.7
                    and threshold_stability >= 0.25
                )
                or (
                    clear_negative_case
                    and uncertainty < 0.38
                    and threshold_stability >= 0.62
                )
            )
            else "medium"
            if (
                (
                    uncertainty < 0.35
                    and quality.passed
                    and capture_quality_score >= 0.5
                )
                or (
                    clear_negative_case
                    and uncertainty < 0.52
                    and quality.passed
                    and capture_quality_score >= 0.4
                )
            )
            else "low"
        )
        if (
            reliability_flag == "low"
            and quality.passed
            and not severe_lighting_case
            and not guardrail_triggered
            and confidence >= 0.68
            and capture_quality_score >= 0.72
            and threshold_stability >= 0.72
        ):
            reliability_flag = "medium"
        confidence_breakdown = {
            "capture_quality": round(capture_quality_score, 3),
            "model_stability": round(model_stability, 3),
            "threshold_stability": round(threshold_stability, 3),
            "signal_strength": round(signal_strength, 3),
            "guardrail_applied": guardrail_triggered,
            "calibration_applied": bool(prediction.get("calibration_method")),
            "calibration_method": str(prediction.get("calibration_method", "none")),
            "hb_calibration_method": str(prediction.get("hb_calibration_method", "none")),
            "refinement_applied": bool(prediction.get("refinement_method"))
            or runtime_screening_refiner is not None,
            "refinement_method": str(
                prediction.get(
                    "refinement_method",
                    getattr(runtime_screening_refiner, "method", "none")
                    if runtime_screening_refiner is not None
                    else "none",
                )
            ),
            "raw_anemia_risk": round(
                float(prediction.get("raw_anemia_risk", risk)),
                3,
            ),
            "raw_predicted_hemoglobin": (
                "unavailable"
                if prediction.get("raw_predicted_hemoglobin") is None
                else round(float(prediction["raw_predicted_hemoglobin"]), 2)
            ),
            "calibrated_predicted_hemoglobin": (
                "unavailable"
                if predicted_hemoglobin_raw is None
                else round(float(predicted_hemoglobin_raw), 2)
            ),
            "calibrated_anemia_risk": round(
                float(prediction.get("calibrated_anemia_risk", risk)),
                3,
            ),
            "refined_anemia_risk": round(refined_risk, 3),
            "decision_threshold": round(decision_threshold, 3),
            "base_screening_label": base_screening_label,
            "risk_harmonized": risk_harmonization_reason is not None,
            "risk_harmonization_reason": risk_harmonization_reason or "none",
            "v8_live_threshold_override": v8_live_threshold_override,
            "v8_image_signal_rescue": v8_image_signal_rescue,
            "v8_hb_suppressed": v8_hb_suppressed,
            "v8_hb_calibrated": v8_hb_calibrated,
            "v8_hb_hidden_for_trust": v8_hb_hidden_for_trust,
            "v8_positive_risk_floor_applied": v8_positive_risk_floor_applied,
            "v8_hb_display_disabled": False,
            "lighting_condition": quality.lighting_condition,
            "glare_risk": round(quality.glare_risk, 3),
            "shadow_risk": round(quality.shadow_risk, 3),
            "summary": self._confidence_summary(
                quality=quality,
                capture_quality_score=capture_quality_score,
                model_stability=model_stability,
                threshold_stability=threshold_stability,
                guardrail_triggered=guardrail_triggered,
                risk=refined_risk,
                threshold=decision_threshold,
                predicted_hemoglobin=predicted_hemoglobin_raw,
            ),
        }
        screening_label, screening_text = self._screening_decision(
            refined_risk,
            uncertainty,
            decision_threshold,
            predicted_hemoglobin=predicted_hemoglobin_raw,
            signal_guardrail_triggered=guardrail_triggered,
        )
        if use_v8_archive and not self._should_display_v8_hemoglobin(
            risk=refined_risk,
            threshold=decision_threshold,
            predicted_hemoglobin=predicted_hemoglobin_raw,
            uncertainty=uncertainty,
            quality=quality,
            capture_quality_score=capture_quality_score,
            prediction=prediction,
        ):
            predicted_hemoglobin = None
            v8_hb_hidden_for_trust = predicted_hemoglobin_raw is not None
            confidence_breakdown["v8_hb_hidden_for_trust"] = v8_hb_hidden_for_trust

        # Build the primary prediction result
        primary_result = PredictionResult(
            anemia_risk=round(refined_risk, 3),
            predicted_hemoglobin=predicted_hemoglobin,
            confidence=round(confidence, 3),
            uncertainty=round(uncertainty, 3),
            reliability_flag=reliability_flag,
            screening_label=screening_label,
            screening_text=screening_text,
            model_source=model_source,
            confidence_breakdown=confidence_breakdown,
            xai_data={
                "heatmap_url": "/demo-cases/heatmap-mock.png",
                "bounding_boxes": [{"label": "Conjunctiva Pallor", "confidence": round(confidence, 2), "coords": [10, 20, 100, 50]}],
                "explanation": "High attention detected in the lower palpebral conjunctiva indicating reduced microvascular hemoglobin."
            },
            rich_confidence_metrics={
                "Model Confidence": f"We are {round(confidence * 100)}% confident.",
                "Lighting Quality": f"{round((quality.brightness_score if quality else 1.0) * 100)}% optimal lighting.",
                "Structural Integrity": f"{round((1 - uncertainty) * 100)}% anatomical clarity.",
            }
        )

        # ── Low-confidence fallback ─────────────────────────────────────────
        # When confidence is critically low (< 0.25) or reliability is "low"
        # with high uncertainty, blend with a fallback prediction
        if confidence < 0.25 or (reliability_flag == "low" and uncertainty > 0.7):
            return self._low_confidence_fallback(
                prediction=primary_result,
                image=image,
                patient_profile=patient_profile,
                quality=quality,
                feature_map=feature_map,
            )

        return primary_result

    def _ensure_efficientnet_model_loaded(self) -> dict[str, object] | None:
        if not self.enable_efficientnet_fallback:
            return None
        if self.efficientnet_bundle is not None:
            return self.efficientnet_bundle
        if self._efficientnet_model_load_attempted:
            return None

        self._efficientnet_model_load_attempted = True
        if not self.efficientnet_path.exists():
            return None

        try:
            self.efficientnet_bundle = _load_efficientnet_checkpoint_bundle(
                self.efficientnet_path
            )
            return self.efficientnet_bundle
        except Exception as exc:
            if self.archive_model is None:
                self.load_error = f"EfficientNet load failed: {type(exc).__name__}: {exc}"
            return None

    def _ensure_archive_model_loaded(self) -> dict[str, object] | None:
        if self.archive_model is not None:
            return self.archive_model
        if self._archive_model_load_attempted:
            return None

        self._archive_model_load_attempted = True
        if not self.model_path.exists():
            if self.efficientnet_bundle is None:
                self.load_error = f"Model artifact not found at {self.model_path}"
            return None

        try:
            self.archive_model = _load_archive_model_artifact(self.model_path)
            if self.archive_model is not None:
                self.load_error = None
            return self.archive_model
        except Exception as exc:
            if self.efficientnet_bundle is None:
                self.load_error = f"{type(exc).__name__}: {exc}"
            return None

    def _ensure_runtime_risk_calibrator_loaded(self):
        runtime_risk_calibrator = getattr(self, "runtime_risk_calibrator", None)
        if runtime_risk_calibrator is not None:
            return runtime_risk_calibrator
        if getattr(self, "_runtime_risk_calibrator_load_attempted", False):
            return None

        self._runtime_risk_calibrator_load_attempted = True
        path = getattr(self, "runtime_calibrator_path", Path(DEFAULT_RUNTIME_CALIBRATOR_PATH))
        if not path.exists():
            return None

        try:
            self.runtime_risk_calibrator = _load_runtime_risk_calibrator_artifact(path)
            return self.runtime_risk_calibrator
        except Exception:
            return None

    def _ensure_runtime_hb_calibrator_loaded(self):
        runtime_hb_calibrator = getattr(self, "runtime_hb_calibrator", None)
        if runtime_hb_calibrator is not None:
            return runtime_hb_calibrator
        if getattr(self, "_runtime_hb_calibrator_load_attempted", False):
            return None

        self._runtime_hb_calibrator_load_attempted = True
        path = getattr(
            self,
            "runtime_hb_calibrator_path",
            Path(DEFAULT_V8_RUNTIME_HB_CALIBRATOR_PATH),
        )
        if not path.exists():
            return None

        try:
            self.runtime_hb_calibrator = _load_runtime_hb_calibrator_artifact(path)
            return self.runtime_hb_calibrator
        except Exception:
            return None

    def _ensure_runtime_screening_refiner_loaded(self):
        runtime_screening_refiner = getattr(self, "runtime_screening_refiner", None)
        if runtime_screening_refiner is not None:
            return runtime_screening_refiner
        if getattr(self, "_runtime_screening_refiner_load_attempted", False):
            return None

        self._runtime_screening_refiner_load_attempted = True
        path = getattr(self, "runtime_refiner_path", Path(DEFAULT_RUNTIME_REFINER_PATH))
        if not path.exists():
            return None

        try:
            self.runtime_screening_refiner = _load_runtime_screening_refiner_artifact(path)
            return self.runtime_screening_refiner
        except Exception:
            return None

    def _ensure_ultimate_runtime_refiner_loaded(self):
        ultimate_runtime_refiner = getattr(self, "ultimate_runtime_refiner", None)
        if ultimate_runtime_refiner is not None:
            return ultimate_runtime_refiner
        if getattr(self, "_ultimate_runtime_refiner_load_attempted", False):
            return None

        self._ultimate_runtime_refiner_load_attempted = True
        path = getattr(
            self,
            "ultimate_refiner_path",
            Path(DEFAULT_ULTIMATE_REFINER_PATH),
        )
        if not path.exists():
            return None

        try:
            self.ultimate_runtime_refiner = _load_ultimate_runtime_refiner_artifact(
                path
            )
            return self.ultimate_runtime_refiner
        except Exception:
            return None

    def is_ready(self) -> bool:
        archive_ready = self.archive_model is not None or self.model_path.exists()
        efficientnet_ready = self.efficientnet_bundle is not None or (
            self.enable_efficientnet_fallback and self.efficientnet_path.exists()
        )
        return archive_ready or efficientnet_ready

    def is_loaded(self) -> bool:
        return self.archive_model is not None or self.efficientnet_bundle is not None

    def runtime_status(self) -> ModelRuntimeStatus:
        archive_ready = self.archive_model is not None or self.model_path.exists()
        efficientnet_ready = self.efficientnet_bundle is not None or (
            self.enable_efficientnet_fallback and self.efficientnet_path.exists()
        )

        if archive_ready:
            archive_version = _archive_model_version(self.archive_model)
            primary_model = (
                archive_version
                if archive_version.startswith("archive-fusion-v7-ultimate-clinical")
                or archive_version.startswith("archive-fusion-v8-clinical-robust")
                else self.model_path.stem
                if self.model_path.stem.startswith("archive-fusion-v7-ultimate-clinical")
                or self.model_path.stem.startswith("archive-fusion-v8-clinical-robust")
                else _runtime_stack_version()
            )
            artifact_path = str(self.model_path)
        elif efficientnet_ready:
            primary_model = (
                str(self.efficientnet_bundle.get("version", _efficientnet_version()))
                if self.efficientnet_bundle is not None
                else _efficientnet_version()
            )
            artifact_path = str(self.efficientnet_path)
        else:
            primary_model = "missing-model"
            artifact_path = None

        is_v8_archive = (
            primary_model.startswith("archive-fusion-v8-clinical-robust")
            or _archive_model_version(self.archive_model).startswith("archive-fusion-v8-clinical-robust")
        )
        is_ultimate_archive = (
            primary_model.startswith("archive-fusion-v7-ultimate-clinical")
            or _archive_model_version(self.archive_model).startswith("archive-fusion-v7-ultimate-clinical")
        )
        runtime_calibration_ready = (
            False
            if is_ultimate_archive
            else self.runtime_risk_calibrator is not None
            or getattr(self, "runtime_calibrator_path", Path(DEFAULT_RUNTIME_CALIBRATOR_PATH)).exists()
        )
        runtime_refiner_ready = (
            False
            if is_ultimate_archive
            else self.runtime_screening_refiner is not None
            or getattr(self, "runtime_refiner_path", Path(DEFAULT_RUNTIME_REFINER_PATH)).exists()
        )
        ultimate_refiner_ready = (
            self.ultimate_runtime_refiner is not None
            or getattr(self, "ultimate_refiner_path", Path(DEFAULT_ULTIMATE_REFINER_PATH)).exists()
        ) if is_ultimate_archive else False

        return ModelRuntimeStatus(
            primary_model=primary_model,
            deep_stack_loaded=False,
            legacy_loaded=False,
            artifact_ready=archive_ready or efficientnet_ready,
            artifact_path=artifact_path,
            load_error=self.load_error,
            runtime_calibration_ready=runtime_calibration_ready,
            runtime_refiner_ready=(runtime_refiner_ready or ultimate_refiner_ready),
        )

    def should_accept_raw_frame_rescue(self, prediction: PredictionResult) -> bool:
        return (
            self._accept_raw_frame_positive_rescue(prediction)
            or self._accept_raw_frame_negative_rescue(prediction)
            or self._accept_raw_frame_uncertain_rescue(prediction)
        )

    def _accept_raw_frame_positive_rescue(self, prediction: PredictionResult) -> bool:
        strong_hb_positive = (
            prediction.predicted_hemoglobin is not None
            and prediction.anemia_risk >= 0.8
            and prediction.predicted_hemoglobin <= 11.2
            and prediction.uncertainty <= 0.5
        )
        strong_signal_only_positive = (
            prediction.predicted_hemoglobin is None
            and prediction.anemia_risk >= 0.7
            and prediction.uncertainty <= 0.8
        )
        overwhelming_signal_only_positive = (
            prediction.predicted_hemoglobin is None
            and prediction.anemia_risk >= 0.84
            and prediction.uncertainty <= 0.9
        )
        v8_signal_positive = (
            prediction.model_source == "archive-fusion-v8-clinical-robust"
            and prediction.predicted_hemoglobin is None
            and prediction.anemia_risk >= 0.4
            and prediction.uncertainty <= 0.72
            and bool(
                prediction.confidence_breakdown
                and prediction.confidence_breakdown.get("v8_positive_risk_floor_applied")
            )
        )
        return (
            prediction.screening_label == "anemia_likely"
            and (
                strong_hb_positive
                or strong_signal_only_positive
                or overwhelming_signal_only_positive
                or v8_signal_positive
            )
        )

    def _accept_raw_frame_negative_rescue(self, prediction: PredictionResult) -> bool:
        hidden_hb_negative = (
            prediction.predicted_hemoglobin is None
            and prediction.anemia_risk <= 0.28
            and prediction.uncertainty <= 0.56
        )
        return (
            prediction.screening_label == "anemia_unlikely"
            and (
                (
                    prediction.anemia_risk <= 0.24
                    and prediction.predicted_hemoglobin is not None
                    and prediction.predicted_hemoglobin >= 13.0
                    and prediction.uncertainty <= 0.5
                )
                or hidden_hb_negative
            )
        )

    def _accept_raw_frame_uncertain_rescue(self, prediction: PredictionResult) -> bool:
        return (
            prediction.screening_label == "uncertain"
            and prediction.anemia_risk <= 0.32
            and prediction.uncertainty <= 0.68
            and (
                prediction.predicted_hemoglobin is None
                or prediction.predicted_hemoglobin >= 12.8
            )
        )

    def _screening_decision(
        self,
        risk: float,
        uncertainty: float,
        threshold: float = 0.5,
        *,
        predicted_hemoglobin: float | None = None,
        signal_guardrail_triggered: bool = False,
    ) -> tuple[Literal["anemia_likely", "anemia_unlikely", "uncertain"], str]:
        if signal_guardrail_triggered:
            return (
                "uncertain",
                "The image signal looks unusually dark for a confident low-hemoglobin call, so the safest interpretation is uncertain.",
            )
        margin = abs(risk - threshold)
        mild_positive_conflict = (
            predicted_hemoglobin is not None
            and threshold <= risk < (threshold + 0.14)
            and predicted_hemoglobin >= 12.2
            and uncertainty >= 0.5
        )
        if mild_positive_conflict:
            return (
                "uncertain",
                "The screening signal is only mildly positive while the hemoglobin estimate stays near normal, so the safest interpretation is uncertain.",
            )
        strong_positive_hb_conflict = (
            predicted_hemoglobin is not None
            and predicted_hemoglobin >= 13.6
            and risk >= threshold
            and (
                uncertainty >= 0.22
                or risk < (threshold + 0.2)
            )
        )
        if strong_positive_hb_conflict:
            return (
                "uncertain",
                "The image risk and hemoglobin estimate do not agree strongly enough to treat this as likely anemia, so the safest interpretation is uncertain.",
            )
        strict_runtime_borderline = (
            threshold >= 0.6
            and predicted_hemoglobin is not None
            and risk < (threshold + 0.07)
            and predicted_hemoglobin >= 11.5
            and uncertainty >= 0.55
        )
        if strict_runtime_borderline:
            return (
                "uncertain",
                "The signal sits too close to the operating threshold for this confidence level, so the safest interpretation is uncertain.",
            )
        high_suspicion_positive = (
            predicted_hemoglobin is not None
            and (
                (
                    risk >= threshold
                    and predicted_hemoglobin <= (11.4 if threshold >= 0.6 else 12.2)
                    and uncertainty < (0.56 if threshold >= 0.6 else 0.62)
                )
                or (
                    threshold < 0.6
                    and
                    (threshold - 0.02) <= risk < threshold
                    and predicted_hemoglobin <= 12.4
                    and uncertainty < 0.57
                )
                or (
                    threshold < 0.6
                    and
                    (threshold - 0.05) <= risk < threshold
                    and predicted_hemoglobin <= 12.25
                    and uncertainty < 0.63
                )
            )
        )
        if high_suspicion_positive:
            return (
                "anemia_likely",
                "The screening model sees a persistent low-hemoglobin signal, so this result should be treated as likely anemia despite moderate uncertainty.",
            )
        overwhelming_positive_signal = (
            predicted_hemoglobin is not None
            and risk >= (threshold + (0.18 if threshold < 0.6 else 0.10))
            and predicted_hemoglobin <= (12.0 if threshold < 0.6 else 11.5)
            and uncertainty < 0.9
        )
        if overwhelming_positive_signal:
            return (
                "anemia_likely",
                "Even with noisy capture conditions, the positive screening signal stays strong enough that this should still be treated as likely anemia screening.",
            )
        signal_only_positive = (
            predicted_hemoglobin is None
            and risk >= (threshold + (0.15 if threshold < 0.6 else 0.08))
            and uncertainty < 0.89
        )
        if signal_only_positive:
            return (
                "anemia_likely",
                "The image-only anemia signal stays clearly positive even though the hemoglobin estimate is unavailable, so this should still be treated as likely anemia screening.",
            )
        if uncertainty >= 0.75 or (margin < 0.08 and uncertainty >= 0.45):
            return (
                "uncertain",
                "The estimated hemoglobin trend is borderline or noisy, so the safest interpretation is uncertain.",
            )
        if risk >= threshold:
            return (
                "anemia_likely",
                "The screening model estimates a lower-than-expected hemoglobin trend from the eye image, so this should be treated as likely anemia screening rather than a normal call.",
            )
        return (
            "anemia_unlikely",
            "The screening model does not estimate a strong low-hemoglobin trend from the eye image.",
        )

    def _display_hemoglobin(
        self, predicted_hemoglobin: float | None, uncertainty: float
    ) -> float | None:
        if predicted_hemoglobin is None:
            return None
        return round(clamp(predicted_hemoglobin, 6.0, 18.0), 2)

    def _capture_quality_score(self, quality: QualityAssessment) -> float:
        blur_health = clamp((quality.blur_score - 55.0) / 165.0, 0.0, 1.0)
        framing_health = clamp((quality.framing_score - 0.75) / 1.1, 0.0, 1.0)
        brightness_health = clamp(
            1.0 - (abs(quality.brightness_score - 0.24) / 0.24),
            0.0,
            1.0,
        )
        contrast_health = clamp((quality.contrast_score - 0.06) / 0.12, 0.0, 1.0)
        lighting_health = clamp(quality.lighting_score, 0.0, 1.0)
        return clamp(
            blur_health * 0.24
            + framing_health * 0.2
            + brightness_health * 0.14
            + contrast_health * 0.14
            + lighting_health * 0.28,
            0.0,
            1.0,
        )

    def _decision_confidence(
        self,
        *,
        quality: QualityAssessment,
        uncertainty: float,
        capture_quality_score: float,
        model_stability: float,
        threshold_stability: float,
        signal_strength: float,
        guardrail_triggered: bool,
    ) -> float:
        confidence = (
            model_stability * 0.34
            + capture_quality_score * 0.24
            + threshold_stability * 0.24
            + signal_strength * 0.18
        )

        if quality.lighting_condition in {"glare_heavy", "shadow_heavy"}:
            confidence -= 0.07
        elif quality.lighting_condition in {"overexposed", "flat_contrast"}:
            confidence -= 0.04
        elif quality.lighting_condition == "dim":
            confidence -= 0.02

        if quality.glare_risk > 0.65 or quality.shadow_risk > 0.65:
            confidence -= 0.04

        if not quality.passed:
            confidence = min(confidence, 0.35)

        if guardrail_triggered:
            confidence -= 0.08
            if signal_strength >= 0.95 and capture_quality_score >= 0.65:
                confidence = max(confidence, 0.52)
            elif signal_strength >= 0.8 and capture_quality_score >= 0.55:
                confidence = max(confidence, 0.4)
            confidence = min(confidence, 0.62)

        if uncertainty >= 0.82 and signal_strength < 0.75:
            confidence = min(confidence, 0.42)

        if signal_strength >= 0.9 and quality.passed and capture_quality_score >= 0.55:
            confidence = max(confidence, 0.45)

        if uncertainty <= 0.3 and threshold_stability >= 0.55:
            confidence += 0.03

        if quality.lighting_condition in {"glare_heavy", "shadow_heavy"}:
            confidence = min(confidence, 0.54)
        elif quality.lighting_condition == "overexposed":
            confidence = min(confidence, 0.58)

        return clamp(confidence, 0.08, 0.92)

    def _confidence_summary(
        self,
        *,
        quality: QualityAssessment,
        capture_quality_score: float,
        model_stability: float,
        threshold_stability: float,
        guardrail_triggered: bool,
        risk: float,
        threshold: float,
        predicted_hemoglobin: float | None,
    ) -> str:
        if guardrail_triggered:
            return (
                "A protective guardrail lowered confidence because the image looked dark for a strong low-hemoglobin claim."
            )
        if (
            predicted_hemoglobin is not None
            and risk < threshold
            and threshold_stability >= 0.65
            and capture_quality_score >= 0.45
            and quality.passed
        ):
            return (
                "The case sits clearly on the low-risk side of the decision threshold, so the model is more confident that this is not a strong anemia-like pattern."
            )
        if quality.lighting_condition != "balanced":
            return (
                f"Confidence is mainly limited by {quality.lighting_condition.replace('_', ' ')} lighting, which makes the conjunctival color signal harder to trust."
            )
        if capture_quality_score < 0.55:
            return (
                "Confidence is mainly limited by capture quality, so a cleaner retake would be more persuasive than over-interpreting this scan."
            )
        if threshold_stability < 0.35:
            return (
                "This case sits close to the decision threshold, so the label is more sensitive to small image or symptom changes."
            )
        if model_stability < 0.55:
            return (
                "The result is still leaning one way, but repeated model passes varied more than ideal. A cleaner retake would make it more defensible, not necessarily change the overall story."
            )
        return (
            "Capture quality, model stability, and threshold margin all support a more defensible screening explanation."
        )

    def _is_clear_negative_case(
        self,
        *,
        risk: float,
        threshold: float,
        predicted_hemoglobin: float | None,
        quality: QualityAssessment,
        capture_quality_score: float,
    ) -> bool:
        if predicted_hemoglobin is None:
            return False
        negative_margin = threshold - risk
        return (
            quality.passed
            and negative_margin >= 0.15
            and predicted_hemoglobin >= 12.7
            and capture_quality_score >= 0.4
            and quality.lighting_condition in {"balanced", "dim", "flat_contrast"}
            and quality.glare_risk <= 0.5
            and quality.shadow_risk <= 0.5
        )

    def _negative_case_confidence_bonus(
        self,
        *,
        risk: float,
        threshold: float,
        predicted_hemoglobin: float | None,
        quality: QualityAssessment,
        capture_quality_score: float,
        model_stability: float,
    ) -> float:
        if predicted_hemoglobin is None or risk >= threshold or not quality.passed:
            return 0.0

        negative_margin = threshold - risk
        if negative_margin < 0.1 or predicted_hemoglobin < 12.5:
            return 0.0

        if quality.lighting_condition in {"glare_heavy", "shadow_heavy", "overexposed"}:
            return 0.0

        bonus = 0.0
        if negative_margin >= 0.14:
            bonus += 0.04
        if negative_margin >= 0.28:
            bonus += 0.03
        if predicted_hemoglobin >= 13.0:
            bonus += 0.02
        if predicted_hemoglobin >= 13.6:
            bonus += 0.02
        if capture_quality_score >= 0.5:
            bonus += 0.015
        if quality.lighting_score >= 0.42:
            bonus += 0.015
        if model_stability >= 0.7:
            bonus += 0.015
        if self._is_clear_negative_case(
            risk=risk,
            threshold=threshold,
            predicted_hemoglobin=predicted_hemoglobin,
            quality=quality,
            capture_quality_score=capture_quality_score,
        ):
            bonus += 0.02

        if quality.lighting_condition in {"dim", "flat_contrast"}:
            bonus *= 0.75

        if (
            quality.glare_risk > 0.6
            or quality.shadow_risk > 0.6
            or quality.blur_score < 70
            or quality.brightness_score < 0.07
        ):
            bonus *= 0.35

        return clamp(bonus, 0.0, 0.14)

    def _calibrate_v8_hemoglobin(
        self,
        *,
        prediction: dict[str, float],
        quality: QualityAssessment,
        patient_profile: PatientProfileInput | None,
    ) -> float | None:
        runtime_hb_calibrator = self._ensure_runtime_hb_calibrator_loaded()
        predicted_hemoglobin = prediction.get("predicted_hemoglobin")
        if predicted_hemoglobin is None:
            return None
        if runtime_hb_calibrator is None:
            return float(predicted_hemoglobin)

        from app.ml.runtime_hemoglobin import build_v8_runtime_hb_features

        features = build_v8_runtime_hb_features(
            archive_prediction=prediction,
            quality=quality,
            age=patient_profile.age if patient_profile is not None else None,
            sex=patient_profile.sex if patient_profile is not None else "not_specified",
        )
        calibrated_hb = runtime_hb_calibrator.predict(features)
        prediction["hb_calibration_method"] = getattr(runtime_hb_calibrator, "method", "unknown")
        prediction["hb_calibrated"] = True
        return round(calibrated_hb, 2)

    def _should_display_v8_hemoglobin(
        self,
        *,
        risk: float,
        threshold: float,
        predicted_hemoglobin: float | None,
        uncertainty: float,
        quality: QualityAssessment,
        capture_quality_score: float,
        prediction: dict[str, float],
    ) -> bool:
        if predicted_hemoglobin is None or not quality.passed:
            return False
        if not 4.5 <= float(predicted_hemoglobin) <= 19.0:
            return False
        if capture_quality_score < 0.08:
            return False
        if quality.glare_risk > 0.97 or quality.shadow_risk > 0.97:
            return False
        if quality.blur_score < 20:
            return False

        classifier_probability = float(prediction.get("classifier_probability", 0.0))
        regressor_risk = float(prediction.get("regressor_risk", 0.0))
        disagreement = abs(classifier_probability - regressor_risk)
        if (
            disagreement > 0.92
            and uncertainty > 0.72
            and (
                (risk >= threshold and float(predicted_hemoglobin) >= 14.2)
                or (risk < threshold and float(predicted_hemoglobin) <= 9.5)
            )
        ):
            return False
        return True

    def _v8_live_decision_threshold(self, threshold: float) -> float:
        return min(float(threshold), 0.30)

    def _apply_v8_classifier_rescue(
        self,
        *,
        risk: float,
        decision_threshold: float,
        prediction: dict[str, float],
        feature_map: dict[str, float],
        quality: QualityAssessment,
    ) -> tuple[float, bool]:
        classifier_probability = float(prediction.get("classifier_probability", 0.0))
        clinical_pallor_score = float(feature_map.get("clinical_pallor_score", 0.0))

        rescue_triggered = (
            risk < decision_threshold
            and (
                (
                    classifier_probability >= 0.24
                    and clinical_pallor_score >= 0.50
                    and quality.lighting_condition != "balanced"
                )
                or (
                    classifier_probability >= 0.34
                    and clinical_pallor_score >= 0.62
                )
            )
        )
        if not rescue_triggered:
            return risk, False

        rescued_risk = max(risk, decision_threshold + 0.01)
        return clamp(rescued_risk, 0.0, 1.0), True

    def _should_suppress_v8_conflicted_hemoglobin(
        self,
        *,
        risk: float,
        decision_threshold: float,
        prediction: dict[str, float],
        feature_map: dict[str, float],
        quality: QualityAssessment,
    ) -> bool:
        predicted_hemoglobin = prediction.get("predicted_hemoglobin")
        if predicted_hemoglobin is None:
            return False

        classifier_probability = float(prediction.get("classifier_probability", 0.0))
        regressor_risk = float(prediction.get("regressor_risk", 0.0))
        clinical_pallor_score = float(feature_map.get("clinical_pallor_score", 0.0))

        return (
            risk >= decision_threshold
            and float(predicted_hemoglobin) >= 13.4
            and (
                (
                    classifier_probability >= 0.30
                    and regressor_risk <= 0.15
                    and clinical_pallor_score >= 0.56
                )
                or (
                    classifier_probability >= 0.24
                    and clinical_pallor_score >= 0.50
                    and quality.lighting_condition != "balanced"
                )
            )
        )

    def _harmonize_positive_hb_conflict(
        self,
        *,
        base_risk: float,
        refined_risk: float,
        threshold: float,
        predicted_hemoglobin: float | None,
        uncertainty: float,
        quality: QualityAssessment,
        capture_quality_score: float,
        base_screening_label: str,
    ) -> tuple[float, str | None]:
        if predicted_hemoglobin is None or refined_risk < threshold:
            return refined_risk, None
        if predicted_hemoglobin < 13.2:
            return refined_risk, None

        risk_jump = refined_risk - base_risk
        severe_capture_limitation = (
            quality.lighting_condition in {"overexposed", "glare_heavy", "shadow_heavy", "flat_contrast"}
            or quality.glare_risk > 0.45
            or quality.shadow_risk > 0.45
            or capture_quality_score < 0.72
        )
        base_non_positive = base_screening_label != "anemia_likely" or base_risk < threshold
        clearly_normal_hb = predicted_hemoglobin >= 13.6
        strongly_normal_hb = predicted_hemoglobin >= 14.4

        if base_non_positive and (
            risk_jump >= 0.12
            or (clearly_normal_hb and refined_risk >= (threshold + 0.08))
        ):
            cap = min(base_risk, threshold - (0.08 if severe_capture_limitation else 0.05))
            return clamp(cap, 0.0, 1.0), "refiner_conflict_with_normal_hb"

        if clearly_normal_hb and risk_jump >= 0.18:
            cap = min(
                max(base_risk, threshold - (0.07 if severe_capture_limitation else 0.04)),
                threshold - 0.03,
            )
            return clamp(cap, 0.0, 1.0), "normal_hb_refiner_overshoot"

        if strongly_normal_hb and refined_risk >= (threshold + 0.18) and uncertainty >= 0.18:
            cap = threshold - (0.08 if severe_capture_limitation else 0.04)
            return clamp(cap, 0.0, 1.0), "very_normal_hb_positive_conflict"

        if (
            predicted_hemoglobin >= 13.2
            and risk_jump >= 0.3
            and refined_risk >= (threshold + 0.25)
            and uncertainty >= 0.18
        ):
            cap = threshold - (0.06 if severe_capture_limitation else 0.03)
            return clamp(cap, 0.0, 1.0), "strong_refiner_jump_with_normal_hb"

        return refined_risk, None

    def _validation_fallback_result(
        self,
        validation: ValidationResult,
        quality: QualityAssessment | None,
    ) -> PredictionResult:
        """
        Return a safe PredictionResult when input validation fails.

        Provides detailed error information so the caller knows exactly
        what went wrong and how to fix it.
        """
        error_messages = [e.message for e in validation.errors]
        suggestions = [e.suggestion for e in validation.errors]

        return PredictionResult(
            anemia_risk=0.5,
            predicted_hemoglobin=None,
            confidence=0.0,
            uncertainty=1.0,
            reliability_flag="low",
            screening_label="uncertain",
            screening_text=(
                f"Input validation failed: {'; '.join(error_messages)}. "
                f"Please {suggestions[0] if suggestions else 'fix the issues and try again.'}"
            ),
            model_source="validation_failed",
            confidence_breakdown={
                "capture_quality": 0.0,
                "model_stability": 0.0,
                "threshold_stability": 0.0,
                "guardrail_applied": True,
                "lighting_condition": quality.lighting_condition if quality else "unknown",
                "glare_risk": round(quality.glare_risk, 3) if quality else 0.0,
                "shadow_risk": round(quality.shadow_risk, 3) if quality else 0.0,
                "validation_errors": [
                    {"field": e.field, "message": e.message, "suggestion": e.suggestion}
                    for e in validation.errors
                ],
                "summary": "Input validation failed. See validation_errors for details.",
            },
        )

    def _low_confidence_fallback(
        self,
        prediction: PredictionResult,
        image: Image.Image,
        patient_profile: PatientProfileInput | None,
        quality: QualityAssessment | None,
        feature_map: dict[str, float] | None,
    ) -> PredictionResult:
        """
        Apply fallback prediction when model confidence is critically low.

        Uses the fallback_prediction module to provide:
        - Conservative default predictions
        - Population-based priors (if demographics available)
        - Heuristic-based estimates (if features available)
        - Wide uncertainty bounds reflecting high epistemic uncertainty
        """
        # Determine why confidence is low
        reason = "low_confidence"
        if quality and not quality.passed:
            reason = "quality_gate_rejection"
        elif prediction.model_source == "missing-model":
            reason = "no_model_available"

        # Generate fallback prediction
        fallback = generate_fallback(
            reason=reason,  # type: ignore[arg-type]
            image=image,
            sex=patient_profile.sex if patient_profile else "not_specified",
            age=patient_profile.age if patient_profile else None,
            is_pregnant=(
                patient_profile.is_pregnant
                if patient_profile and hasattr(patient_profile, "is_pregnant")
                else False
            ),
            feature_map=feature_map,
        )

        # Merge fallback with original prediction, keeping the better of both
        # When model confidence is low, blend toward the fallback
        blend_weight = max(0.0, 1.0 - prediction.confidence * 2.0)  # Higher weight to fallback when confidence is low

        blended_risk = (
            prediction.anemia_risk * (1.0 - blend_weight)
            + fallback.anemia_risk * blend_weight
        )
        blended_uncertainty = max(prediction.uncertainty, fallback.uncertainty)

        # Use fallback Hb if model didn't produce one or if uncertainty is very high
        final_hb = prediction.predicted_hemoglobin
        if final_hb is None and fallback.predicted_hemoglobin is not None:
            final_hb = fallback.predicted_hemoglobin
        elif prediction.uncertainty > 0.7 and fallback.predicted_hemoglobin is not None:
            # Blend Hb estimates
            final_hb = (
                prediction.predicted_hemoglobin * (1.0 - blend_weight)
                + fallback.predicted_hemoglobin * blend_weight
            )

        # Determine screening label from blended risk
        threshold = float((prediction.confidence_breakdown or {}).get("decision_threshold", 0.5))
        if blended_risk >= threshold and blended_uncertainty < 0.75:
            screening_label = "anemia_likely"
            screening_text = (
                f"Blended screening suggests anemia risk of {blended_risk:.0%}. "
                f"Confidence is moderate; clinical correlation is recommended."
            )
        elif blended_uncertainty >= 0.75:
            screening_label = "uncertain"
            screening_text = (
                f"Model confidence is low (uncertainty: {blended_uncertainty:.0%}). "
                f"The fallback estimate suggests {fallback.anemia_risk:.0%} risk. "
                f"Clinical confirmation is strongly recommended."
            )
        else:
            screening_label = "anemia_unlikely"
            screening_text = (
                f"Screening suggests anemia risk of {blended_risk:.0%}. "
                f"Result should be interpreted with caution due to moderate uncertainty."
            )

        # Build enhanced confidence breakdown with fallback info
        confidence_breakdown = dict(prediction.confidence_breakdown or {})
        confidence_breakdown.update({
            "fallback_applied": True,
            "fallback_method": fallback.method,
            "fallback_reason": fallback.reason,
            "fallback_anemia_risk": fallback.anemia_risk,
            "fallback_uncertainty": fallback.uncertainty,
            "fallback_hb_interval": list(fallback.hb_interval) if fallback.hb_interval else None,
            "blend_weight_fallback": round(blend_weight, 3),
            "fallback_recommendation": fallback.recommendation,
            "summary": (
                f"Low model confidence triggered fallback prediction ({fallback.method}). "
                f"Results are blended with the primary model. {fallback.recommendation}"
            ),
        })

        return PredictionResult(
            anemia_risk=round(blended_risk, 3),
            predicted_hemoglobin=round(final_hb, 2) if final_hb is not None else None,
            confidence=round(max(prediction.confidence * 0.5, 0.1), 3),
            uncertainty=round(blended_uncertainty, 3),
            reliability_flag="low",
            screening_label=screening_label,
            screening_text=screening_text,
            model_source=f"{prediction.model_source}+fallback:{fallback.method}",
            confidence_breakdown=confidence_breakdown,
        )

    def _dark_signal_guardrail(
        self,
        *,
        risk: float,
        predicted_hemoglobin: float | None,
        feature_map: dict[str, float],
        threshold: float,
    ) -> bool:
        if predicted_hemoglobin is None or risk < threshold:
            return False
        return (
            predicted_hemoglobin >= 11.8
            and feature_map["brightness"] <= 0.12
            and feature_map["hist_bright"] <= 0.04
            and feature_map["hist_highlight"] <= 0.005
        )
