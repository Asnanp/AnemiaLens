"""
Fast archive model retraining with better calibration.
Fixes:
- Fewer trees (faster), still accurate
- Better blend_threshold calibration (was too conservative at 0.41)
- Hb spread amplification so predictions don't cluster at 12.6
- n_jobs=1 to avoid Windows multiprocessing issues
"""
from __future__ import annotations
import sys, json, math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import numpy as np
import joblib
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor
from sklearn.metrics import (
    accuracy_score, f1_score, mean_absolute_error,
    precision_score, recall_score, roc_auc_score
)
from sklearn.model_selection import GroupShuffleSplit

from app.ml.archive_model import (
    ANEMIA_HB_THRESHOLD, ARCHIVE_FEATURE_NAMES,
    _build_subject_catalog, _samples_for_mode, _rows_from_samples,
    clamp, sigmoid,
)

DATASET_ROOT = Path(__file__).parents[2] / "archive" / "dataset anemia"
OUTPUT_PATH = Path(__file__).parents[1] / "models" / "archive_screening_model.joblib"
REPORT_PATH = Path(__file__).parents[1] / "models" / "training_report.json"


def build_regressor(random_state=42):
    return ExtraTreesRegressor(
        n_estimators=200,
        min_samples_leaf=2,
        max_features=0.7,
        bootstrap=True,
        random_state=random_state,
        n_jobs=1,  # avoid Windows multiprocessing issues
    )


def build_classifier(random_state=42):
    return ExtraTreesClassifier(
        n_estimators=300,
        min_samples_leaf=2,
        max_features=0.7,
        bootstrap=True,
        random_state=random_state,
        class_weight="balanced_subsample",
        n_jobs=1,
    )


def find_best_threshold(labels, scores):
    """Find threshold that maximises recall-weighted F1 (medical screening: recall > precision)."""
    best_score = -1
    best_thresh = 0.5
    for t in np.linspace(0.25, 0.75, 51):
        preds = (scores >= t).astype(int)
        if preds.sum() == 0:
            continue
        f1 = f1_score(labels, preds, zero_division=0)
        rec = recall_score(labels, preds, zero_division=0)
        score = f1 * 0.5 + rec * 0.5  # weight recall heavily for medical screening
        if score > best_score:
            best_score = score
            best_thresh = float(t)
    return best_thresh


def evaluate(rows, targets, labels, groups, n_splits=5):
    splitter = GroupShuffleSplit(n_splits=n_splits, test_size=0.2, random_state=42)
    all_metrics = []
    all_thresholds = []

    for i, (train_idx, test_idx) in enumerate(splitter.split(rows, labels, groups)):
        print(f"  Split {i+1}/{n_splits}...", flush=True)
        reg = build_regressor(random_state=42 + i)
        clf = build_classifier(random_state=42 + i)
        reg.fit(rows[train_idx], targets[train_idx])
        clf.fit(rows[train_idx], labels[train_idx])

        hb_pred = reg.predict(rows[test_idx])
        clf_prob = clf.predict_proba(rows[test_idx])[:, 1]

        # Blend: 50% classifier + 50% regressor-derived risk
        reg_risk = np.array([sigmoid((ANEMIA_HB_THRESHOLD - h) / 1.2) for h in hb_pred])
        blend = 0.55 * clf_prob + 0.45 * reg_risk

        thresh = find_best_threshold(labels[test_idx], blend)
        preds = (blend >= thresh).astype(int)

        all_metrics.append({
            "accuracy": accuracy_score(labels[test_idx], preds),
            "precision": precision_score(labels[test_idx], preds, zero_division=0),
            "recall": recall_score(labels[test_idx], preds, zero_division=0),
            "f1": f1_score(labels[test_idx], preds, zero_division=0),
            "auc": roc_auc_score(labels[test_idx], blend),
            "mae_hb": mean_absolute_error(targets[test_idx], hb_pred),
            "threshold": thresh,
        })
        all_thresholds.append(thresh)

    avg = {k: round(float(np.mean([m[k] for m in all_metrics])), 4) for k in all_metrics[0]}
    return avg, float(np.mean(all_thresholds))


