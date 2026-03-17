from __future__ import annotations

from pathlib import Path
from typing import Literal

from PIL import Image

from app.config import DEFAULT_ARCHIVE_MODEL_PATH, DEFAULT_EFFICIENTNET_MODEL_PATH
from app.ml.archive_model import (
    clamp,
    load_archive_model,
    predict_with_archive_model,
)
from app.ml.efficientnet_model import (
    EFFICIENTNET_VERSION,
    load_efficientnet_checkpoint,
    predict_with_efficientnet_model,
)
from app.ml.features import extract_eye_features
from app.ml.runtime_stack import (
    RUNTIME_STACK_VERSION,
    build_runtime_stack_prediction,
    decision_threshold_for_source,
)
from app.schemas import ModelRuntimeStatus, PredictionResult, QualityAssessment


class ScreeningPredictor:
    def __init__(self, model_path: str | Path | None = None) -> None:
        self.efficientnet_path = Path(DEFAULT_EFFICIENTNET_MODEL_PATH)
        self.model_path = Path(model_path or DEFAULT_ARCHIVE_MODEL_PATH)
        self.load_error: str | None = None
        self.efficientnet_bundle = self._load_efficientnet_model()
        self.archive_model = self._load_archive_model()

    def predict(self, image: Image.Image, quality: QualityAssessment) -> PredictionResult:
        prediction: dict[str, float] | None = None
        model_source = "missing-model"
        decision_threshold = 0.5
        feature_map = extract_eye_features(image)
        source_hint: Literal["roi_original", "palpebral", "forniceal_palpebral"] = "roi_original"

        if self.archive_model is not None:
            try:
                efficientnet_secondary: dict[str, float] | None = None
                if self.efficientnet_bundle is not None:
                    try:
                        efficientnet_secondary = predict_with_efficientnet_model(
                            self.efficientnet_bundle,
                            image,
                            mc_passes=4,  # reduced from 12 to lower peak RAM on Render
                        )
                    except Exception:
                        efficientnet_secondary = None

                archive_prediction = predict_with_archive_model(
                    self.archive_model,
                    feature_map,
                    source_hint=source_hint,
                )
                prediction = build_runtime_stack_prediction(
                    archive_prediction,
                    efficientnet_prediction=efficientnet_secondary,
                    source_hint=source_hint,
                )
                model_source = RUNTIME_STACK_VERSION
                decision_threshold = float(prediction.get("decision_threshold", decision_threshold_for_source(source_hint)))
            except Exception as exc:
                self.load_error = f"Archive inference failed: {type(exc).__name__}: {exc}"

        if prediction is None and self.efficientnet_bundle is not None:
            try:
                prediction = predict_with_efficientnet_model(
                    self.efficientnet_bundle,
                    image,
                    mc_passes=4,  # reduced from 16 to lower peak RAM on Render
                )
                model_source = str(self.efficientnet_bundle.get("version", EFFICIENTNET_VERSION))
                decision_threshold = float(prediction.get("decision_threshold", 0.5))
            except Exception as exc:
                self.load_error = f"EfficientNet inference failed: {type(exc).__name__}: {exc}"

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
            )
        risk = float(prediction["anemia_risk"])
        uncertainty = float(prediction["uncertainty"])
        predicted_hemoglobin_raw = float(prediction["predicted_hemoglobin"])
        predicted_hemoglobin = round(predicted_hemoglobin_raw, 2)
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
            if uncertainty < 0.2 and quality.passed
            else "medium"
            if uncertainty < 0.35 and quality.passed
            else "low"
        )
        predicted_hemoglobin = self._display_hemoglobin(predicted_hemoglobin, uncertainty)
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
        )

    def _load_efficientnet_model(self) -> dict[str, object] | None:
        if not self.efficientnet_path.exists():
            return None
        try:
            return load_efficientnet_checkpoint(self.efficientnet_path)
        except Exception as exc:
            self.load_error = f"EfficientNet load failed: {type(exc).__name__}: {exc}"
            return None

    def _load_archive_model(self) -> dict[str, object] | None:
        if not self.model_path.exists():
            if self.efficientnet_bundle is None:
                self.load_error = f"Model artifact not found at {self.model_path}"
            return None
        try:
            if self.efficientnet_bundle is None:
                self.load_error = None
            return load_archive_model(self.model_path)
        except Exception as exc:
            if self.efficientnet_bundle is None:
                self.load_error = f"{type(exc).__name__}: {exc}"
            return None

    def is_ready(self) -> bool:
        return self.efficientnet_bundle is not None or self.archive_model is not None

    def runtime_status(self) -> ModelRuntimeStatus:
        return ModelRuntimeStatus(
            primary_model=(
                RUNTIME_STACK_VERSION
                if self.archive_model is not None
                else str(self.efficientnet_bundle.get("version", EFFICIENTNET_VERSION))
                if self.efficientnet_bundle is not None
                else "missing-model"
            ),
            deep_stack_loaded=False,
            legacy_loaded=False,
            artifact_ready=self.is_ready(),
            artifact_path=(
                str(self.model_path)
                if self.archive_model is not None
                else str(self.efficientnet_path)
            ),
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
            and (prediction.predicted_hemoglobin is None or prediction.predicted_hemoglobin >= 12.8)
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
            and threshold <= risk < (threshold + 0.12)
            and predicted_hemoglobin > 13.0
            and uncertainty >= 0.65
        )
        if mild_positive_conflict:
            return (
                "uncertain",
                "The screening signal is only mildly positive while the hemoglobin estimate stays near normal, so the safest interpretation is uncertain.",
            )
        high_suspicion_positive = (
            predicted_hemoglobin is not None
            and (
                (
                    risk >= threshold
                    and predicted_hemoglobin <= 12.2
                    and uncertainty < 0.62
                )
                or (
                    (threshold - 0.02) <= risk < threshold
                    and predicted_hemoglobin <= 12.4
                    and uncertainty < 0.57
                )
                or (
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
                "The screening model estimates a lower-than-expected hemoglobin trend from the eye image.",
            )
        return (
            "anemia_unlikely",
            "The screening model does not estimate a strong low-hemoglobin trend from the eye image.",
        )

    def _display_hemoglobin(self, predicted_hemoglobin: float | None, uncertainty: float) -> float | None:
        if predicted_hemoglobin is None:
            return None
        if uncertainty >= 0.70:
            return None
        return round(clamp(predicted_hemoglobin, 6.0, 18.0), 2)

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
