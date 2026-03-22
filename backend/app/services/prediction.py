from __future__ import annotations

from pathlib import Path
from typing import Literal

from PIL import Image

from app.config import DEFAULT_ARCHIVE_MODEL_PATH, DEFAULT_EFFICIENTNET_MODEL_PATH, settings
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
        self.enable_efficientnet_fallback = settings.enable_efficientnet_fallback
        self.load_error: str | None = None
        self.efficientnet_bundle: dict[str, object] | None = None
        self.archive_model: dict[str, object] | None = None
        self._archive_model_load_attempted = False
        self._efficientnet_model_load_attempted = False

    def preload(self) -> None:
        self._ensure_archive_model_loaded()
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
        capture_quality_score = self._capture_quality_score(quality)
        model_stability = clamp(1.0 - raw_uncertainty, 0.0, 1.0)
        threshold_stability = clamp(abs(risk - decision_threshold) / 0.18, 0.0, 1.0)
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

        uncertainty = clamp(uncertainty + quality_delta, 0.05, 0.88)
        guardrail_triggered = self._dark_signal_guardrail(
            risk=risk,
            predicted_hemoglobin=predicted_hemoglobin,
            feature_map=feature_map,
            threshold=decision_threshold,
        )
        if guardrail_triggered:
            uncertainty = max(uncertainty, 0.35)

        confidence = clamp(1.0 - uncertainty)
        reliability_flag = (
            "high"
            if uncertainty < 0.2
            and quality.passed
            and capture_quality_score >= 0.7
            and threshold_stability >= 0.25
            else "medium"
            if uncertainty < 0.35
            and quality.passed
            and capture_quality_score >= 0.5
            else "low"
        )
        confidence_breakdown = {
            "capture_quality": round(capture_quality_score, 3),
            "model_stability": round(model_stability, 3),
            "threshold_stability": round(threshold_stability, 3),
            "guardrail_applied": guardrail_triggered,
            "lighting_condition": quality.lighting_condition,
            "glare_risk": round(quality.glare_risk, 3),
            "shadow_risk": round(quality.shadow_risk, 3),
            "summary": self._confidence_summary(
                quality=quality,
                capture_quality_score=capture_quality_score,
                model_stability=model_stability,
                threshold_stability=threshold_stability,
                guardrail_triggered=guardrail_triggered,
            ),
        }
        predicted_hemoglobin = self._display_hemoglobin(
            predicted_hemoglobin, uncertainty
        )
        screening_label, screening_text = self._screening_decision(
            risk,
            uncertainty,
            decision_threshold,
            predicted_hemoglobin=predicted_hemoglobin_raw,
            signal_guardrail_triggered=guardrail_triggered,
        )

        return PredictionResult(
            anemia_risk=round(risk, 3),
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

        return ModelRuntimeStatus(
            primary_model=primary_model,
            deep_stack_loaded=False,
            legacy_loaded=False,
            artifact_ready=archive_ready or efficientnet_ready,
            artifact_path=artifact_path,
            load_error=self.load_error,
        )

    def should_accept_raw_frame_rescue(self, prediction: PredictionResult) -> bool:
        return (
            self._accept_raw_frame_positive_rescue(prediction)
            or self._accept_raw_frame_negative_rescue(prediction)
            or self._accept_raw_frame_uncertain_rescue(prediction)
        )

    def _accept_raw_frame_positive_rescue(self, prediction: PredictionResult) -> bool:
        return (
            prediction.screening_label == "anemia_likely"
            and prediction.predicted_hemoglobin is not None
            and prediction.anemia_risk >= 0.8
            and prediction.predicted_hemoglobin <= 11.2
            and prediction.uncertainty <= 0.5
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

    def _confidence_summary(
        self,
        *,
        quality: QualityAssessment,
        capture_quality_score: float,
        model_stability: float,
        threshold_stability: float,
        guardrail_triggered: bool,
    ) -> str:
        if guardrail_triggered:
            return (
                "A protective guardrail lowered confidence because the image looked dark for a strong low-hemoglobin claim."
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
                "The model spread stayed wider than ideal, so the result is usable but not as stable as a clearer high-confidence case."
            )
        return (
            "Capture quality, model stability, and threshold margin all support a more defensible screening explanation."
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