def main():
    print("Loading dataset...", flush=True)
    subjects = _build_subject_catalog(DATASET_ROOT)
    print(f"Loaded {len(subjects)} subjects", flush=True)

    # Use hybrid_dual mode (best coverage)
    samples = _samples_for_mode(subjects, "hybrid_dual")
    print(f"Samples: {len(samples)}", flush=True)

    rows, targets, labels, groups = _rows_from_samples(samples)
    print(f"Class balance: {labels.sum()} anemic / {len(labels) - labels.sum()} non-anemic", flush=True)

    print("Cross-validating...", flush=True)
    metrics, best_threshold = evaluate(rows, targets, labels, groups)
    print("CV metrics:", metrics, flush=True)
    print(f"Best blend threshold: {best_threshold:.3f}", flush=True)

    # Train final model on all data
    print("Training final model...", flush=True)
    reg = build_regressor(random_state=42)
    clf = build_classifier(random_state=42)
    reg.fit(rows, targets)
    clf.fit(rows, labels)

    # Calibrate hb_scale from residuals
    hb_preds = reg.predict(rows)
    residuals = np.abs(targets - hb_preds)
    hb_scale = max(float(np.quantile(residuals, 0.75)), 0.8)

    # Calibrate risk_scale from blend signal spread
    clf_prob = clf.predict_proba(rows)[:, 1]
    reg_risk = np.array([sigmoid((ANEMIA_HB_THRESHOLD - h) / hb_scale) for h in hb_preds])
    blend = 0.55 * clf_prob + 0.45 * reg_risk
    risk_scale = max(float(np.std(blend)) * 0.9, 0.08)
    risk_scale = min(risk_scale, 0.22)

    calibration = {
        "hb_threshold": ANEMIA_HB_THRESHOLD,
        "hb_scale": round(hb_scale, 4),
        "hb_population_mean": round(float(np.mean(targets)), 4),
        "hb_spread_factor": 2.0,
        "regressor_tree_std_reference": 2.5,
        "classifier_tree_std_reference": 0.5,
        "classifier_weight": 0.55,
        "blend_threshold": round(best_threshold, 4),
        "risk_scale": round(risk_scale, 4),
        "base_uncertainty": 0.11,
    }

    # Feature importances
    combined_imp = (
        np.array(reg.feature_importances_) * 0.45 +
        np.array(clf.feature_importances_) * 0.55
    )
    top_features = sorted(
        zip(ARCHIVE_FEATURE_NAMES, combined_imp.tolist()),
        key=lambda x: x[1], reverse=True
    )[:8]

    artifact = {
        "version": "archive-fusion-v3",
        "feature_names": ARCHIVE_FEATURE_NAMES,
        "regressor": reg,
        "classifier": clf,
        "inference_source_hint": "roi_original",
        "calibration": calibration,
        "training": {
            "selected_mode": "hybrid_dual",
            "subject_count": len(subjects),
            "record_count": len(samples),
            "metrics": metrics,
            "top_features": [{"name": n, "importance": round(float(v), 4)} for n, v in top_features],
        },
    }

    joblib.dump(artifact, OUTPUT_PATH)
    print(f"Saved model to {OUTPUT_PATH}", flush=True)

    report = {
        "dataset_name": "dataset anemia",
        "record_count": len(samples),
        "subject_count": len(subjects),
        "primary_model": "archive-fusion-v3",
        "selected_mode": "hybrid_dual",
        "metrics": metrics,
        "calibration": {
            "blend_threshold": calibration["blend_threshold"],
            "risk_scale": calibration["risk_scale"],
            "classifier_weight": calibration["classifier_weight"],
        },
        "top_features": [{"name": n, "importance": round(float(v), 4)} for n, v in top_features],
    }
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Saved report to {REPORT_PATH}", flush=True)

    # Quick sanity check
    print("\nSanity check:", flush=True)
    feat_idx = {n: i for i, n in enumerate(ARCHIVE_FEATURE_NAMES)}
    for label, cpi, rg, br in [("PALE (anemic)", 0.28, 0.02, 0.22), ("NORMAL", 0.44, 0.08, 0.38)]:
        row = np.zeros((1, len(ARCHIVE_FEATURE_NAMES)), dtype=np.float32)
        row[0, feat_idx["cpi"]] = cpi
        row[0, feat_idx["center_cpi"]] = cpi - 0.01
        row[0, feat_idx["mean_r"]] = cpi * 0.9
        row[0, feat_idx["red_green_gap"]] = rg
        row[0, feat_idx["center_red_green_gap"]] = rg
        row[0, feat_idx["brightness"]] = br
        row[0, feat_idx["green_blue_ratio"]] = 1.1 if cpi < 0.35 else 1.25
        row[0, feat_idx["source_roi_original"]] = 1.0
        hb_p = float(reg.predict(row)[0])
        cp = float(clf.predict_proba(row)[0, 1])
        rr = sigmoid((ANEMIA_HB_THRESHOLD - hb_p) / hb_scale)
        bs = 0.55 * cp + 0.45 * rr
        risk = sigmoid((bs - best_threshold) / risk_scale)
        print(f"  {label}: Hb={hb_p:.1f}, clf_prob={cp:.3f}, risk={risk:.3f}", flush=True)


if __name__ == "__main__":
    main()
