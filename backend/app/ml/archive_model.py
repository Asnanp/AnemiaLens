from __future__ import annotations

import math
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import cv2
import joblib
import numpy as np
from PIL import Image
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

from app.ml.features import FEATURE_NAMES, extract_eye_features
from app.services.conjunctiva_roi import ConjunctivaRoiExtractor

ARCHIVE_VERSION = "archive-fusion-v2"
ANEMIA_HB_THRESHOLD = 11.5
ARCHIVE_FEATURE_NAMES = FEATURE_NAMES + [
    "source_roi_original",
    "source_segmented",
    "source_forniceal_palpebral",
]
_XLSX_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def sigmoid(value: float) -> float:
    if value >= 0:
        exp_value = math.exp(-value)
        return 1.0 / (1.0 + exp_value)
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def save_archive_model(artifact: dict[str, object], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, target)


def load_archive_model(path: str | Path) -> dict[str, object]:
    return joblib.load(path)


def predict_with_archive_model(
    artifact: dict[str, object],
    feature_map: dict[str, float],
    *,
    source_hint: Literal["roi_original", "palpebral", "forniceal_palpebral"] = "roi_original",
) -> dict[str, float]:
    prepared = prepare_feature_map(feature_map, source_hint=source_hint)
    row = np.asarray([prepared[name] for name in artifact["feature_names"]], dtype=np.float32).reshape(1, -1)

    regressor = artifact["regressor"]
    classifier = artifact["classifier"]
    calibration = artifact["calibration"]

    predicted_hb = float(regressor.predict(row)[0])
    regressor_risk = sigmoid((float(calibration["hb_threshold"]) - predicted_hb) / float(calibration["hb_scale"]))
    classifier_probability = float(classifier.predict_proba(row)[0, 1])

    blend_weight = float(calibration["classifier_weight"])
    blend_signal = (classifier_probability * blend_weight) + (regressor_risk * (1.0 - blend_weight))
    risk = sigmoid((blend_signal - float(calibration["blend_threshold"])) / float(calibration["risk_scale"]))

    regressor_tree_std = float(_regression_tree_std(regressor, row)[0])
    classifier_tree_std = float(_classification_tree_std(classifier, row)[0])
    disagreement = abs(classifier_probability - regressor_risk)
    margin_uncertainty = 1.0 - min(1.0, abs(risk - 0.5) * 2.0)
    regressor_uncertainty = clamp(regressor_tree_std / max(float(calibration["regressor_tree_std_reference"]), 1e-6))
    classifier_uncertainty = clamp(classifier_tree_std / max(float(calibration["classifier_tree_std_reference"]), 1e-6))
    out_of_range_penalty = 0.08 if predicted_hb < 7.0 or predicted_hb > 18.0 else 0.0
    uncertainty = clamp(
        (regressor_uncertainty * 0.32)
        + (classifier_uncertainty * 0.18)
        + (disagreement * 0.22)
        + (margin_uncertainty * 0.18)
        + float(calibration["base_uncertainty"])
        + out_of_range_penalty,
        0.05,
        0.95,
    )

    return {
        "anemia_risk": risk,
        "predicted_hemoglobin": predicted_hb,
        "uncertainty": uncertainty,
        "classifier_probability": classifier_probability,
        "regressor_risk": regressor_risk,
        "blend_signal": blend_signal,
    }


def prepare_feature_map(
    feature_map: dict[str, float],
    *,
    source_hint: Literal["roi_original", "palpebral", "forniceal_palpebral"] = "roi_original",
) -> dict[str, float]:
    prepared = {name: float(feature_map[name]) for name in FEATURE_NAMES}
    prepared["source_roi_original"] = 1.0 if source_hint == "roi_original" else 0.0
    prepared["source_segmented"] = 0.0 if source_hint == "roi_original" else 1.0
    prepared["source_forniceal_palpebral"] = 1.0 if source_hint == "forniceal_palpebral" else 0.0
    return prepared


