from __future__ import annotations

import json

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from app.config import DEFAULT_DEPLOYED_SCREENING_REPORT_PATH
from app.services.image_quality import ImageQualityService
from app.services.prediction import ScreeningPredictor
from train_efficientnet import ARCHIVE_ROOT, _balanced_group_split, _build_records, _load_image_with_fallback


def main() -> None:
    records = _build_records(ARCHIVE_ROOT)
    if not records:
        raise RuntimeError(f"No evaluation records found in {ARCHIVE_ROOT}.")

    _, val_records = _balanced_group_split(records, test_size=0.2, n_splits=32)
    roi_records = [record for record in val_records if record.source == "roi_original"]

    quality_service = ImageQualityService()
    predictor = ScreeningPredictor()

    labels: list[int] = []
    predictions: list[int] = []
    blocked_positive = 0
    blocked_negative = 0
    likely_count = 0
    uncertain_count = 0

    for record in roi_records:
        with record.image_path.open("rb") as handle:
            quality, processed = quality_service.evaluate(handle.read())

        labels.append(int(record.label))
        prediction = predictor.predict(processed, quality) if quality.passed else None
        if prediction is None and quality_service.allows_raw_frame_rescue(quality):
            raw_image = _load_image_with_fallback(record.image_path).convert("RGB")
            raw_prediction = predictor.predict(raw_image, quality)
            if predictor.should_accept_raw_frame_rescue(raw_prediction):
                quality = quality_service.build_raw_frame_rescue_assessment(quality)
                prediction = raw_prediction

        if prediction is None:
            predictions.append(0)
            if record.label:
                blocked_positive += 1
            else:
                blocked_negative += 1
            continue

        predictions.append(int(prediction.screening_label == "anemia_likely"))
        likely_count += int(prediction.screening_label == "anemia_likely")
        uncertain_count += int(prediction.screening_label == "uncertain")

    labels_array = np.asarray(labels, dtype=np.int32)
    predictions_array = np.asarray(predictions, dtype=np.int32)
    report = {
        "evaluation_scope": "deployed_roi_screening",
        "record_count": len(records),
        "validation_size": len(roi_records),
        "metrics": {
            "accuracy": round(float(accuracy_score(labels_array, predictions_array)), 4),
            "precision": round(float(precision_score(labels_array, predictions_array, zero_division=0)), 4),
            "recall": round(float(recall_score(labels_array, predictions_array, zero_division=0)), 4),
            "f1": round(float(f1_score(labels_array, predictions_array, zero_division=0)), 4),
            "split_strategy": "group-shuffle-balance-select: roi_original + deployed quality gate",
        },
        "operating_counts": {
            "blocked_positive": blocked_positive,
            "blocked_negative": blocked_negative,
            "blocked_total": blocked_positive + blocked_negative,
            "likely_count": likely_count,
            "uncertain_count": uncertain_count,
        },
    }
    DEFAULT_DEPLOYED_SCREENING_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\nDeployed ROI screening metrics")
    for key in ("accuracy", "precision", "recall", "f1"):
        print(f"{key}: {report['metrics'][key]:.4f}")
    print(f"blocked_total: {report['operating_counts']['blocked_total']}")
    print(f"likely_count: {report['operating_counts']['likely_count']}")
    print(f"uncertain_count: {report['operating_counts']['uncertain_count']}")


if __name__ == "__main__":
    main()
