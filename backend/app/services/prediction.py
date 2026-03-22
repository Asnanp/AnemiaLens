from __future__ import annotations

from pathlib import Path
from typing import Literal

from PIL import Image

from app.config import (
    DEFAULT_ARCHIVE_MODEL_PATH,
    DEFAULT_EFFICIENTNET_MODEL_PATH,
    DEFAULT_RUNTIME_CALIBRATOR_PATH,
    DEFAULT_RUNTIME_REFINER_PATH,
    settings,
)
from app.ml.archive_model import clamp
from app.ml.features import extract_eye_features
from app.schemas import ModelRuntimeStatus, PredictionResult, QualityAssessment


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


def _load_runtime_screening_refiner_artifact(path: Path):
    from app.ml.runtime_refinement import RuntimeScreeningRefiner

    return RuntimeScreeningRefiner.load(path)


def _predict_archive_model(
    artifact: dict[str, object],
    feature_map: dict[str, float],
    *,
    source_hint: Literal["roi_original", "palpebral", "forniceal_palpebral"],
) -> dict[str, float]:
    from app.ml.archive_model import predict_with_archive_model

    return predict_with_archive_model(artifact, feature_map, source_hint=source_hint)


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
        self.runtime_calibrator_path = Path(DEFAULT_RUNTIME_CALIBRATOR_PATH)
        self.runtime_refiner_path = Path(DEFAULT_RUNTIME_REFINER_PATH)
        self.enable_efficientnet_fallback = settings.enable_efficientnet_fallback
        self.load_error: str | None = None
        self.efficientnet_bundle: dict[str, object] | None = None
        self.archive_model: dict[str, object] | None = None
        self.runtime_risk_calibrator = None
        self.runtime_screening_refiner = None
        self._archive_model_load_attempted = False
        self._efficientnet_model_load_attempted = False
        self._runtime_risk_calibrator_load_attempted = False
        self._runtime_screening_refiner_load_attempted = False

    def preload(self) -> None:
        self._ensure_archive_model_loaded()
        self._ensure_runtime_risk_calibrator_loaded()
        self._ensure_runtime_screening_refiner_loaded()
        if self.enable_efficientnet_fallback:
            self._ensure_efficientnet_model_loaded()

    def predict(self, image: Image.Image, quality: QualityAssessment) -> PredictionResult:
        prediction: dict[str, float] | None = None
        model_source = "missing-model"
        decision_threshold = 0.5
        feature_map = extract_eye_features(image)
        source_hint: Literal["roi_original", "palpebral", "forniceal_palpebral"] = "roi_original"

        archive_model = self._ensure_archive_model_loaded()
        if archive_model is not None:
            try:
                efficientnet_secondary: dict[str, float] | None = None
                if self.enable_efficientnet_fallback:
                    efficientnet_bundle = self._ensure_efficientnet_model_loaded()
                    if efficientnet_bundle is not None:
                        try:
                            efficientnet_secondary = _predict_efficientnet_bundle(
                                efficientnet_bundle,
                                image,
                                mc_passes=4,
                            )
                        except Exception:
                            efficientnet_secondary = None

                archive_prediction = _predict_archive_model(
                    archive_model,
                    feature_map,
                    source_hint=source_hint,
                )
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
                        mc_passes=4,
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
        predicted_hemoglobin_raw = float(prediction["predicted_hemoglobin"])
        predicted_hemoglobin = round(predicted_hemoglobin_raw, 2)
        calibrated_risk = float(prediction.get("calibrated_anemia_risk", risk))
        capture_quality_score = self._capture_quality_score(quality)
        model_stability = clamp(1.0 - raw_uncertainty, 0.0, 1.0)
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
            feature_map=feature_map,
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
        runtime_screening_refiner = self._ensure_runtime_screening_refiner_loaded()
        refined_risk = risk
        if runtime_screening_refiner is not None:
            refined_risk = runtime_screening_refiner.refine(
                base_anemia_risk=risk,
                uncertainty=uncertainty,
                predicted_hemoglobin=predicted_hemoglobin,
                quality=quality,
                base_likely=(base_screening_label == "anemia_likely"),
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
            "refinement_applied": runtime_screening_refiner is not None,
            "refinement_method": (
                getattr(runtime_screening_refiner, "method", "none")
                if runtime_screening_refiner is not None
                else "none"
            ),
            "raw_anemia_risk": round(
                float(prediction.get("raw_anemia_risk", risk)),
                3,
            ),
            "calibrated_anemia_risk": round(
                float(prediction.get("calibrated_anemia_risk", risk)),
                3,
            ),
            "refined_anemia_risk": round(refined_risk, 3),
            "decision_threshold": round(decision_threshold, 3),
            "base_screening_label": base_screening_label,
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

        return PredictionResult(
            anemia_risk=round(refined_risk, 3),
            predicted_hemoglobin=predicted_hemoglobin,
            confidence=round(confidence, 3),
            uncertainty=round(uncertainty, 3),
            reliability_flag=reliability_flag,
            screening_label=screening_label,
            screening_text=screening_text,
            model_source=model_source,
            confidence_breakdown=confidence_breakdown,
        )

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
            primary_model = _runtime_stack_version()
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

        runtime_calibration_ready = self.runtime_risk_calibrator is not None or (
            getattr(self, "runtime_calibrator_path", Path(DEFAULT_RUNTIME_CALIBRATOR_PATH)).exists()
        )
        runtime_refiner_ready = self.runtime_screening_refiner is not None or (
            getattr(self, "runtime_refiner_path", Path(DEFAULT_RUNTIME_REFINER_PATH)).exists()
        )

        return ModelRuntimeStatus(
            primary_model=primary_model,
            deep_stack_loaded=False,
            legacy_loaded=False,
            artifact_ready=archive_ready or efficientnet_ready,
            artifact_path=artifact_path,
            load_error=self.load_error,
            runtime_calibration_ready=runtime_calibration_ready,
            runtime_refiner_ready=runtime_refiner_ready,
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
        return (
            prediction.screening_label == "anemia_likely"
            and (
                strong_hb_positive
                or strong_signal_only_positive
                or overwhelming_signal_only_positive
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
        if uncertainty >= 0.70:
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
