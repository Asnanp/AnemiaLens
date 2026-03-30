from __future__ import annotations

import math
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image
from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler

from app.ml.features import (
    V8_CLINICAL_FEATURE_NAMES,
    extract_v8_clinical_features,
    load_image_path,
)
from app.schemas import QualityAssessment
from app.services.image_quality import ImageQualityService

V8_VERSION = "archive-fusion-v8-clinical-robust"
ANEMIA_HB_THRESHOLD = 11.5
_XLSX_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, float(value)))


def sigmoid(value: float) -> float:
    if value >= 0:
        exp_value = math.exp(-value)
        return 1.0 / (1.0 + exp_value)
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def predict_with_archive_model_v8(
    artifact: dict[str, object],
    feature_map: dict[str, float],
    *,
    source_hint: str = "roi_original",
) -> dict[str, float]:
    feat_names = artifact.get("feature_names")
    if not isinstance(feat_names, list) or not feat_names:
        feat_names = V8_CLINICAL_FEATURE_NAMES

    prepared = {name: float(feature_map.get(name, 0.0)) for name in feat_names}
    source_value = str(source_hint).strip().lower()
    prepared["source_roi_original"] = 1.0 if source_value == "roi_original" else 0.0
    prepared["source_palpebral"] = 1.0 if source_value == "palpebral" else 0.0
    prepared["source_forniceal_palpebral"] = 1.0 if source_value == "forniceal_palpebral" else 0.0

    row = np.asarray([prepared[name] for name in feat_names], dtype=np.float32).reshape(1, -1)
    scalers = artifact.get("scalers")
    linear_scaler = scalers.get("linear") if isinstance(scalers, dict) else artifact.get("scaler")
    row_scaled = row
    if linear_scaler is not None:
        try:
            row_scaled = np.asarray(linear_scaler.transform(row), dtype=np.float32)
        except Exception:
            row_scaled = row

    models = artifact.get("models")
    if not isinstance(models, dict):
        models = {}
    scaled_models = {
        str(name)
        for name in artifact.get("scaled_models", [])
        if isinstance(name, str)
    }

    classifier_predictions: list[float] = []
    classifier_weights: list[float] = []
    for name, weight in _ordered_weights(artifact.get("classifier_weights")):
        model = models.get(name)
        score = _safe_classifier_predict(
            model,
            row_scaled if name in scaled_models else row,
        )
        if score is not None:
            classifier_predictions.append(score)
            classifier_weights.append(weight)

    hb_predictions: list[float] = []
    regressor_weights: list[float] = []
    for name, weight in _ordered_weights(artifact.get("regressor_weights")):
        model = models.get(name)
        score = _safe_regression_predict(
            model,
            row_scaled if name in scaled_models else row,
        )
        if score is not None:
            hb_predictions.append(score)
            regressor_weights.append(weight)

    if not classifier_predictions and not hb_predictions:
        raise RuntimeError("V8 clinical artifact contains no usable predictor heads.")

    classifier_probability = (
        _weighted_average(classifier_predictions, classifier_weights)
        if classifier_predictions
        else 0.0
    )
    predicted_hb = (
        _weighted_average(hb_predictions, regressor_weights)
        if hb_predictions
        else float(np.clip(13.0 - (classifier_probability * 2.6), 6.0, 18.0))
    )

    calibration = artifact.get("calibration")
    calibration_map = calibration if isinstance(calibration, dict) else {}
    hb_threshold = float(calibration_map.get("hb_threshold", ANEMIA_HB_THRESHOLD))
    hb_scale = float(calibration_map.get("hb_scale", 1.0))
    classifier_weight = float(calibration_map.get("classifier_weight", 0.60))
    blend_threshold = float(calibration_map.get("blend_threshold", 0.48))
    risk_scale = float(calibration_map.get("risk_scale", 0.16))

    regressor_risk = float(sigmoid((hb_threshold - predicted_hb) / max(hb_scale, 1e-6)))
    blend_signal = float(
        (classifier_probability * classifier_weight)
        + (regressor_risk * (1.0 - classifier_weight))
    )
    risk = float(sigmoid((blend_signal - blend_threshold) / max(risk_scale, 1e-6)))

    classifier_spread = float(np.std(classifier_predictions)) if len(classifier_predictions) > 1 else 0.0
    hb_spread = float(np.std(hb_predictions)) if len(hb_predictions) > 1 else 0.0
    disagreement = abs(classifier_probability - regressor_risk)
    lighting_penalty = (
        (1.0 - float(feature_map.get("lighting_score", 0.72))) * 0.45
        + float(feature_map.get("glare_risk", 0.0)) * 0.30
        + float(feature_map.get("shadow_risk", 0.0)) * 0.25
    )
    margin_uncertainty = 1.0 - min(1.0, abs(blend_signal - blend_threshold) / 0.24)
    uncertainty = clamp(
        (classifier_spread * 0.25)
        + (min(hb_spread / 1.8, 1.0) * 0.18)
        + (disagreement * 0.22)
        + (margin_uncertainty * 0.18)
        + (lighting_penalty * 0.12)
        + 0.05,
        0.05,
        0.92,
    )
    hb_interval_half_width = max(
        0.6,
        hb_scale * (0.95 + (hb_spread * 0.85) + (uncertainty * 0.4)),
    )

    return {
        "anemia_risk": risk,
        "predicted_hemoglobin": float(np.clip(predicted_hb, 4.8, 20.0)),
        "uncertainty": uncertainty,
        "classifier_probability": classifier_probability,
        "regressor_risk": regressor_risk,
        "blend_signal": blend_signal,
        "decision_threshold": blend_threshold,
        "hb_interval_low": round(max(predicted_hb - hb_interval_half_width, 4.0), 1),
        "hb_interval_high": round(min(predicted_hb + hb_interval_half_width, 22.0), 1),
    }


