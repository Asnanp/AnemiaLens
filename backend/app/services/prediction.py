from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image

from app.config import DEFAULT_ARCHIVE_MODEL_PATH, DEFAULT_EFFICIENTNET_MODEL_PATH
from app.ml.calibration import CompositeCalibrator
from app.ml.features import extract_eye_features
from app.ml.roi_confidence import RoiConfidenceScorer
from app.schemas import ModelRuntimeStatus, PredictionResult, QualityAssessment

_CALIBRATOR_PATH = Path(__file__).parent.parent / "artifacts" / "calibrator.pkl"


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _runtime_stack_version() -> str:
    from app.ml.runtime_stack import RUNTIME_STACK_VERSION

    return RUNTIME_STACK_VERSION


def _efficientnet_version() -> str:
    from app.ml.efficientnet_model import EFFICIENTNET_VERSION

    return EFFICIENTNET_VERSION


def _decision_threshold_for_source(
    source_hint: Literal["roi_original", "palpebral", "forniceal_palpebral"] = "roi_original",
) -> float:
    from app.ml.runtime_stack import decision_threshold_for_source

    return float(decision_threshold_for_source(source_hint))


def _load_archive_model_artifact(path: str | Path) -> dict[str, object]:
    from app.ml.archive_model import load_archive_model

    return load_archive_model(path)


def _predict_archive_model(
    artifact: dict[str, object],
    feature_map: dict[str, float],
    *,
    source_hint: Literal["roi_original", "palpebral", "forniceal_palpebral"] = "roi_original",
) -> dict[str, float]:
    from app.ml.archive_model import predict_with_archive_model

    return predict_with_archive_model(artifact, feature_map, source_hint=source_hint)


def _load_efficientnet_checkpoint_bundle(path: str | Path) -> dict[str, object]:
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


def _build_runtime_stack(
    archive_prediction: dict[str, float],
    *,
    efficientnet_prediction: dict[str, float] | None = None,
    source_hint: Literal["roi_original", "palpebral", "forniceal_palpebral"] = "roi_original",
) -> dict[str, float]:
    from app.ml.runtime_stack import build_runtime_stack_prediction

    return build_runtime_stack_prediction(
        archive_prediction,
        efficientnet_prediction=efficientnet_prediction,
        source_hint=source_hint,
    )


