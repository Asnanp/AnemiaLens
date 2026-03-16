from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, precision_score, recall_score, roc_auc_score

from app.config import (
    DEFAULT_ARCHIVE_MODEL_PATH,
    DEFAULT_EFFICIENTNET_MODEL_PATH,
    DEFAULT_RUNTIME_STACK_REPORT_PATH,
)
from app.ml.archive_model import load_archive_model, predict_with_archive_model
from app.ml.efficientnet_model import load_efficientnet_checkpoint
from app.ml.features import extract_eye_features
from app.ml.runtime_stack import (
    DEFAULT_SOURCE_THRESHOLDS,
    RUNTIME_STACK_VERSION,
    build_runtime_stack_prediction,
    decision_threshold_for_source,
)
from app.services.conjunctiva_roi import ConjunctivaRoiExtractor
from train_efficientnet import ARCHIVE_ROOT, _balanced_group_split, _build_records, _load_image_with_fallback


def main() -> None:
    records = _build_records(ARCHIVE_ROOT)
    if not records:
        raise RuntimeError(f"No evaluation records found in {ARCHIVE_ROOT}.")

    _, val_records = _balanced_group_split(records, test_size=0.2, n_splits=32)
    archive_model = load_archive_model(DEFAULT_ARCHIVE_MODEL_PATH)
    efficientnet_bundle = (
        load_efficientnet_checkpoint(DEFAULT_EFFICIENTNET_MODEL_PATH)
        if Path(DEFAULT_EFFICIENTNET_MODEL_PATH).exists()
        else None
    )
    roi_extractor = ConjunctivaRoiExtractor()

    runtime_rows: list[dict[str, float | int | str]] = []
    full_rows: list[dict[str, float | int | str]] = []
    prepared_images: list[object] = []
    prepared_sources: list[str] = []
    prepared_archive_predictions: list[dict[str, float]] = []
    prepared_records = []

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
        row = {
            "label": int(record.label),
            "source": str(record.source),
            "risk": float(runtime_prediction["anemia_risk"]),
            "predicted_hb": float(runtime_prediction["predicted_hemoglobin"]),
            "target_hb": float(record.hb),
        }
        full_rows.append(row)
        if record.source == "roi_original":
            runtime_rows.append(row)

    runtime_metrics = _evaluate_rows(runtime_rows, source_aware=False)
    full_metrics = _evaluate_rows(full_rows, source_aware=True)

    report = {
        "primary_model": RUNTIME_STACK_VERSION,
        "record_count": len(records),
        "subject_count": len({record.subject_id for record in records}),
        "selected_mode": "archive_evidence_fusion_runtime",
        "source_thresholds": DEFAULT_SOURCE_THRESHOLDS,
        "metrics": runtime_metrics,
        "full_validation": full_metrics,
    }
    DEFAULT_RUNTIME_STACK_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\nRuntime stack metrics (ROI-gated uploads)")
    for key in ("accuracy", "precision", "recall", "f1", "auc", "hb_mae"):
        print(f"{key}: {runtime_metrics[key]:.4f}")

    print("\nFull validation metrics (all sources)")
    for key in ("accuracy", "precision", "recall", "f1", "auc", "hb_mae"):
        print(f"{key}: {full_metrics[key]:.4f}")


def _evaluate_rows(
    rows: list[dict[str, float | int | str]],
    *,
    source_aware: bool,
) -> dict[str, float | int | str]:
    labels = np.asarray([int(row["label"]) for row in rows], dtype=np.int32)
    probabilities = np.asarray([float(row["risk"]) for row in rows], dtype=np.float32)
    predicted_hb = np.asarray([float(row["predicted_hb"]) for row in rows], dtype=np.float32)
    target_hb = np.asarray([float(row["target_hb"]) for row in rows], dtype=np.float32)

    if source_aware:
        predictions = np.asarray(
            [
                1
                if float(row["risk"]) >= decision_threshold_for_source(str(row["source"]))  # type: ignore[arg-type]
                else 0
                for row in rows
            ],
            dtype=np.int32,
        )
        split_strategy = "group-shuffle-balance-select: source-aware"
    else:
        threshold = decision_threshold_for_source("roi_original")
        predictions = (probabilities >= threshold).astype(np.int32)
        split_strategy = "group-shuffle-balance-select: roi_original"

    return {
        "accuracy": round(float(accuracy_score(labels, predictions)), 4),
        "precision": round(float(precision_score(labels, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(labels, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(labels, predictions, zero_division=0)), 4),
        "auc": round(float(roc_auc_score(labels, probabilities)), 4),
        "hb_mae": round(float(mean_absolute_error(target_hb, predicted_hb)), 4),
        "validation_size": int(len(rows)),
        "split_strategy": split_strategy,
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