def train_archive_model(
    dataset_root: str | Path,
    *,
    n_splits: int = 6,
    test_size: float = 0.2,
) -> tuple[dict[str, object], dict[str, object]]:
    subjects = _build_subject_catalog(Path(dataset_root))
    if not subjects:
        raise RuntimeError("No archive dataset records were loaded.")

    candidate_reports: list[dict[str, object]] = []
    selected_candidates: list[dict[str, object]] = []
    for mode in ("roi_primary", "hybrid_dual", "palpebral_primary"):
        samples = _samples_for_mode(subjects, mode)
        if not samples:
            continue
        candidate_report = _evaluate_candidate(samples, mode=mode, n_splits=n_splits, test_size=test_size)
        candidate_reports.append(candidate_report)
        if mode != "palpebral_primary":
            selected_candidates.append(candidate_report)

    if not selected_candidates:
        raise RuntimeError("No deployable training candidate could be built from the archive dataset.")

    selected_report = max(selected_candidates, key=lambda report: float(report["selection_score"]))
    final_samples = _samples_for_mode(subjects, str(selected_report["mode"]))
    final_rows, final_targets, final_labels, final_groups = _rows_from_samples(final_samples)

    calibration_split = _calibration_split(final_labels, final_groups, random_state=2026)
    calibration = _fit_calibration(
        final_rows,
        final_targets,
        final_labels,
        calibration_split["train"],
        calibration_split["calibration"],
        random_state=2026,
    )

    regressor = _build_regressor(random_state=42)
    classifier = _build_classifier(random_state=42)
    regressor.fit(final_rows, final_targets)
    classifier.fit(final_rows, final_labels)

    combined_importance = (
        (np.asarray(regressor.feature_importances_) * 0.45)
        + (np.asarray(classifier.feature_importances_) * 0.55)
    )
    source_counts = dict(Counter(sample["source"] for sample in final_samples))

    artifact = {
        "version": ARCHIVE_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "feature_names": ARCHIVE_FEATURE_NAMES,
        "regressor": regressor,
        "classifier": classifier,
        "inference_source_hint": "roi_original",
        "calibration": calibration,
        "training": {
            "selected_mode": selected_report["mode"],
            "subject_count": len(subjects),
            "record_count": len(final_samples),
            "source_counts": source_counts,
            "candidate_metrics": candidate_reports,
            "metrics": selected_report["metrics"],
            "top_features": _top_features(combined_importance, ARCHIVE_FEATURE_NAMES),
        },
    }

    report = {
        "dataset_name": "Eyes-defy-anemia",
        "record_count": len(final_samples),
        "subject_count": len(subjects),
        "primary_model": ARCHIVE_VERSION,
        "selected_mode": selected_report["mode"],
        "source_counts": source_counts,
        "metrics": selected_report["metrics"],
        "candidate_metrics": candidate_reports,
        "calibration": {
            "classifier_weight": calibration["classifier_weight"],
            "blend_threshold": calibration["blend_threshold"],
            "risk_scale": calibration["risk_scale"],
        },
        "top_features": artifact["training"]["top_features"],
    }
    return artifact, report


