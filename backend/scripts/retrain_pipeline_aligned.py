"""
Retrain the archive model using the EXACT same pipeline as inference:
  raw JPG -> quality gate -> ROI extraction -> feature extraction

This ensures train/inference feature distributions match.
Previous models trained on pre-cropped palpebral PNGs but inference
runs on raw JPGs through the ROI extractor — causing a massive domain gap.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

import numpy as np
import joblib
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor
from sklearn.metrics import (
    accuracy_score, f1_score, mean_absolute_error,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit

from app.ml.archive_model import (
    ANEMIA_HB_THRESHOLD, ARCHIVE_FEATURE_NAMES,
    clamp, sigmoid, _parse_workbook, _parse_float, _load_image_with_fallback,
)
from app.ml.features import extract_eye_features, FEATURE_NAMES
from app.services.conjunctiva_roi import ConjunctivaRoiExtractor
from app.services.image_quality import ImageQualityService

DATASET_ROOT = Path(__file__).parents[2] / "archive" / "dataset anemia"
OUTPUT_PATH = Path(__file__).parents[1] / "models" / "archive_screening_model.joblib"
REPORT_PATH = Path(__file__).parents[1] / "models" / "training_report.json"


def build_pipeline_aligned_dataset():
    """
    Load raw JPGs, run through ROI extractor (same as inference),
    extract features. Returns samples with ground-truth Hb.
    """
    roi_extractor = ConjunctivaRoiExtractor()
    samples = []
    skipped = 0

    for country in ("India", "Italy"):
        workbook_path = DATASET_ROOT / country / f"{country}.xlsx"
        metadata = _parse_workbook(workbook_path)

        for subject_number, row in metadata.items():
            hb = _parse_float(row.get("Hgb"))
            if hb is None:
                continue

            subject_dir = DATASET_ROOT / country / subject_number
            if not subject_dir.exists():
                continue

            # Use raw JPG — same as what users upload
            jpgs = sorted(subject_dir.glob("*.jpg"))
            if not jpgs:
                skipped += 1
                continue

            try:
                raw_img = _load_image_with_fallback(jpgs[0])
                roi_result = roi_extractor.extract(raw_img)
                roi_img = roi_result.image
                features = extract_eye_features(roi_img)

                # Add source flags (roi_original path)
                prepared = dict(features)
                prepared["source_roi_original"] = 1.0
                prepared["source_segmented"] = 0.0
                prepared["source_forniceal_palpebral"] = 0.0

                samples.append({
                    "group": f"{country}-{subject_number}",
                    "hb": hb,
                    "label": int(hb < ANEMIA_HB_THRESHOLD),
                    "features": prepared,
                })
            except Exception as e:
                skipped += 1

    print(f"  Loaded {len(samples)} samples, skipped {skipped}")
    return samples


def find_best_threshold(labels, scores):
    best_score, best_thresh = -1.0, 0.5
    for t in np.linspace(0.20, 0.80, 61):
        preds = (scores >= t).astype(int)
        if preds.sum() == 0:
            continue
        f1 = f1_score(labels, preds, zero_division=0)
        rec = recall_score(labels, preds, zero_division=0)
        # Weight recall heavily — medical screening, false negatives are worse
        score = f1 * 0.4 + rec * 0.6
        if score > best_score:
            best_score = score
            best_thresh = float(t)
    return best_thresh


def main():
    print("=" * 60)
    print("AnemiaLens — pipeline-aligned retraining")
    print("=" * 60)

    print("\n[1/4] Building pipeline-aligned dataset...")
    samples = build_pipeline_aligned_dataset()

    feat_names = ARCHIVE_FEATURE_NAMES  # 44 features
    rows = np.array([[float(s["features"].get(n, 0.0)) for n in feat_names] for s in samples], dtype=np.float32)
    targets = np.array([s["hb"] for s in samples], dtype=np.float32)
    labels = np.array([s["label"] for s in samples], dtype=np.int32)
    groups = np.array([s["group"] for s in samples], dtype=object)

    print(f"  Samples: {len(samples)}, Anemic: {labels.sum()}, Normal: {(labels==0).sum()}")

    print("\n[2/4] Cross-validating...")
    splitter = GroupShuffleSplit(n_splits=5, test_size=0.2, random_state=42)
    all_metrics = []
    all_thresholds = []

    for i, (train_idx, test_idx) in enumerate(splitter.split(rows, labels, groups)):
        print(f"  Split {i+1}/5...", flush=True)

        # Augment training: add noise + oversample anemic
        rng = np.random.default_rng(42 + i)
        tr_rows, tr_targets, tr_labels = rows[train_idx], targets[train_idx], labels[train_idx]

        # Gaussian noise on all samples
        noisy = tr_rows.copy()
        noisy += rng.normal(0, 0.008, size=noisy.shape)
        noisy = np.clip(noisy, 0.0, 1.0)

        # 3x oversample anemic
        anemic_idx = np.where(tr_labels == 1)[0]
        copies_list = [tr_rows, noisy]
        t_list = [tr_targets, tr_targets]
        l_list = [tr_labels, tr_labels]
        for _ in range(3):
            copies = tr_rows[anemic_idx].copy()
            copies += rng.normal(0, 0.01, size=copies.shape)
            copies = np.clip(copies, 0.0, 1.0)
            copies_list.append(copies)
            t_list.append(tr_targets[anemic_idx])
            l_list.append(tr_labels[anemic_idx])

        aug_rows = np.vstack(copies_list)
        aug_targets = np.concatenate(t_list)
        aug_labels = np.concatenate(l_list)

        reg = ExtraTreesRegressor(n_estimators=300, min_samples_leaf=2, max_features=0.7,
                                   bootstrap=True, random_state=42+i, n_jobs=1)
        clf = ExtraTreesClassifier(n_estimators=300, min_samples_leaf=2, max_features=0.7,
                                    bootstrap=True, class_weight="balanced_subsample",
                                    random_state=42+i, n_jobs=1)
        reg.fit(aug_rows, aug_targets)
        clf.fit(aug_rows, aug_labels)

        hb_pred = reg.predict(rows[test_idx])
        clf_prob = clf.predict_proba(rows[test_idx])[:, 1]

        hb_scale = max(float(np.quantile(np.abs(aug_targets - reg.predict(aug_rows)), 0.75)), 0.8)
        reg_risk = np.array([sigmoid((ANEMIA_HB_THRESHOLD - h) / hb_scale) for h in hb_pred])
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
        })
        all_thresholds.append(thresh)

    avg = {k: round(float(np.mean([m[k] for m in all_metrics])), 4) for k in all_metrics[0]}
    best_threshold = float(np.mean(all_thresholds))
    print(f"\n  CV metrics: {avg}")
    print(f"  Best threshold: {best_threshold:.3f}")

    print("\n[3/4] Training final model on full dataset...")
    rng = np.random.default_rng(42)
    noisy = rows.copy()
    noisy += rng.normal(0, 0.008, size=noisy.shape)
    noisy = np.clip(noisy, 0.0, 1.0)
    anemic_idx = np.where(labels == 1)[0]
    copies_list = [rows, noisy]
    t_list = [targets, targets]
    l_list = [labels, labels]
    for _ in range(3):
        copies = rows[anemic_idx].copy()
        copies += rng.normal(0, 0.01, size=copies.shape)
        copies = np.clip(copies, 0.0, 1.0)
        copies_list.append(copies)
        t_list.append(targets[anemic_idx])
        l_list.append(labels[anemic_idx])
    aug_rows = np.vstack(copies_list)
    aug_targets = np.concatenate(t_list)
    aug_labels = np.concatenate(l_list)

    reg = ExtraTreesRegressor(n_estimators=300, min_samples_leaf=2, max_features=0.7,
                               bootstrap=True, random_state=42, n_jobs=1)
    clf = ExtraTreesClassifier(n_estimators=300, min_samples_leaf=2, max_features=0.7,
                                bootstrap=True, class_weight="balanced_subsample",
                                random_state=42, n_jobs=1)
    reg.fit(aug_rows, aug_targets)
    clf.fit(aug_rows, aug_labels)

    hb_preds_full = reg.predict(rows)
    residuals = np.abs(targets - hb_preds_full)
    hb_scale = max(float(np.quantile(residuals, 0.75)), 0.8)
    clf_probs_full = clf.predict_proba(rows)[:, 1]
    reg_risk_full = np.array([sigmoid((ANEMIA_HB_THRESHOLD - h) / hb_scale) for h in hb_preds_full])
    blend_full = 0.55 * clf_probs_full + 0.45 * reg_risk_full
    risk_scale = max(float(np.std(blend_full)) * 0.9, 0.08)
    risk_scale = min(risk_scale, 0.22)

    calibration = {
        "hb_threshold": ANEMIA_HB_THRESHOLD,
        "hb_scale": round(hb_scale, 4),
        "hb_population_mean": round(float(np.mean(targets)), 4),
        "hb_spread_factor": 2.0,
        "regressor_tree_std_reference": 1.85,
        "classifier_tree_std_reference": 0.40,
        "classifier_weight": 0.55,
        "blend_threshold": round(best_threshold, 4),
        "risk_scale": round(risk_scale, 4),
        "base_uncertainty": 0.08,
    }

    artifact = {
        "version": "archive-fusion-v4-pipeline",
        "feature_names": feat_names,
        "regressor": reg,
        "classifier": clf,
        "calibration": calibration,
        "training": {
            "selected_mode": "pipeline_aligned_roi",
            "subject_count": len(samples),
            "record_count": len(samples),
            "metrics": avg,
        },
    }

    print("\n[4/4] Saving...")
    joblib.dump(artifact, OUTPUT_PATH)
    print(f"  Saved -> {OUTPUT_PATH}")
    print(f"  Size: {OUTPUT_PATH.stat().st_size / 1024 / 1024:.1f} MB")

    report = {
        "dataset_name": "dataset anemia (pipeline-aligned)",
        "record_count": len(samples),
        "subject_count": len(samples),
        "primary_model": "archive-fusion-v4-pipeline",
        "selected_mode": "pipeline_aligned_roi",
        "metrics": avg,
        "calibration": {
            "blend_threshold": calibration["blend_threshold"],
            "risk_scale": calibration["risk_scale"],
            "classifier_weight": calibration["classifier_weight"],
        },
    }
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)

    # Sanity check on training data
    print("\nSanity check (training data):")
    for label, cpi, rg, br in [("PALE", 0.28, 0.02, 0.22), ("NORMAL", 0.44, 0.08, 0.38)]:
        from app.ml.archive_model import prepare_feature_map
        from app.ml.features import FEATURE_NAMES as FN
        feat_map = {n: 0.0 for n in FN}
        feat_map.update({"cpi": cpi, "center_cpi": cpi-0.01, "mean_r": cpi*0.9,
                         "mean_g": cpi*0.9-rg, "mean_b": cpi*0.7,
                         "red_green_gap": rg, "center_red_green_gap": rg,
                         "brightness": br, "center_brightness": br,
                         "green_blue_ratio": 1.1 if cpi < 0.35 else 1.25,
                         "contrast": 0.12, "center_contrast": 0.12,
                         "blur_score": 100.0, "center_blur_score": 120.0,
                         "saturation": 0.3, "center_saturation": 0.3,
                         "hist_mid": 0.5, "hist_bright": 0.3,
                         "aspect_ratio": 1.0, "size_score": 1.0})
        prepared = prepare_feature_map(feat_map, source_hint="roi_original")
        row = np.array([[prepared.get(n, 0.0) for n in feat_names]], dtype=np.float32)
        hb_p = float(reg.predict(row)[0])
        cp = float(clf.predict_proba(row)[0, 1])
        rr = sigmoid((ANEMIA_HB_THRESHOLD - hb_p) / hb_scale)
        bs = 0.55 * cp + 0.45 * rr
        risk = sigmoid((bs - best_threshold) / risk_scale)
        print(f"  {label}: Hb={hb_p:.1f}, risk={risk:.3f}")

    print("\nDone.")


if __name__ == "__main__":
    main()