class ScreeningPredictor:
    def __init__(self, model_path: str | Path | None = None) -> None:
        self.efficientnet_path = Path(DEFAULT_EFFICIENTNET_MODEL_PATH)
        self.model_path = Path(model_path or DEFAULT_ARCHIVE_MODEL_PATH)
        self.load_error: str | None = None
        self.efficientnet_bundle: dict[str, object] | None = None
        self.archive_model: dict[str, object] | None = None
        self._archive_model_load_attempted = False
        self._efficientnet_model_load_attempted = False
        self._calibrator = self._load_calibrator()
        self._roi_scorer = RoiConfidenceScorer()

    def preload(self) -> None:
        self._ensure_archive_model_loaded()
        if self.archive_model is None:
            self._ensure_efficientnet_model_loaded()

    def predict(self, image: Image.Image, quality: QualityAssessment, symptom_score: float = 0.0) -> PredictionResult:
        prediction: dict[str, float] | None = None
        model_source = "missing-model"
        decision_threshold = 0.5
        feature_map = extract_eye_features(image)
        source_hint: Literal["roi_original", "palpebral", "forniceal_palpebral"] = "roi_original"

        self._ensure_archive_model_loaded()
        if self.archive_model is not None:
            try:
                # EfficientNet was trained for only 1 epoch (AUC ~0.56 = near-random).
                # Blending it with the archive model degrades predictions.
                # Skip it until a properly trained checkpoint is available.
                efficientnet_secondary: dict[str, float] | None = None

                archive_prediction = _predict_archive_model(
                    self.archive_model,
                    feature_map,
                    source_hint=source_hint,
                )
                prediction = _build_runtime_stack(
                    archive_prediction,
                    efficientnet_prediction=efficientnet_secondary,
                    source_hint=source_hint,
                )
                model_source = _runtime_stack_version()
                decision_threshold = float(prediction.get("decision_threshold", _decision_threshold_for_source(source_hint)))
            except Exception as exc:
                self.load_error = f"Archive inference failed: {type(exc).__name__}: {exc}"

        if prediction is None:
            self._ensure_efficientnet_model_loaded()
        if prediction is None and self.efficientnet_bundle is not None:
            try:
                prediction = _predict_efficientnet_bundle(
                    self.efficientnet_bundle,
                    image,
                    mc_passes=4,  # reduced from 16 to lower peak RAM on constrained hosts
                )
                model_source = str(self.efficientnet_bundle.get("version", _efficientnet_version()))
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
        # Apply probability calibration if available
        risk = self._calibrator.calibrate(risk)
        uncertainty = float(prediction["uncertainty"])
        predicted_hemoglobin_raw = float(prediction["predicted_hemoglobin"])
        predicted_hemoglobin = round(predicted_hemoglobin_raw, 2)

        # --- Symptom-driven post-processing --------------------------------
        # When symptoms are present, they provide real clinical signal.
        # Blend symptom evidence into risk and Hb even for real model outputs.
        if symptom_score > 0.0:
            # Symptoms push risk up: all symptoms (score=1.0) adds up to +0.30
            symptom_risk_boost = symptom_score * 0.30
            risk = float(np.clip(risk + symptom_risk_boost * (1.0 - risk), 0.0, 1.0))
            # Symptoms lower Hb estimate: all symptoms → up to -2.5 g/dL
            symptom_hb_penalty = symptom_score * 2.5
            predicted_hemoglobin_raw = float(np.clip(predicted_hemoglobin_raw - symptom_hb_penalty, 6.0, 18.0))
            predicted_hemoglobin = round(predicted_hemoglobin_raw, 2)
            # Symptoms reduce uncertainty slightly (more signal available)
            uncertainty = float(np.clip(uncertainty - symptom_score * 0.08, 0.05, 0.88))
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
            if uncertainty < 0.35 and quality.passed
            else "medium"
            if uncertainty < 0.55 and quality.passed
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

    def _load_calibrator(self) -> CompositeCalibrator:
        try:
            if _CALIBRATOR_PATH.exists():
                return CompositeCalibrator.load(_CALIBRATOR_PATH)
        except Exception:
            pass
        return CompositeCalibrator(method="none")  # identity — no-op until trained

    def _ensure_archive_model_loaded(self) -> None:
        if self._archive_model_load_attempted:
            return
        self._archive_model_load_attempted = True
        self.archive_model = self._load_archive_model()

    def _ensure_efficientnet_model_loaded(self) -> None:
        if self._efficientnet_model_load_attempted:
            return
        self._efficientnet_model_load_attempted = True
        self.efficientnet_bundle = self._load_efficientnet_model()

    def _load_efficientnet_model(self) -> dict[str, object] | None:
        if not self.efficientnet_path.exists():
            return None
        try:
            return _load_efficientnet_checkpoint_bundle(self.efficientnet_path)
        except Exception as exc:
            self.load_error = f"EfficientNet load failed: {type(exc).__name__}: {exc}"
            return None

    def _load_archive_model(self) -> dict[str, object] | None:
        if not self.model_path.exists():
            if self.efficientnet_bundle is None:
                self.load_error = f"Model artifact not found at {self.model_path}"
            return None
        try:
            self.load_error = None
            return _load_archive_model_artifact(self.model_path)
        except Exception as exc:
            if self.efficientnet_bundle is None:
                self.load_error = f"{type(exc).__name__}: {exc}"
            return None

    def is_ready(self) -> bool:
        return (
            self.archive_model is not None
            or self.efficientnet_bundle is not None
            or self.model_path.exists()
            or self.efficientnet_path.exists()
        )

    def is_loaded(self) -> bool:
        return self.archive_model is not None or self.efficientnet_bundle is not None

    def runtime_status(self) -> ModelRuntimeStatus:
        archive_available = self.model_path.exists()
        efficientnet_available = self.efficientnet_path.exists()
        return ModelRuntimeStatus(
            primary_model=(
                _runtime_stack_version()
                if archive_available or self.archive_model is not None
                else str(self.efficientnet_bundle.get("version", _efficientnet_version()))
                if efficientnet_available or self.efficientnet_bundle is not None
                else "missing-model"
            ),
            deep_stack_loaded=False,
            legacy_loaded=False,
            artifact_ready=self.is_ready(),
            artifact_path=(
                str(self.model_path)
                if archive_available or self.archive_model is not None
                else str(self.efficientnet_path)
                if efficientnet_available or self.efficientnet_bundle is not None
                else None
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
            and (
                (
                    threshold <= risk < (threshold + 0.12)
                    and predicted_hemoglobin > 13.0
                    and uncertainty >= 0.65
                )
                or (
                    threshold < 0.6
                    and threshold <= risk < (threshold + 0.13)
                    and predicted_hemoglobin >= 12.3
                    and uncertainty >= 0.52
                )
            )
        )
        if mild_positive_conflict:
            return (
                "uncertain",
                "The screening signal is only mildly positive while the hemoglobin estimate stays near normal, so the safest interpretation is uncertain.",
            )
        strict_runtime_threshold = threshold >= 0.6
        allow_below_threshold_rescue = not strict_runtime_threshold
        high_suspicion_positive = (
            predicted_hemoglobin is not None
            and (
                (
                    risk >= threshold
                    and predicted_hemoglobin <= 12.2
                    and uncertainty < 0.62
                )
                or (
                    allow_below_threshold_rescue
                    and (threshold - 0.02) <= risk < threshold
                    and predicted_hemoglobin <= 12.4
                    and uncertainty < 0.57
                )
                or (
                    allow_below_threshold_rescue
                    and (threshold - 0.05) <= risk < threshold
                    and predicted_hemoglobin <= 12.25
                    and uncertainty < 0.63
                )
            )
        )
        low_reliability_positive_requires_extra_evidence = (
            strict_runtime_threshold
            and predicted_hemoglobin is not None
            and risk >= threshold
            and uncertainty >= 0.55
            and risk < (threshold + 0.11)
            and predicted_hemoglobin > 11.4
        )
        if low_reliability_positive_requires_extra_evidence:
            return (
                "uncertain",
                "The scan trends positive, but at this confidence level the model only upgrades to likely anemia when the risk margin is stronger or the hemoglobin estimate is more clearly low.",
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
        # Show Hb unless uncertainty is very high (was 0.70, loosened to 0.80
        # since the new model has higher base uncertainty on sparse feature vectors)
        if uncertainty >= 0.80:
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
