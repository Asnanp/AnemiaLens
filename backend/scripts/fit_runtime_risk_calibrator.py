from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
)

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.config import (
    DEFAULT_ARCHIVE_MODEL_PATH,
    DEFAULT_EFFICIENTNET_MODEL_PATH,
    DEFAULT_RUNTIME_CALIBRATION_REPORT_PATH,
    DEFAULT_RUNTIME_CALIBRATOR_PATH,
)
from app.ml.archive_model import load_archive_model, predict_with_archive_model
from app.ml.calibration import CompositeCalibrator, expected_calibration_error
from app.ml.efficientnet_model import load_efficientnet_checkpoint
from app.ml.features import extract_eye_features
from app.ml.runtime_calibration import RuntimeRiskCalibrator
from app.ml.runtime_stack import (
    DEFAULT_SOURCE_THRESHOLDS,
    build_runtime_stack_prediction,
    decision_threshold_for_source,
)
from app.services.conjunctiva_roi import ConjunctivaRoiExtractor
from train_efficientnet import ARCHIVE_ROOT, _balanced_group_split, _build_records, _load_image_with_fallback


def main() -> None:
    records = _build_records(ARCHIVE_ROOT)
    if not records:
        raise RuntimeError(f"No calibration records found in {ARCHIVE_ROOT}.")

    _, val_records = _balanced_group_split(records, test_size=0.2, n_splits=32)
    archive_model = load_archive_model(DEFAULT_ARCHIVE_MODEL_PATH)
    efficientnet_bundle = None
    if Path(DEFAULT_EFFICIENTNET_MODEL_PATH).exists():
        try:
            efficientnet_bundle = load_efficientnet_checkpoint(DEFAULT_EFFICIENTNET_MODEL_PATH)
        except Exception:
            efficientnet_bundle = None
    roi_extractor = ConjunctivaRoiExtractor()

    prepared_records = []
    prepared_images: list[object] = []
    prepared_sources: list[str] = []
    prepared_archive_predictions: list[dict[str, float]] = []

    for record in val_records:
        image = _load_image_with_fallback(record.image_path)
        source_hint = record.source
        if record.source == "roi_original":
            image = roi_extractor.extract(image).image
        image = image.convert("RGB")
        archive_prediction = predict_with_archive_model(
            archive_model,
            extract_eye_features(image),
            source_hint=source_hint,
        )
        prepared_records.append(record)
        prepared_images.append(image)
        prepared_sources.append(source_hint)
        prepared_archive_predictions.append(archive_prediction)

    efficientnet_predictions = _predict_efficientnet_batch(efficientnet_bundle, prepared_images)

    roi_labels: list[int] = []
    roi_probabilities: list[float] = []

    for record, source_hint, archive_prediction, efficientnet_prediction in zip(
        prepared_records,
        prepared_sources,
        prepared_archive_predictions,
        efficientnet_predictions,
        strict=True,
    ):
        runtime_prediction = build_runtime_stack_prediction(
            archive_prediction,
            efficientnet_prediction=efficientnet_prediction,
            source_hint=source_hint,  # type: ignore[arg-type]
        )
        if record.source != "roi_original":
            continue
        roi_labels.append(int(record.label))
        roi_probabilities.append(float(runtime_prediction["anemia_risk"]))

    if len(roi_labels) < 12 or len(set(roi_labels)) < 2:
        raise RuntimeError("Not enough ROI validation data to fit a runtime calibrator.")

    labels = np.asarray(roi_labels, dtype=np.int32)
    probabilities = np.asarray(roi_probabilities, dtype=np.float32)

    calibrator = CompositeCalibrator(method="temperature").fit(probabilities, labels)
    calibrated = calibrator.calibrate_array(probabilities)

    ece_before = expected_calibration_error(probabilities, labels)["ece"]
    ece_after = expected_calibration_error(calibrated, labels)["ece"]
    brier_before = float(brier_score_loss(labels, probabilities))
    brier_after = float(brier_score_loss(labels, calibrated))

    default_threshold = decision_threshold_for_source("roi_original")
    selected_threshold = _choose_threshold(labels, calibrated, default_threshold=default_threshold)

    default_predictions = (probabilities >= default_threshold).astype(np.int32)
    calibrated_predictions = (calibrated >= selected_threshold).astype(np.int32)

    artifact = RuntimeRiskCalibrator(
        method="temperature",
        calibrator=calibrator,
        source_thresholds={
            **DEFAULT_SOURCE_THRESHOLDS,
            "roi_original": round(selected_threshold, 4),
        },
        report={
            "default_threshold": round(default_threshold, 4),
            "selected_threshold": round(selected_threshold, 4),
            "ece_before": round(float(ece_before), 4),
            "ece_after": round(float(ece_after), 4),
            "brier_before": round(brier_before, 4),
            "brier_after": round(brier_after, 4),
        },
    )
    artifact.save(DEFAULT_RUNTIME_CALIBRATOR_PATH)

    report = {
        "version": artifact.version,
        "method": artifact.method,
        "validation_size": int(len(labels)),
        "selected_thresholds": artifact.source_thresholds,
        "diagnostics": {
            "ece_before": round(float(ece_before), 4),
            "ece_after": round(float(ece_after), 4),
            "brier_before": round(brier_before, 4),
            "brier_after": round(brier_after, 4),
        },
        "roi_metrics_before": _metric_block(labels, default_predictions),
        "roi_metrics_after": _metric_block(labels, calibrated_predictions),
    }
    DEFAULT_RUNTIME_CALIBRATION_REPORT_PATH.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("Runtime risk calibration")
    print(f"validation_size: {report['validation_size']}")
    print(f"ece_before: {report['diagnostics']['ece_before']:.4f}")
    print(f"ece_after: {report['diagnostics']['ece_after']:.4f}")
    print(f"brier_before: {report['diagnostics']['brier_before']:.4f}")
    print(f"brier_after: {report['diagnostics']['brier_after']:.4f}")
    print(f"roi_threshold: {selected_threshold:.4f}")
    print(f"artifact: {DEFAULT_RUNTIME_CALIBRATOR_PATH}")