def _build_subject_catalog(dataset_root: Path) -> list[dict[str, object]]:
    roi_extractor = ConjunctivaRoiExtractor()
    subjects: list[dict[str, object]] = []

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

            views: dict[str, dict[str, float]] = {}
            original_path = _first_path(subject_dir.glob("*.jpg"))
            if original_path is not None:
                try:
                    original = _load_image_with_fallback(original_path)
                    roi = roi_extractor.extract(original).image
                    views["roi_original"] = prepare_feature_map(
                        extract_eye_features(roi),
                        source_hint="roi_original",
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
                    views["palpebral"] = prepare_feature_map(
                        extract_eye_features(palpebral),
                        source_hint="palpebral",
                    )
                except Exception:
                    pass

            forniceal_palpebral_path = _first_path(subject_dir.glob("*_forniceal_palpebral.png"))
            if forniceal_palpebral_path is not None:
                try:
                    forniceal_palpebral = _load_image_with_fallback(forniceal_palpebral_path)
                    views["forniceal_palpebral"] = prepare_feature_map(
                        extract_eye_features(forniceal_palpebral),
                        source_hint="forniceal_palpebral",
                    )
                except Exception:
                    pass

            if not views:
                continue

            subjects.append(
                {
                    "subject_id": f"{country}-{subject_number}",
                    "country": country,
                    "subject_number": subject_number,
                    "hb": hb,
                    "label": int(hb < ANEMIA_HB_THRESHOLD),
                    "views": views,
                }
            )

    return subjects


def _samples_for_mode(
    subjects: list[dict[str, object]],
    mode: str,
) -> list[dict[str, object]]:
    samples: list[dict[str, object]] = []
    for subject in subjects:
        views = subject["views"]
        if mode == "roi_primary":
            selected_source = _preferred_source(views, ("roi_original", "palpebral", "forniceal_palpebral"))
            if selected_source is None:
                continue
            samples.append(_sample_from_view(subject, views[selected_source], selected_source))
            continue

        if mode == "hybrid_dual":
            segmented_source = _preferred_source(views, ("palpebral", "forniceal_palpebral"))
            if segmented_source is not None:
                samples.append(_sample_from_view(subject, views[segmented_source], segmented_source))
            if "roi_original" in views:
                samples.append(_sample_from_view(subject, views["roi_original"], "roi_original"))
            elif segmented_source is None:
                continue
            continue

        if mode == "palpebral_primary":
            selected_source = _preferred_source(views, ("palpebral", "forniceal_palpebral"))
            if selected_source is None:
                continue
            samples.append(_sample_from_view(subject, views[selected_source], selected_source))
            continue

        raise ValueError(f"Unsupported candidate mode: {mode}")

    return samples


def _sample_from_view(
    subject: dict[str, object],
    feature_map: dict[str, float],
    source: str,
) -> dict[str, object]:
    return {
        "group": subject["subject_id"],
        "label": subject["label"],
        "hb": subject["hb"],
        "source": source,
        "features": feature_map,
    }


def _evaluate_candidate(
    samples: list[dict[str, object]],
    *,
    mode: str,
    n_splits: int,
    test_size: float,
) -> dict[str, object]:
    rows, targets, labels, groups = _rows_from_samples(samples)
    splitter = GroupShuffleSplit(n_splits=n_splits, test_size=test_size, random_state=42)
    split_metrics: list[dict[str, float]] = []
    hb_scales: list[float] = []
    regressor_tree_refs: list[float] = []
    classifier_tree_refs: list[float] = []
    classifier_weights: list[float] = []
    blend_thresholds: list[float] = []
    risk_scales: list[float] = []
    feature_importances: list[np.ndarray] = []

    for split_index, (train_index, test_index) in enumerate(splitter.split(rows, labels, groups)):
        calibration_split = _calibration_split(labels[train_index], groups[train_index], random_state=4200 + split_index)
        calibration = _fit_calibration(
            rows[train_index],
            targets[train_index],
            labels[train_index],
            calibration_split["train"],
            calibration_split["calibration"],
            random_state=4200 + split_index,
        )

        train_rows = rows[train_index][calibration_split["train"]]
        train_targets = targets[train_index][calibration_split["train"]]
        train_labels = labels[train_index][calibration_split["train"]]
        test_rows = rows[test_index]
        test_targets = targets[test_index]
        test_labels = labels[test_index]

        regressor = _build_regressor(random_state=4200 + split_index)
        classifier = _build_classifier(random_state=5200 + split_index)
        regressor.fit(train_rows, train_targets)
        classifier.fit(train_rows, train_labels)

        regressor_predictions = regressor.predict(test_rows)
        regressor_risk = np.asarray(
            [sigmoid((ANEMIA_HB_THRESHOLD - prediction) / calibration["hb_scale"]) for prediction in regressor_predictions],
            dtype=np.float32,
        )
        classifier_probability = classifier.predict_proba(test_rows)[:, 1]
        blend_signal = (
            classifier_probability * calibration["classifier_weight"]
            + regressor_risk * (1.0 - calibration["classifier_weight"])
        )
        screening_risk = np.asarray(
            [sigmoid((value - calibration["blend_threshold"]) / calibration["risk_scale"]) for value in blend_signal],
            dtype=np.float32,
        )
        predicted_labels = (screening_risk >= 0.5).astype(np.int32)

        split_metrics.append(
            {
                "accuracy": float(accuracy_score(test_labels, predicted_labels)),
                "precision": float(precision_score(test_labels, predicted_labels, zero_division=0)),
                "recall": float(recall_score(test_labels, predicted_labels, zero_division=0)),
                "f1": float(f1_score(test_labels, predicted_labels, zero_division=0)),
                "auc": float(roc_auc_score(test_labels, screening_risk)),
                "mae_hb": float(mean_absolute_error(test_targets, regressor_predictions)),
            }
        )
        hb_scales.append(float(calibration["hb_scale"]))
        regressor_tree_refs.append(float(calibration["regressor_tree_std_reference"]))
        classifier_tree_refs.append(float(calibration["classifier_tree_std_reference"]))
        classifier_weights.append(float(calibration["classifier_weight"]))
        blend_thresholds.append(float(calibration["blend_threshold"]))
        risk_scales.append(float(calibration["risk_scale"]))
        feature_importances.append(
            (np.asarray(regressor.feature_importances_) * 0.45)
            + (np.asarray(classifier.feature_importances_) * 0.55)
        )

    averaged_metrics = {
        name: round(float(np.mean([metric[name] for metric in split_metrics])), 4)
        for name in ("accuracy", "precision", "recall", "f1", "auc", "mae_hb")
    }
    averaged_metrics["validation_size"] = int(round(len(samples) * test_size))
    averaged_metrics["split_strategy"] = "group-shuffle-repeat"
    averaged_metrics["sample_count"] = len(samples)
    averaged_metrics["subject_count"] = len(set(groups))

    source_counts = dict(Counter(str(sample["source"]) for sample in samples))
    averaged_feature_importances = np.mean(feature_importances, axis=0)
    mae_score = clamp(1.0 - (averaged_metrics["mae_hb"] / 2.8))
    deployment_bonus = 0.04 if mode in {"roi_primary", "hybrid_dual"} else 0.0
    selection_score = round(
        (averaged_metrics["f1"] * 0.34)
        + (averaged_metrics["recall"] * 0.24)
        + (averaged_metrics["auc"] * 0.22)
        + (averaged_metrics["accuracy"] * 0.08)
        + (mae_score * 0.12)
        + deployment_bonus,
        4,
    )

    return {
        "mode": mode,
        "selection_score": selection_score,
        "source_counts": source_counts,
        "metrics": averaged_metrics,
        "calibration": {
            "hb_scale": round(float(np.mean(hb_scales)), 4),
            "regressor_tree_std_reference": round(float(np.mean(regressor_tree_refs)), 4),
            "classifier_tree_std_reference": round(float(np.mean(classifier_tree_refs)), 4),
            "classifier_weight": round(float(np.mean(classifier_weights)), 4),
            "blend_threshold": round(float(np.mean(blend_thresholds)), 4),
            "risk_scale": round(float(np.mean(risk_scales)), 4),
            "base_uncertainty": round(clamp((averaged_metrics["mae_hb"] / 4.8) + 0.02, 0.05, 0.2), 4),
        },
        "top_features": _top_features(averaged_feature_importances, ARCHIVE_FEATURE_NAMES),
    }


def _fit_calibration(
    rows: np.ndarray,
    targets: np.ndarray,
    labels: np.ndarray,
    train_index: np.ndarray,
    calibration_index: np.ndarray,
    *,
    random_state: int,
) -> dict[str, float]:
    train_rows = rows[train_index]
    train_targets = targets[train_index]
    train_labels = labels[train_index]
    calibration_rows = rows[calibration_index]
    calibration_targets = targets[calibration_index]
    calibration_labels = labels[calibration_index]

    regressor = _build_regressor(random_state=random_state)
    classifier = _build_classifier(random_state=random_state)
    regressor.fit(train_rows, train_targets)
    classifier.fit(train_rows, train_labels)

    train_predictions = regressor.predict(train_rows)
    hb_scale = _calibrate_hb_scale(train_targets, train_predictions)
    calibration_predictions = regressor.predict(calibration_rows)
    regressor_risk = np.asarray(
        [sigmoid((ANEMIA_HB_THRESHOLD - prediction) / hb_scale) for prediction in calibration_predictions],
        dtype=np.float32,
    )
    classifier_probability = classifier.predict_proba(calibration_rows)[:, 1]
    fusion = _choose_fusion_config(calibration_labels, classifier_probability, regressor_risk)

    blend_signal = (
        classifier_probability * fusion["classifier_weight"]
        + regressor_risk * (1.0 - fusion["classifier_weight"])
    )
    risk_scale = _calibrate_risk_scale(blend_signal)
    regressor_tree_std_reference = float(np.quantile(_regression_tree_std(regressor, calibration_rows), 0.9))
    classifier_tree_std_reference = float(np.quantile(_classification_tree_std(classifier, calibration_rows), 0.9))
    _ = calibration_targets

    return {
        "hb_threshold": ANEMIA_HB_THRESHOLD,
        "hb_scale": hb_scale,
        "regressor_tree_std_reference": max(regressor_tree_std_reference, 0.18),
        "classifier_tree_std_reference": max(classifier_tree_std_reference, 0.08),
        "classifier_weight": fusion["classifier_weight"],
        "blend_threshold": fusion["blend_threshold"],
        "risk_scale": risk_scale,
        "base_uncertainty": 0.11,
    }


def _choose_fusion_config(
    labels: np.ndarray,
    classifier_probability: np.ndarray,
    regressor_risk: np.ndarray,
) -> dict[str, float]:
    if len(np.unique(labels)) < 2:
        return {"classifier_weight": 0.65, "blend_threshold": 0.4}

    best: dict[str, float] | None = None
    for classifier_weight in np.linspace(0.5, 0.75, 6):
        blend_signal = (
            classifier_probability * classifier_weight
            + regressor_risk * (1.0 - classifier_weight)
        )
        for blend_threshold in np.linspace(0.32, 0.58, 27):
            predicted = (blend_signal >= blend_threshold).astype(np.int32)
            precision = float(precision_score(labels, predicted, zero_division=0))
            recall = float(recall_score(labels, predicted, zero_division=0))
            f1 = float(f1_score(labels, predicted, zero_division=0))
            score = (f1 * 0.6) + (recall * 0.25) + (precision * 0.15)
            candidate = {
                "classifier_weight": float(round(classifier_weight, 4)),
                "blend_threshold": float(round(blend_threshold, 4)),
                "score": float(score),
            }
            if best is None or candidate["score"] > best["score"]:
                best = candidate

    assert best is not None
    return {
        "classifier_weight": best["classifier_weight"],
        "blend_threshold": best["blend_threshold"],
    }


def _rows_from_samples(
    samples: list[dict[str, object]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rows = np.asarray(
        [[float(sample["features"][name]) for name in ARCHIVE_FEATURE_NAMES] for sample in samples],
        dtype=np.float32,
    )
    targets = np.asarray([float(sample["hb"]) for sample in samples], dtype=np.float32)
    labels = np.asarray([int(sample["label"]) for sample in samples], dtype=np.int32)
    groups = np.asarray([str(sample["group"]) for sample in samples], dtype=object)
    return rows, targets, labels, groups


def _build_regressor(*, random_state: int) -> ExtraTreesRegressor:
    return ExtraTreesRegressor(
        n_estimators=320,
        min_samples_leaf=2,
        random_state=random_state,
        n_jobs=-1,
    )


def _build_classifier(*, random_state: int) -> ExtraTreesClassifier:
    return ExtraTreesClassifier(
        n_estimators=500,
        min_samples_leaf=2,
        random_state=random_state,
        class_weight="balanced_subsample",
        n_jobs=-1,
    )


def _regression_tree_std(regressor: ExtraTreesRegressor, rows: np.ndarray) -> np.ndarray:
    tree_predictions = np.asarray([tree.predict(rows) for tree in regressor.estimators_], dtype=np.float32)
    return np.std(tree_predictions, axis=0)


def _classification_tree_std(classifier: ExtraTreesClassifier, rows: np.ndarray) -> np.ndarray:
    tree_probabilities = np.asarray(
        [tree.predict_proba(rows)[:, 1] for tree in classifier.estimators_],
        dtype=np.float32,
    )
    return np.std(tree_probabilities, axis=0)


def _calibrate_hb_scale(targets: np.ndarray, predictions: np.ndarray) -> float:
    residuals = np.abs(targets - predictions)
    upper_quartile = float(np.quantile(residuals, 0.75)) if residuals.size else 0.8
    return max(upper_quartile, 0.8)


def _calibrate_risk_scale(blend_signal: np.ndarray) -> float:
    spread = float(np.std(blend_signal)) if blend_signal.size else 0.1
    return clamp(spread * 0.9, 0.08, 0.18)


def _calibration_split(
    labels: np.ndarray,
    groups: np.ndarray,
    *,
    random_state: int,
) -> dict[str, np.ndarray]:
    splitter = GroupShuffleSplit(n_splits=8, test_size=0.18, random_state=random_state)
    fallback: tuple[np.ndarray, np.ndarray] | None = None

    for train_index, calibration_index in splitter.split(np.zeros(len(labels)), labels, groups):
        if fallback is None:
            fallback = (train_index, calibration_index)
        if len(np.unique(labels[calibration_index])) >= 2 and len(np.unique(labels[train_index])) >= 2:
            return {"train": train_index, "calibration": calibration_index}

    if fallback is None:
        raise RuntimeError("Unable to create a calibration split for the archive model.")

    train_index, calibration_index = fallback
    return {"train": train_index, "calibration": calibration_index}


def _top_features(importances: np.ndarray, feature_names: list[str], limit: int = 8) -> list[dict[str, object]]:
    ranked = sorted(
        zip(feature_names, importances.tolist()),
        key=lambda item: item[1],
        reverse=True,
    )
    return [
        {"name": name, "importance": round(float(importance), 4)}
        for name, importance in ranked[:limit]
    ]


def _preferred_source(
    views: dict[str, dict[str, float]],
    order: tuple[str, ...],
) -> str | None:
    for key in order:
        if key in views:
            return key
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
        with Image.open(path) as image:
            return image.convert("RGB")
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


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    value = cell.find("a:v", _XLSX_NS)
    if value is None or value.text is None:
        return ""
    if cell.get("t") == "s":
        return shared_strings[int(value.text)]
    return value.text


def _parse_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace(",", ".")
    if not text or text.lower() in {"nan", "none", "null", "_", "-", "--"}:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if match is None:
        return None
    return float(match.group())
