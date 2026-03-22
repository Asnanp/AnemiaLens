from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from app.config import DEFAULT_RUNTIME_REFINEMENT_REPORT_PATH, DEFAULT_RUNTIME_REFINER_PATH
from app.ml.runtime_refinement import RuntimeScreeningRefiner
from app.services.image_quality import ImageQualityService
from app.services.prediction import ScreeningPredictor
from train_efficientnet import (
    ARCHIVE_ROOT,
    _balanced_group_split,
    _build_records,
    _load_image_with_fallback,
)


def _metric_block(labels: np.ndarray, predictions: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": round(float(accuracy_score(labels, predictions)), 4),
        "precision": round(float(precision_score(labels, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(labels, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(labels, predictions, zero_division=0)), 4),
    }


def _build_dataset(records) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    quality_service = ImageQualityService()
    predictor = ScreeningPredictor()
    predictor.runtime_screening_refiner = None
    predictor._runtime_screening_refiner_load_attempted = True

    feature_rows: list[list[float]] = []
    labels: list[int] = []
    base_predictions: list[int] = []

    for record in records:
        with record.image_path.open("rb") as handle:
            quality, processed = quality_service.evaluate(handle.read())
        prediction = predictor.predict(processed, quality) if quality.passed else None
        if prediction is None and quality_service.allows_raw_frame_rescue(quality):
            raw_image = _load_image_with_fallback(record.image_path).convert("RGB")
            raw_prediction = predictor.predict(raw_image, quality)
            if predictor.should_accept_raw_frame_rescue(raw_prediction):
                quality = quality_service.build_raw_frame_rescue_assessment(quality)
                prediction = raw_prediction

        if prediction is None:
            base_risk = 0.0
            uncertainty = 1.0
            predicted_hemoglobin = None
            base_likely = False
            base_prediction = 0
        else:
            base_risk = float(
                prediction.confidence_breakdown.get("raw_anemia_risk", prediction.anemia_risk)
            )
            uncertainty = float(prediction.uncertainty)
            predicted_hemoglobin = prediction.predicted_hemoglobin
            base_likely = str(
                prediction.confidence_breakdown.get("base_screening_label", prediction.screening_label)
            ) == "anemia_likely"
            base_prediction = int(prediction.screening_label == "anemia_likely")

        feature_rows.append(
            RuntimeScreeningRefiner()._feature_vector(
                base_anemia_risk=base_risk,
                uncertainty=uncertainty,
                predicted_hemoglobin=predicted_hemoglobin,
                quality=quality,
                base_likely=base_likely,
            )
        )
        labels.append(int(record.label))
        base_predictions.append(base_prediction)

    return (
        np.asarray(feature_rows, dtype=np.float32),
        np.asarray(labels, dtype=np.int32),
        np.asarray(base_predictions, dtype=np.int32),
    )


def _evaluate_deployed_records(records, *, use_refiner: bool) -> dict[str, float]:
    quality_service = ImageQualityService()
    predictor = ScreeningPredictor()
    if not use_refiner:
        predictor.runtime_screening_refiner = None
        predictor._runtime_screening_refiner_load_attempted = True
    labels: list[int] = []
    predictions: list[int] = []

    for record in records:
        with record.image_path.open("rb") as handle:
            quality, processed = quality_service.evaluate(handle.read())
        prediction = predictor.predict(processed, quality) if quality.passed else None
        if prediction is None and quality_service.allows_raw_frame_rescue(quality):
            raw_image = _load_image_with_fallback(record.image_path).convert("RGB")
            raw_prediction = predictor.predict(raw_image, quality)
            if predictor.should_accept_raw_frame_rescue(raw_prediction):
                quality = quality_service.build_raw_frame_rescue_assessment(quality)
                prediction = raw_prediction

        labels.append(int(record.label))
        predictions.append(int(prediction is not None and prediction.screening_label == "anemia_likely"))

    return _metric_block(
        np.asarray(labels, dtype=np.int32),
        np.asarray(predictions, dtype=np.int32),
    )


def _choose_threshold(labels: np.ndarray, probabilities: np.ndarray) -> tuple[float, dict[str, float]]:
    best_threshold = 0.5
    best_metrics: dict[str, float] | None = None
    for threshold in np.linspace(0.3, 0.7, 41):
        predictions = (probabilities >= threshold).astype(np.int32)
        metrics = _metric_block(labels, predictions)
        if best_metrics is None or metrics["f1"] > best_metrics["f1"] or (
            metrics["f1"] == best_metrics["f1"] and metrics["precision"] > best_metrics["precision"]
        ):
            best_threshold = float(threshold)
            best_metrics = metrics
    assert best_metrics is not None
    return best_threshold, best_metrics


def main() -> None:
    records = _build_records(ARCHIVE_ROOT)
    if not records:
        raise RuntimeError(f"No evaluation records found in {ARCHIVE_ROOT}.")

    train_records, val_records = _balanced_group_split(records, test_size=0.2, n_splits=32)
    train_roi = [record for record in train_records if record.source == "roi_original"]
    val_roi = [record for record in val_records if record.source == "roi_original"]

    X_train, y_train, _ = _build_dataset(train_roi)
    X_val, y_val, base_predictions = _build_dataset(val_roi)

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "logreg",
                LogisticRegression(
                    C=0.3,
                    max_iter=4000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )
    model.fit(X_train, y_train)
    probabilities = model.predict_proba(X_val)[:, 1]
    selected_threshold, stage_metrics_after = _choose_threshold(y_val, probabilities)
    metrics_before = _evaluate_deployed_records(val_roi, use_refiner=False)

    refiner = RuntimeScreeningRefiner(
        model=model,
        threshold=round(selected_threshold, 4),
        report={
            "validation_size": int(len(y_val)),
            "metrics_before": metrics_before,
            "selected_threshold": round(selected_threshold, 4),
        },
    )
    refiner.save(DEFAULT_RUNTIME_REFINER_PATH)
    metrics_after = _evaluate_deployed_records(val_roi, use_refiner=True)

    report = {
        "version": refiner.version,
        "method": refiner.method,
        "validation_size": int(len(y_val)),
        "selected_threshold": round(selected_threshold, 4),
        "metrics_before": metrics_before,
        "metrics_after": metrics_after,
        "stage_metrics_after": stage_metrics_after,
    }
    DEFAULT_RUNTIME_REFINEMENT_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\nRuntime screening refinement metrics")
    print(f"validation_size: {report['validation_size']}")
    print(f"selected_threshold: {report['selected_threshold']:.4f}")
    print("before:", report["metrics_before"])
    print("after:", report["metrics_after"])


if __name__ == "__main__":
    main()
