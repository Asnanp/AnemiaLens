from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, mean_absolute_error, precision_score, recall_score, roc_auc_score
from torch.utils.data import DataLoader

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from app.config import DEFAULT_EFFICIENTNET_MODEL_PATH
from app.ml.efficientnet_model import load_efficientnet_checkpoint
from train_efficientnet import (
    ARCHIVE_ROOT,
    DATA_ROOT,
    ConjunctivaDataset,
    _balanced_group_split,
    _build_records,
    build_val_transform,
)

DEFAULT_OUTPUT_PATH = BACKEND_ROOT / "models" / "efficientnet_error_report.json"


def main() -> None:
    dataset_root = DATA_ROOT if DATA_ROOT.exists() else ARCHIVE_ROOT
    records = _build_records(dataset_root)
    if not records:
        raise RuntimeError(f"No dataset records found under {dataset_root}.")
    if not DEFAULT_EFFICIENTNET_MODEL_PATH.exists():
        raise RuntimeError(f"EfficientNet checkpoint not found at {DEFAULT_EFFICIENTNET_MODEL_PATH}.")

    train_records, val_records = _balanced_group_split(records, test_size=0.2, n_splits=32)
    bundle = load_efficientnet_checkpoint(DEFAULT_EFFICIENTNET_MODEL_PATH)
    report = analyze_validation_split(val_records, bundle, dataset_root=dataset_root, train_records=train_records)

    DEFAULT_OUTPUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved error report to {DEFAULT_OUTPUT_PATH}")
    print(json.dumps(report["summary"], indent=2))


def analyze_validation_split(
    val_records: list,
    bundle: dict[str, object],
    *,
    dataset_root: Path,
    train_records: list,
) -> dict[str, object]:
    model = bundle["model"]
    device = bundle["device"]
    hb_mean = float(bundle.get("hb_mean", 0.0))
    hb_std = float(bundle.get("hb_std", 1.0))
    threshold = float(bundle.get("decision_threshold", 0.5))

    dataset = ConjunctivaDataset(val_records, build_val_transform())
    loader = DataLoader(dataset, batch_size=16, shuffle=False, num_workers=0)

    probabilities: list[float] = []
    predictions: list[int] = []
    labels: list[int] = []
    hb_predictions: list[float] = []
    hb_targets: list[float] = []

    model.eval()
    with torch.no_grad():
        for images, batch_labels, batch_hbs in loader:
            output = model(images.to(device))
            batch_probabilities = torch.sigmoid(output[:, 0]).cpu().tolist()
            batch_hb_predictions = (((output[:, 1].cpu()) * hb_std) + hb_mean).tolist()
            probabilities.extend(batch_probabilities)
            predictions.extend([1 if value >= threshold else 0 for value in batch_probabilities])
            labels.extend(batch_labels.squeeze(1).cpu().int().tolist())
            hb_predictions.extend(batch_hb_predictions)
            hb_targets.extend(batch_hbs.squeeze(1).cpu().tolist())

    summary = {
        "dataset_root": str(dataset_root),
        "checkpoint_path": str(DEFAULT_EFFICIENTNET_MODEL_PATH),
        "record_count": len(val_records),
        "subject_count": len({record.subject_id for record in val_records}),
        "threshold": round(threshold, 4),
        "train_record_count": len(train_records),
        "train_subject_count": len({record.subject_id for record in train_records}),
        "accuracy": round(float(accuracy_score(labels, predictions)), 4),
        "precision": round(float(precision_score(labels, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(labels, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(labels, predictions, zero_division=0)), 4),
        "auc": round(float(roc_auc_score(labels, probabilities)), 4),
        "hb_mae": round(float(mean_absolute_error(hb_targets, hb_predictions)), 4),
        "label_counts": dict(Counter(labels)),
        "prediction_counts": dict(Counter(predictions)),
        "confusion_matrix": confusion_matrix(labels, predictions).tolist(),
    }

    source_breakdown = _source_breakdown(val_records, labels, predictions, probabilities, hb_predictions, hb_targets)
    false_positives, false_negatives = _mistakes(val_records, labels, predictions, probabilities, hb_predictions, hb_targets)

    return {
        "summary": summary,
        "source_breakdown": source_breakdown,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def _source_breakdown(
    val_records: list,
    labels: list[int],
    predictions: list[int],
    probabilities: list[float],
    hb_predictions: list[float],
    hb_targets: list[float],
) -> dict[str, object]:
    by_source: dict[str, dict[str, object]] = defaultdict(
        lambda: {
            "count": 0,
            "errors": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "probabilities": [],
            "hb_abs_error": [],
        }
    )

    for record, label, prediction, probability, hb_prediction, hb_target in zip(
        val_records,
        labels,
        predictions,
        probabilities,
        hb_predictions,
        hb_targets,
    ):
        item = by_source[record.source]
        item["count"] += 1
        item["errors"] += int(label != prediction)
        item["false_positives"] += int(label == 0 and prediction == 1)
        item["false_negatives"] += int(label == 1 and prediction == 0)
        item["probabilities"].append(float(probability))
        item["hb_abs_error"].append(abs(float(hb_prediction) - float(hb_target)))

    normalized: dict[str, object] = {}
    for source, item in by_source.items():
        normalized[source] = {
            "count": item["count"],
            "errors": item["errors"],
            "false_positives": item["false_positives"],
            "false_negatives": item["false_negatives"],
            "error_rate": round(float(item["errors"] / max(item["count"], 1)), 4),
            "mean_probability": round(float(np.mean(item["probabilities"])), 4),
            "hb_mae": round(float(np.mean(item["hb_abs_error"])), 4),
        }
    return normalized


def _mistakes(
    val_records: list,
    labels: list[int],
    predictions: list[int],
    probabilities: list[float],
    hb_predictions: list[float],
    hb_targets: list[float],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    false_positives: list[dict[str, object]] = []
    false_negatives: list[dict[str, object]] = []

    for record, label, prediction, probability, hb_prediction, hb_target in zip(
        val_records,
        labels,
        predictions,
        probabilities,
        hb_predictions,
        hb_targets,
    ):
        if label == prediction:
            continue
        item = {
            "subject_id": record.subject_id,
            "source": record.source,
            "probability": round(float(probability), 4),
            "hb_true": round(float(hb_target), 2),
            "hb_predicted": round(float(hb_prediction), 2),
            "image_path": str(record.image_path),
        }
        if label == 0 and prediction == 1:
            false_positives.append(item)
        else:
            false_negatives.append(item)

    false_positives.sort(key=lambda item: float(item["probability"]), reverse=True)
    false_negatives.sort(key=lambda item: float(item["probability"]))
    return false_positives[:12], false_negatives[:12]


if __name__ == "__main__":
    main()