def train_archive_model_v8(
    dataset_root: str | Path,
    *,
    n_splits: int = 10,
    test_size: float = 0.2,
) -> tuple[dict[str, object], dict[str, object]]:
    samples = build_v8_samples(Path(dataset_root))
    if not samples:
        raise RuntimeError("No v8 training samples were built from the archive dataset.")

    rows, targets, labels, groups, sample_weights, sources = _rows_from_samples(samples)
    classifier_weights = _derive_classifier_weights(
        rows,
        labels,
        groups,
        sample_weights,
        n_splits=n_splits,
        test_size=test_size,
    )
    regressor_weights = _derive_regressor_weights(
        rows,
        targets,
        groups,
        sample_weights,
        n_splits=n_splits,
        test_size=test_size,
    )
    calibration, metrics, diagnostics = _evaluate_v8_configuration(
        rows,
        targets,
        labels,
        groups,
        sample_weights,
        classifier_weights=classifier_weights,
        regressor_weights=regressor_weights,
        n_splits=n_splits,
        test_size=test_size,
    )

    scaler = StandardScaler()
    scaled_rows = scaler.fit_transform(rows)
    models: dict[str, object] = {}
    scaled_models: list[str] = []

    for name, entry in _classifier_suite(seed=2026).items():
        model = entry["builder"]()
        _fit_with_optional_weight(
            model,
            scaled_rows if entry["scaled"] else rows,
            labels,
            sample_weights,
        )
        models[name] = model
        if entry["scaled"]:
            scaled_models.append(name)

    for name, entry in _regressor_suite(seed=2026).items():
        model = entry["builder"]()
        _fit_with_optional_weight(
            model,
            scaled_rows if entry["scaled"] else rows,
            targets,
            sample_weights,
        )
        models[name] = model
        if entry["scaled"]:
            scaled_models.append(name)

    source_counts = dict(Counter(sources.tolist()))
    artifact = {
        "version": V8_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "feature_names": V8_CLINICAL_FEATURE_NAMES,
        "models": models,
        "scalers": {"linear": scaler},
        "scaled_models": sorted(set(scaled_models)),
        "classifier_weights": classifier_weights,
        "regressor_weights": regressor_weights,
        "calibration": calibration,
        "training": {
            "selected_mode": "v8_multi_view_live_aligned",
            "record_count": int(len(samples)),
            "subject_count": int(len(set(groups.tolist()))),
            "source_counts": source_counts,
            "metrics": metrics,
            "diagnostics": diagnostics,
            "top_features": _v8_feature_importance_summary(
                models,
                classifier_weights,
                regressor_weights,
            ),
        },
    }
    report = {
        "dataset_name": "dataset anemia (v8 multi-view live-aligned)",
        "record_count": int(len(samples)),
        "subject_count": int(len(set(groups.tolist()))),
        "primary_model": V8_VERSION,
        "selected_mode": "v8_multi_view_live_aligned",
        "source_counts": source_counts,
        "metrics": metrics,
        "calibration": calibration,
        "classifier_weights": classifier_weights,
        "regressor_weights": regressor_weights,
        "diagnostics": diagnostics,
        "top_features": artifact["training"]["top_features"],
    }
    return artifact, report