def _choose_threshold(
    labels: np.ndarray,
    probabilities: np.ndarray,
    *,
    default_threshold: float,
) -> float:
    best_threshold = default_threshold
    best_score = -1.0
    for threshold in np.linspace(0.3, 0.75, 91):
        predictions = (probabilities >= threshold).astype(np.int32)
        precision = float(precision_score(labels, predictions, zero_division=0))
        recall = float(recall_score(labels, predictions, zero_division=0))
        f1 = float(f1_score(labels, predictions, zero_division=0))
        score = (f1 * 0.55) + (recall * 0.25) + (precision * 0.20)
        if score > best_score:
            best_score = score
            best_threshold = float(threshold)
    return best_threshold


def _metric_block(labels: np.ndarray, predictions: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": round(float(accuracy_score(labels, predictions)), 4),
        "precision": round(float(precision_score(labels, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(labels, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(labels, predictions, zero_division=0)), 4),
    }


def _predict_efficientnet_batch(
    bundle: dict[str, object] | None,
    images: list[object],
) -> list[dict[str, float] | None]:
    if bundle is None:
        return [None] * len(images)

    transform = bundle["transform"]
    model = bundle["model"]
    hb_mean = float(bundle.get("hb_mean", 0.0))
    hb_std = max(float(bundle.get("hb_std", 1.0)), 1e-6)
    tensors = torch.stack([transform(image) for image in images], dim=0)

    with torch.no_grad():
        output = model(tensors)
        probabilities = torch.sigmoid(output[:, 0]).cpu().numpy()
        hemoglobin = ((output[:, 1].cpu().numpy()) * hb_std) + hb_mean

    results: list[dict[str, float]] = []
    for probability, hb_value in zip(probabilities, hemoglobin, strict=True):
        margin_uncertainty = 1.0 - min(1.0, abs(float(probability) - 0.5) * 2.0)
        results.append(
            {
                "anemia_risk": float(probability),
                "predicted_hemoglobin": float(hb_value),
                "uncertainty": float(np.clip((margin_uncertainty * 0.2) + 0.05, 0.05, 0.95)),
            }
        )
    return results


if __name__ == "__main__":
    main()