def build_v8_samples(dataset_root: Path) -> list[dict[str, object]]:
    quality_service = ImageQualityService()
    samples: list[dict[str, object]] = []

    for country in ("India", "Italy"):
        workbook_path = dataset_root / country / f"{country}.xlsx"
        metadata = _parse_workbook(workbook_path)
        for subject_number, row in metadata.items():
            hb = _parse_float(row.get("Hgb"))
            if hb is None:
                continue

            subject_dir = dataset_root / country / subject_number
            if not subject_dir.exists():
                continue

            age = _safe_int(row.get("Age"))
            sex = _normalise_sex(row.get("Gender"))
            subject_id = f"{country}-{subject_number}"

            raw_path = _first_path(subject_dir.glob("*.jpg"))
            if raw_path is not None:
                try:
                    quality, roi_image = quality_service.evaluate(raw_path.read_bytes())
                    if quality.passed:
                        feature_map = extract_v8_clinical_features(
                            roi_image,
                            quality,
                            age=age,
                            sex=sex,
                            source_hint="roi_original",
                        )
                        samples.append(
                            _sample_record(
                                subject_id=subject_id,
                                country=country,
                                source="roi_original",
                                hb=hb,
                                age=age,
                                sex=sex,
                                features=feature_map,
                                quality=quality,
                            )
                        )
                except Exception:
                    pass

            palpebral_path = _first_path(
                path
                for path in subject_dir.glob("*_palpebral.png")
                if "forniceal_palpebral" not in path.name.lower()
            )
            if palpebral_path is not None:
                try:
                    palpebral = _load_image_with_fallback(palpebral_path)
                    feature_map = extract_v8_clinical_features(
                        palpebral,
                        None,
                        age=age,
                        sex=sex,
                        source_hint="palpebral",
                    )
                    samples.append(
                        _sample_record(
                            subject_id=subject_id,
                            country=country,
                            source="palpebral",
                            hb=hb,
                            age=age,
                            sex=sex,
                            features=feature_map,
                            quality=None,
                        )
                    )
                except Exception:
                    pass

            forniceal_path = _first_path(subject_dir.glob("*_forniceal_palpebral.png"))
            if forniceal_path is not None:
                try:
                    forniceal = _load_image_with_fallback(forniceal_path)
                    feature_map = extract_v8_clinical_features(
                        forniceal,
                        None,
                        age=age,
                        sex=sex,
                        source_hint="forniceal_palpebral",
                    )
                    samples.append(
                        _sample_record(
                            subject_id=subject_id,
                            country=country,
                            source="forniceal_palpebral",
                            hb=hb,
                            age=age,
                            sex=sex,
                            features=feature_map,
                            quality=None,
                        )
                    )
                except Exception:
                    pass

    return samples


def _sample_record(
    *,
    subject_id: str,
    country: str,
    source: str,
    hb: float,
    age: int | None,
    sex: str,
    features: dict[str, float],
    quality: QualityAssessment | None,
) -> dict[str, object]:
    label = int(hb < ANEMIA_HB_THRESHOLD)
    weight = 1.0

    margin = abs(float(hb) - ANEMIA_HB_THRESHOLD)
    if margin < 0.4:
        weight *= 0.78
    elif margin >= 1.0:
        weight *= 1.12

    if label == 1 and hb <= 10.8:
        weight *= 1.14
    if label == 0 and hb >= 12.5:
        weight *= 1.18

    if source == "roi_original":
        weight *= 1.22
    elif source == "forniceal_palpebral":
        weight *= 0.96

    if features.get("lighting_score", 0.7) < 0.38:
        weight *= 0.88
    if features.get("glare_risk", 0.0) > 0.65 or features.get("shadow_risk", 0.0) > 0.65:
        weight *= 0.84
    if quality is not None and not quality.passed:
        weight *= 0.72

    return {
        "group": subject_id,
        "country": country,
        "source": source,
        "age": age,
        "sex": sex,
        "hb": float(hb),
        "label": label,
        "features": {name: float(features.get(name, 0.0)) for name in V8_CLINICAL_FEATURE_NAMES},
        "sample_weight": clamp(weight, 0.45, 1.7),
    }


def _rows_from_samples(
    samples: list[dict[str, object]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rows = np.asarray(
        [[float(sample["features"][name]) for name in V8_CLINICAL_FEATURE_NAMES] for sample in samples],
        dtype=np.float32,
    )
    targets = np.asarray([float(sample["hb"]) for sample in samples], dtype=np.float32)
    labels = np.asarray([int(sample["label"]) for sample in samples], dtype=np.int32)
    groups = np.asarray([str(sample["group"]) for sample in samples], dtype=object)
    weights = np.asarray([float(sample["sample_weight"]) for sample in samples], dtype=np.float32)
    sources = np.asarray([str(sample["source"]) for sample in samples], dtype=object)
    return rows, targets, labels, groups, weights, sources


def _derive_classifier_weights(
    rows: np.ndarray,
    labels: np.ndarray,
    groups: np.ndarray,
    sample_weights: np.ndarray,
    *,
    n_splits: int,
    test_size: float,
) -> dict[str, float]:
    score_bag: dict[str, list[float]] = defaultdict(list)
    splitter = GroupShuffleSplit(n_splits=n_splits, test_size=test_size, random_state=2026)

    for split_index, (train_index, test_index) in enumerate(splitter.split(rows, labels, groups)):
        scaler = StandardScaler()
        scaler.fit(rows[train_index])
        train_rows = rows[train_index]
        test_rows = rows[test_index]
        train_scaled = scaler.transform(train_rows)
        test_scaled = scaler.transform(test_rows)
        train_weights = sample_weights[train_index]
        train_labels = labels[train_index]
        test_labels = labels[test_index]

        for name, entry in _classifier_suite(seed=3100 + split_index).items():
            model = entry["builder"]()
            _fit_with_optional_weight(
                model,
                train_scaled if entry["scaled"] else train_rows,
                train_labels,
                train_weights,
            )
            probabilities = _predict_classifier_array(
                model,
                test_scaled if entry["scaled"] else test_rows,
            )
            auc = _safe_auc(test_labels, probabilities)
            preds = (probabilities >= 0.5).astype(np.int32)
            f1 = float(f1_score(test_labels, preds, zero_division=0))
            precision = float(precision_score(test_labels, preds, zero_division=0))
            score_bag[name].append(((auc - 0.5) * 0.55) + (f1 * 0.30) + (precision * 0.15))

    return _normalise_positive_weights(score_bag, fallback_names=list(_classifier_suite(seed=0).keys()))


def _derive_regressor_weights(
    rows: np.ndarray,
    targets: np.ndarray,
    groups: np.ndarray,
    sample_weights: np.ndarray,
    *,
    n_splits: int,
    test_size: float,
) -> dict[str, float]:
    score_bag: dict[str, list[float]] = defaultdict(list)
    splitter = GroupShuffleSplit(n_splits=n_splits, test_size=test_size, random_state=4096)

    for split_index, (train_index, test_index) in enumerate(splitter.split(rows, targets, groups)):
        scaler = StandardScaler()
        scaler.fit(rows[train_index])
        train_rows = rows[train_index]
        test_rows = rows[test_index]
        train_scaled = scaler.transform(train_rows)
        test_scaled = scaler.transform(test_rows)
        train_weights = sample_weights[train_index]
        train_targets = targets[train_index]
        test_targets = targets[test_index]

        for name, entry in _regressor_suite(seed=5100 + split_index).items():
            model = entry["builder"]()
            _fit_with_optional_weight(
                model,
                train_scaled if entry["scaled"] else train_rows,
                train_targets,
                train_weights,
            )
            predictions = np.asarray(
                model.predict(test_scaled if entry["scaled"] else test_rows),
                dtype=np.float32,
            )
            mae = float(mean_absolute_error(test_targets, predictions))
            score_bag[name].append(1.0 / max(mae, 0.45))

    return _normalise_positive_weights(score_bag, fallback_names=list(_regressor_suite(seed=0).keys()))


def _evaluate_v8_configuration(
    rows: np.ndarray,
    targets: np.ndarray,
    labels: np.ndarray,
    groups: np.ndarray,
    sample_weights: np.ndarray,
    *,
    classifier_weights: dict[str, float],
    regressor_weights: dict[str, float],
    n_splits: int,
    test_size: float,
) -> tuple[dict[str, float], dict[str, float], dict[str, object]]:
    pooled_labels: list[int] = []
    pooled_classifier: list[float] = []
    pooled_hb: list[float] = []
    split_metrics: list[dict[str, float]] = []
    splitter = GroupShuffleSplit(n_splits=n_splits, test_size=test_size, random_state=777)

    for split_index, (train_index, test_index) in enumerate(splitter.split(rows, labels, groups)):
        models, scaler = _fit_v8_model_bundle(
            rows[train_index],
            targets[train_index],
            labels[train_index],
            sample_weights[train_index],
            seed=7000 + split_index,
        )
        classifier_prob = _ensemble_classifier_predictions(
            models,
            scaler,
            rows[test_index],
            classifier_weights,
        )
        hb_predictions = _ensemble_regressor_predictions(
            models,
            scaler,
            rows[test_index],
            regressor_weights,
        )
        pooled_labels.extend(labels[test_index].tolist())
        pooled_classifier.extend(classifier_prob.tolist())
        pooled_hb.extend(hb_predictions.tolist())

    pooled_labels_arr = np.asarray(pooled_labels, dtype=np.int32)
    pooled_classifier_arr = np.asarray(pooled_classifier, dtype=np.float32)
    pooled_hb_arr = np.asarray(pooled_hb, dtype=np.float32)

    calibration = _search_blend_configuration(
        pooled_labels_arr,
        pooled_classifier_arr,
        pooled_hb_arr,
    )

    splitter = GroupShuffleSplit(n_splits=n_splits, test_size=test_size, random_state=1313)
    for split_index, (train_index, test_index) in enumerate(splitter.split(rows, labels, groups)):
        models, scaler = _fit_v8_model_bundle(
            rows[train_index],
            targets[train_index],
            labels[train_index],
            sample_weights[train_index],
            seed=8100 + split_index,
        )
        classifier_prob = _ensemble_classifier_predictions(
            models,
            scaler,
            rows[test_index],
            classifier_weights,
        )
        hb_predictions = _ensemble_regressor_predictions(
            models,
            scaler,
            rows[test_index],
            regressor_weights,
        )
        regressor_risk = np.asarray(
            [sigmoid((ANEMIA_HB_THRESHOLD - value) / calibration["hb_scale"]) for value in hb_predictions],
            dtype=np.float32,
        )
        blend_signal = (
            classifier_prob * calibration["classifier_weight"]
            + regressor_risk * (1.0 - calibration["classifier_weight"])
        )
        risk = np.asarray(
            [sigmoid((value - calibration["blend_threshold"]) / calibration["risk_scale"]) for value in blend_signal],
            dtype=np.float32,
        )
        predicted_labels = (risk >= 0.5).astype(np.int32)
        split_metrics.append(
            {
                "accuracy": float(accuracy_score(labels[test_index], predicted_labels)),
                "precision": float(precision_score(labels[test_index], predicted_labels, zero_division=0)),
                "recall": float(recall_score(labels[test_index], predicted_labels, zero_division=0)),
                "f1": float(f1_score(labels[test_index], predicted_labels, zero_division=0)),
                "auc": float(_safe_auc(labels[test_index], risk)),
                "mae_hb": float(mean_absolute_error(targets[test_index], hb_predictions)),
            }
        )

    averaged_metrics = {
        name: round(float(np.mean([metric[name] for metric in split_metrics])), 4)
        for name in ("accuracy", "precision", "recall", "f1", "auc", "mae_hb")
    }
    averaged_metrics["split_strategy"] = "group-shuffle-repeat-v8-multiview"
    averaged_metrics["validation_size"] = int(round(len(rows) * test_size))

    diagnostics = {
        "record_count": int(len(rows)),
        "positive_rate": round(float(np.mean(labels)), 4),
        "pooled_classifier_mean": round(float(np.mean(pooled_classifier_arr)), 4),
        "pooled_hb_mean": round(float(np.mean(pooled_hb_arr)), 4),
        "split_count": n_splits,
    }
    return calibration, averaged_metrics, diagnostics


def _fit_v8_model_bundle(
    train_rows: np.ndarray,
    train_targets: np.ndarray,
    train_labels: np.ndarray,
    train_weights: np.ndarray,
    *,
    seed: int,
) -> tuple[dict[str, object], StandardScaler]:
    scaler = StandardScaler()
    scaler.fit(train_rows)
    train_scaled = scaler.transform(train_rows)
    models: dict[str, object] = {}

    for name, entry in _classifier_suite(seed=seed).items():
        model = entry["builder"]()
        _fit_with_optional_weight(
            model,
            train_scaled if entry["scaled"] else train_rows,
            train_labels,
            train_weights,
        )
        models[name] = model

    for name, entry in _regressor_suite(seed=seed).items():
        model = entry["builder"]()
        _fit_with_optional_weight(
            model,
            train_scaled if entry["scaled"] else train_rows,
            train_targets,
            train_weights,
        )
        models[name] = model

    return models, scaler


def _search_blend_configuration(
    labels: np.ndarray,
    classifier_probabilities: np.ndarray,
    hb_predictions: np.ndarray,
) -> dict[str, float]:
    best: dict[str, float] | None = None
    for classifier_weight in np.linspace(0.48, 0.74, 14):
        for hb_scale in np.linspace(0.85, 1.4, 12):
            regressor_risk = np.asarray(
                [sigmoid((ANEMIA_HB_THRESHOLD - value) / hb_scale) for value in hb_predictions],
                dtype=np.float32,
            )
            blend_signal = (
                classifier_probabilities * classifier_weight
                + regressor_risk * (1.0 - classifier_weight)
            )
            for blend_threshold in np.linspace(0.36, 0.60, 25):
                predicted_labels = (blend_signal >= blend_threshold).astype(np.int32)
                accuracy = float(accuracy_score(labels, predicted_labels))
                precision = float(precision_score(labels, predicted_labels, zero_division=0))
                recall = float(recall_score(labels, predicted_labels, zero_division=0))
                f1 = float(f1_score(labels, predicted_labels, zero_division=0))
                auc = float(_safe_auc(labels, blend_signal))
                score = (
                    accuracy * 0.10
                    + precision * 0.27
                    + recall * 0.28
                    + f1 * 0.25
                    + auc * 0.10
                )
                if recall < 0.78:
                    score -= (0.78 - recall) * 0.8
                if precision < 0.70:
                    score -= (0.70 - precision) * 0.45
                if best is None or score > best["selection_score"]:
                    spread = float(np.std(blend_signal)) if blend_signal.size > 1 else 0.12
                    best = {
                        "selection_score": score,
                        "classifier_weight": round(float(classifier_weight), 4),
                        "blend_threshold": round(float(blend_threshold), 4),
                        "hb_scale": round(float(hb_scale), 4),
                        "risk_scale": round(clamp(spread * 0.88, 0.09, 0.18), 4),
                        "hb_threshold": ANEMIA_HB_THRESHOLD,
                    }

    if best is None:
        return {
            "classifier_weight": 0.62,
            "blend_threshold": 0.48,
            "hb_scale": 1.0,
            "risk_scale": 0.14,
            "hb_threshold": ANEMIA_HB_THRESHOLD,
        }
    best.pop("selection_score", None)
    return best


def _ensemble_classifier_predictions(
    models: dict[str, object],
    scaler: StandardScaler,
    rows: np.ndarray,
    weights: dict[str, float],
) -> np.ndarray:
    scaled_rows = scaler.transform(rows)
    outputs: list[np.ndarray] = []
    output_weights: list[float] = []
    for name, weight in weights.items():
        model = models.get(name)
        if model is None:
            continue
        array = _predict_classifier_array(
            model,
            scaled_rows if name == "lr_clf" else rows,
        )
        outputs.append(array)
        output_weights.append(float(weight))
    if not outputs:
        raise RuntimeError("No classifier outputs available for v8 evaluation.")
    return _weighted_average_matrix(outputs, output_weights)


def _ensemble_regressor_predictions(
    models: dict[str, object],
    scaler: StandardScaler,
    rows: np.ndarray,
    weights: dict[str, float],
) -> np.ndarray:
    scaled_rows = scaler.transform(rows)
    outputs: list[np.ndarray] = []
    output_weights: list[float] = []
    for name, weight in weights.items():
        model = models.get(name)
        if model is None:
            continue
        array = np.asarray(
            model.predict(scaled_rows if name == "ridge_reg" else rows),
            dtype=np.float32,
        )
        outputs.append(array)
        output_weights.append(float(weight))
    if not outputs:
        raise RuntimeError("No regressor outputs available for v8 evaluation.")
    return _weighted_average_matrix(outputs, output_weights)


def _classifier_suite(*, seed: int) -> dict[str, dict[str, Any]]:
    return {
        "hgb_clf": {
            "scaled": False,
            "builder": lambda: HistGradientBoostingClassifier(
                max_depth=3,
                learning_rate=0.045,
                max_iter=260,
                min_samples_leaf=6,
                l2_regularization=0.16,
                random_state=seed,
            ),
        },
        "et_clf": {
            "scaled": False,
            "builder": lambda: ExtraTreesClassifier(
                n_estimators=520,
                max_features="sqrt",
                min_samples_leaf=3,
                bootstrap=True,
                class_weight="balanced_subsample",
                random_state=seed + 1,
                n_jobs=1,
            ),
        },
        "rf_clf": {
            "scaled": False,
            "builder": lambda: RandomForestClassifier(
                n_estimators=460,
                max_features="sqrt",
                min_samples_leaf=4,
                bootstrap=True,
                class_weight="balanced_subsample",
                random_state=seed + 2,
                n_jobs=1,
            ),
        },
        "lr_clf": {
            "scaled": True,
            "builder": lambda: LogisticRegression(
                C=0.9,
                class_weight="balanced",
                max_iter=4000,
                solver="lbfgs",
                random_state=seed + 3,
            ),
        },
    }


def _regressor_suite(*, seed: int) -> dict[str, dict[str, Any]]:
    return {
        "hgb_reg": {
            "scaled": False,
            "builder": lambda: HistGradientBoostingRegressor(
                max_depth=3,
                learning_rate=0.045,
                max_iter=280,
                min_samples_leaf=6,
                l2_regularization=0.12,
                random_state=seed,
            ),
        },
        "et_reg": {
            "scaled": False,
            "builder": lambda: ExtraTreesRegressor(
                n_estimators=520,
                max_features="sqrt",
                min_samples_leaf=3,
                bootstrap=True,
                random_state=seed + 1,
                n_jobs=1,
            ),
        },
        "rf_reg": {
            "scaled": False,
            "builder": lambda: RandomForestRegressor(
                n_estimators=460,
                max_features="sqrt",
                min_samples_leaf=4,
                bootstrap=True,
                random_state=seed + 2,
                n_jobs=1,
            ),
        },
        "ridge_reg": {
            "scaled": True,
            "builder": lambda: Ridge(alpha=1.4, random_state=seed + 3),
        },
    }


def _fit_with_optional_weight(model, rows, target, sample_weight: np.ndarray) -> None:
    try:
        model.fit(rows, target, sample_weight=sample_weight)
    except TypeError:
        model.fit(rows, target)


def _predict_classifier_array(model, rows: np.ndarray) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return np.asarray(model.predict_proba(rows)[:, 1], dtype=np.float32)
    if hasattr(model, "decision_function"):
        scores = np.asarray(model.decision_function(rows), dtype=np.float32)
        return np.asarray([sigmoid(value) for value in scores], dtype=np.float32)
    return np.asarray(model.predict(rows), dtype=np.float32)


def _safe_classifier_predict(model, row: np.ndarray) -> float | None:
    try:
        return float(_predict_classifier_array(model, row)[0])
    except Exception:
        return None


def _safe_regression_predict(model, row: np.ndarray) -> float | None:
    try:
        return float(model.predict(row)[0])
    except Exception:
        return None


def _safe_auc(labels: np.ndarray, scores: np.ndarray) -> float:
    if len(np.unique(labels)) < 2:
        return 0.5
    return float(roc_auc_score(labels, scores))


def _weighted_average(values: list[float], weights: list[float]) -> float:
    total = max(sum(weights), 1e-6)
    return float(sum(value * weight for value, weight in zip(values, weights)) / total)


def _weighted_average_matrix(values: list[np.ndarray], weights: list[float]) -> np.ndarray:
    total = max(sum(weights), 1e-6)
    blended = np.zeros_like(values[0], dtype=np.float32)
    for value, weight in zip(values, weights):
        blended += np.asarray(value, dtype=np.float32) * float(weight)
    return blended / total


def _ordered_weights(weight_map: object) -> list[tuple[str, float]]:
    if not isinstance(weight_map, dict):
        return []
    ordered = [
        (str(name), float(weight))
        for name, weight in weight_map.items()
        if isinstance(name, str)
    ]
    return sorted(ordered, key=lambda item: item[1], reverse=True)


def _normalise_positive_weights(
    weight_bag: dict[str, list[float]],
    *,
    fallback_names: list[str],
) -> dict[str, float]:
    raw_weights = {
        name: max(float(np.mean(values)), 1e-3)
        for name, values in weight_bag.items()
        if values
    }
    if not raw_weights:
        raw_weights = {name: 1.0 for name in fallback_names}
    total = sum(raw_weights.values())
    return {
        name: round(float(weight / total), 4)
        for name, weight in sorted(raw_weights.items())
    }


def _v8_feature_importance_summary(
    models: dict[str, object],
    classifier_weights: dict[str, float],
    regressor_weights: dict[str, float],
    *,
    limit: int = 10,
) -> list[dict[str, object]]:
    importances = np.zeros(len(V8_CLINICAL_FEATURE_NAMES), dtype=np.float64)

    for name, weight in classifier_weights.items():
        model = models.get(name)
        feature_importance = getattr(model, "feature_importances_", None)
        if feature_importance is not None:
            importances += np.asarray(feature_importance, dtype=np.float64) * float(weight) * 0.6

    for name, weight in regressor_weights.items():
        model = models.get(name)
        feature_importance = getattr(model, "feature_importances_", None)
        if feature_importance is not None:
            importances += np.asarray(feature_importance, dtype=np.float64) * float(weight) * 0.4

    ranked = sorted(
        zip(V8_CLINICAL_FEATURE_NAMES, importances.tolist()),
        key=lambda item: item[1],
        reverse=True,
    )
    return [
        {"name": name, "importance": round(float(importance), 4)}
        for name, importance in ranked[:limit]
    ]


def _safe_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(float(str(value)))
    except Exception:
        return None


def _normalise_sex(value: object) -> str:
    normalised = str(value or "").strip().lower()
    if normalised in {"f", "female"}:
        return "female"
    if normalised in {"m", "male"}:
        return "male"
    return "not_specified"


def _parse_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        stripped = str(value).strip()
        if not stripped:
            return None
        return float(stripped)
    except Exception:
        return None


def _first_path(paths: object) -> Path | None:
    ordered = sorted(Path(path) for path in paths)
    return ordered[0] if ordered else None


def _load_image_with_fallback(path: Path) -> Image.Image:
    if path.suffix.lower() == ".png":
        array = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if array is not None:
            rgb = cv2.cvtColor(array, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb)

    try:
        return load_image_path(path)
    except Exception:
        array = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if array is None:
            raise
        rgb = cv2.cvtColor(array, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)


def _parse_workbook(path: Path) -> dict[str, dict[str, object]]:
    metadata: dict[str, dict[str, object]] = {}
    with zipfile.ZipFile(path) as workbook:
        shared_strings = _shared_strings(workbook)
        sheet_names = sorted(
            name
            for name in workbook.namelist()
            if name.startswith("xl/worksheets/") and name.endswith(".xml")
        )
        if not sheet_names:
            return metadata
        sheet_root = ET.fromstring(workbook.read(sheet_names[0]))
        rows = sheet_root.findall(".//a:row", _XLSX_NS)
        headers: list[str] = []
        for row_index, row in enumerate(rows):
            values = [_cell_value(cell, shared_strings) for cell in row.findall("a:c", _XLSX_NS)]
            if row_index == 0:
                headers = [str(value).strip() for value in values]
                continue

            row_data = {header: value for header, value in zip(headers, values) if header}
            subject_number = _parse_float(row_data.get("Number"))
            if subject_number is None:
                continue
            metadata[str(int(subject_number))] = row_data
    return metadata


def _shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []

    root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for string_item in root.findall("a:si", _XLSX_NS):
        value = "".join(node.text or "" for node in string_item.iterfind(".//a:t", _XLSX_NS))
        strings.append(value)
    return strings


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> object:
    value = cell.findtext("a:v", default="", namespaces=_XLSX_NS)
    cell_type = cell.get("t")
    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except Exception:
            return value
    return value
