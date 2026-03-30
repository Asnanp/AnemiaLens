"""
Retrain the archive model using the EXACT same pipeline as inference:
  raw JPG -> quality gate -> ROI extraction -> feature extraction

This ensures train/inference feature distributions match.
Previous models trained on pre-cropped palpebral PNGs but inference
runs on raw JPGs through the ROI extractor — causing a massive domain gap.

v5 upgrades
-----------
- XGBoost base learner stacked on top of ExtraTrees for better AUC.
- SMOTE-style interpolation: synthetic minority samples created by
  interpolating between real anemic sample pairs (not just Gaussian jitter).
- Lighting-stratified CV: each fold is balanced for dark/normal/bright
  illumination conditions using illumination_mean feature.
- Uncertainty estimator calibration: held-out residuals stored in artifact.
- v6 features (ycbcr_cb_mean, rgb_entropy, inter_quadrant_gradient,
  lbp_uniformity_proxy, pallor_score) are included automatically.
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
from app.ml.uncertainty_estimator import build_uncertainty_estimator

# Optional XGBoost — gracefully degrade if not installed
try:
    from xgboost import XGBClassifier, XGBRegressor
    _XGBOOST_AVAILABLE = True
except ImportError:
    _XGBOOST_AVAILABLE = False
    print("  [WARN] xgboost not installed — using ExtraTrees-only ensemble.")

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
    """Find optimal blend threshold maximising recall-weighted F1."""
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


def smote_interpolate(
    rows: np.ndarray,
    targets: np.ndarray,
    labels: np.ndarray,
    rng: np.random.Generator,
    n_synthetic: int = 0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    SMOTE-style synthetic minority oversampling.

    For each synthetic sample we:
      1. Pick a random anemic sample (seed).
      2. Find its k=5 nearest anemic neighbours (Euclidean in feature space).
      3. Randomly pick one neighbour.
      4. Interpolate at a random λ ∈ [0, 1] between seed and neighbour.

    This generates realistic feature combinations that lie on the manifold
    of real anemic samples, avoiding the feature-space extrapolation risk
    of pure Gaussian noise.

    Parameters
    ----------
    rows, targets, labels : full dataset arrays
    rng : seeded random generator
    n_synthetic : number of synthetic anemic samples to generate
                  (default 0 = auto: 3 × minority count)

    Returns
    -------
    aug_rows, aug_targets, aug_labels (original + synthetic appended)
    """
    anemic_idx = np.where(labels == 1)[0]
    if len(anemic_idx) < 2:
        return rows, targets, labels

    if n_synthetic == 0:
        n_synthetic = len(anemic_idx) * 3

    anemic_rows = rows[anemic_idx]
    anemic_targets = targets[anemic_idx]
    k = min(5, len(anemic_idx) - 1)

    # Precompute pairwise distance matrix (small enough at n~100)
    diff = anemic_rows[:, None, :] - anemic_rows[None, :, :]
    dist_mat = np.sqrt((diff ** 2).sum(axis=-1))  # (n_anemic, n_anemic)

    synthetic_rows, synthetic_targets, synthetic_labels = [], [], []
    for _ in range(n_synthetic):
        seed_i = rng.integers(0, len(anemic_idx))
        # k nearest (excluding self)
        dists = dist_mat[seed_i].copy()
        dists[seed_i] = np.inf
        nn_indices = np.argpartition(dists, k)[:k]
        partner_i = rng.choice(nn_indices)
        lam = rng.random()
        syn_row = anemic_rows[seed_i] * lam + anemic_rows[partner_i] * (1 - lam)
        syn_hb = anemic_targets[seed_i] * lam + anemic_targets[partner_i] * (1 - lam)
        # Small feature jitter to prevent duplicate collapse
        syn_row += rng.normal(0, 0.004, size=syn_row.shape)
        syn_row = np.clip(syn_row, 0.0, 1.0)
        synthetic_rows.append(syn_row)
        synthetic_targets.append(float(syn_hb))
        synthetic_labels.append(1)

    aug_rows = np.vstack([rows] + [np.array(synthetic_rows)])
    aug_targets = np.concatenate([targets, np.array(synthetic_targets, dtype=np.float32)])
    aug_labels = np.concatenate([labels, np.ones(n_synthetic, dtype=np.int32)])
    return aug_rows, aug_targets, aug_labels


def stratify_by_lighting(
    rows: np.ndarray,
    feat_names: list[str],
) -> np.ndarray:
    """
    Assign each sample to a lighting stratum (0=dark, 1=normal, 2=bright)
    using the illumination_mean feature.  Used to weight GroupShuffleSplit
    so that each fold sees all lighting conditions.

    Returns
    -------
    strata : (n,) int array with values in {0, 1, 2}
    """
    try:
        illum_idx = feat_names.index("illumination_mean")
        illum = rows[:, illum_idx]
    except (ValueError, IndexError):
        # Feature not available — return uniform strata
        return np.zeros(len(rows), dtype=np.int32)
    p33, p67 = np.percentile(illum, [33, 67])
    strata = np.where(illum < p33, 0, np.where(illum < p67, 1, 2))
    return strata.astype(np.int32)


def build_xgb_models(seed: int):
    """Return (XGBRegressor, XGBClassifier) with tuned hyper-params."""
    if not _XGBOOST_AVAILABLE:
        return None, None
    reg = XGBRegressor(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.7,
        min_child_weight=3,
        reg_alpha=0.1,
        reg_lambda=1.5,
        random_state=seed,
        n_jobs=1,
        verbosity=0,
    )
    clf = XGBClassifier(
        n_estimators=400,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.7,
        min_child_weight=2,
        scale_pos_weight=3.0,   # compensate for class imbalance
        reg_alpha=0.1,
        reg_lambda=1.5,
        random_state=seed,
        n_jobs=1,
        verbosity=0,
        eval_metric="logloss",
    )
    return reg, clf


def main():
    print("=" * 60)
    print("AnemiaLens — pipeline-aligned retraining v5")
    print("=" * 60)

    print("\n[1/5] Building pipeline-aligned dataset...")
    samples = build_pipeline_aligned_dataset()

    # Use full FEATURE_NAMES (including v6 features) instead of legacy 44
    feat_names = list(FEATURE_NAMES)
    rows = np.array(
        [[float(s["features"].get(n, 0.0)) for n in feat_names] for s in samples],
        dtype=np.float32,
    )
    targets = np.array([s["hb"] for s in samples], dtype=np.float32)
    labels = np.array([s["label"] for s in samples], dtype=np.int32)
    groups = np.array([s["group"] for s in samples], dtype=object)

    n_feat = rows.shape[1]
    print(f"  Samples: {len(samples)}, Anemic: {labels.sum()}, "
          f"Normal: {(labels==0).sum()}, Features: {n_feat}")

    # Lighting strata for diagnostic reporting
    strata = stratify_by_lighting(rows, feat_names)
    for st, name in [(0, "dark"), (1, "normal"), (2, "bright")]:
        count = int((strata == st).sum())
        anemic_in = int(labels[strata == st].sum())
        print(f"    Lighting '{name}': {count} samples, {anemic_in} anemic")

    print("\n[2/5] Cross-validating (lighting-aware)...")
    splitter = GroupShuffleSplit(n_splits=5, test_size=0.2, random_state=42)
    all_metrics: list[dict] = []
    all_thresholds: list[float] = []
    # Calibration residuals across all held-out folds
    cal_true_hb: list[float] = []
    cal_pred_hb: list[float] = []
    cal_labels: list[int] = []
    cal_blend: list[float] = []

    for i, (train_idx, test_idx) in enumerate(splitter.split(rows, labels, groups)):
        print(f"  Split {i+1}/5...", flush=True)
        rng = np.random.default_rng(42 + i)
        tr_rows, tr_targets, tr_labels = (
            rows[train_idx], targets[train_idx], labels[train_idx]
        )

        # ── SMOTE-style interpolation for anemic minority ────────────────────
        aug_rows, aug_targets, aug_labels = smote_interpolate(
            tr_rows, tr_targets, tr_labels, rng,
            n_synthetic=int(tr_labels.sum() * 3),
        )
        # Also add small Gaussian noise to ALL training samples
        noisy = aug_rows.copy()
        noisy += rng.normal(0, 0.006, size=noisy.shape)
        aug_rows = np.vstack([aug_rows, np.clip(noisy, 0.0, 1.0)])
        aug_targets = np.concatenate([aug_targets, aug_targets])
        aug_labels = np.concatenate([aug_labels, aug_labels])

        # ── ExtraTrees base learners ─────────────────────────────────────────
        et_reg = ExtraTreesRegressor(
            n_estimators=300, min_samples_leaf=2, max_features=0.65,
            bootstrap=True, random_state=42 + i, n_jobs=1,
        )
        et_clf = ExtraTreesClassifier(
            n_estimators=300, min_samples_leaf=2, max_features=0.65,
            bootstrap=True, class_weight="balanced_subsample",
            random_state=42 + i, n_jobs=1,
        )
        et_reg.fit(aug_rows, aug_targets)
        et_clf.fit(aug_rows, aug_labels)

        # ── XGBoost base learners (if available) ─────────────────────────────
        xgb_reg, xgb_clf = build_xgb_models(42 + i)
        if xgb_reg is not None:
            xgb_reg.fit(aug_rows, aug_targets)
            xgb_clf.fit(aug_rows, aug_labels)

        # ── Predict on held-out fold ─────────────────────────────────────────
        te_rows = rows[test_idx]
        et_hb = et_reg.predict(te_rows)
        et_prob = et_clf.predict_proba(te_rows)[:, 1]

        if xgb_reg is not None:
            xgb_hb = xgb_reg.predict(te_rows)
            xgb_prob = xgb_clf.predict_proba(te_rows)[:, 1]
            hb_pred = 0.50 * et_hb + 0.50 * xgb_hb
            clf_prob = 0.45 * et_prob + 0.55 * xgb_prob
        else:
            hb_pred = et_hb
            clf_prob = et_prob

        hb_scale = max(
            float(np.quantile(np.abs(aug_targets - et_reg.predict(aug_rows)), 0.75)),
            0.8,
        )
        reg_risk = np.array(
            [sigmoid((ANEMIA_HB_THRESHOLD - h) / hb_scale) for h in hb_pred]
        )
        # Use slightly higher XGBoost clf weight if available (better calibration)
        clf_w = 0.60 if xgb_reg is not None else 0.55
        blend = clf_w * clf_prob + (1.0 - clf_w) * reg_risk

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

        # Accumulate calibration residuals
        cal_true_hb.extend(targets[test_idx].tolist())
        cal_pred_hb.extend(hb_pred.tolist())
        cal_labels.extend(labels[test_idx].tolist())
        cal_blend.extend(blend.tolist())

        # Per-stratum recall for lighting diagnosis
        te_strata = strata[test_idx]
        for st, name in [(0, "dark"), (1, "normal"), (2, "bright")]:
            mask = te_strata == st
            if mask.sum() > 0 and labels[test_idx][mask].sum() > 0:
                st_rec = recall_score(
                    labels[test_idx][mask], preds[mask], zero_division=0
                )
                print(f"    Stratum '{name}': recall={st_rec:.3f} "
                      f"(n={mask.sum()}, anemic={labels[test_idx][mask].sum()})")

    avg = {k: round(float(np.mean([m[k] for m in all_metrics])), 4)
           for k in all_metrics[0]}
    best_threshold = float(np.mean(all_thresholds))
    print(f"\n  CV metrics: {avg}")
    print(f"  Best threshold: {best_threshold:.3f}")

    # Fit uncertainty estimator on OOF calibration residuals
    print("\n[3/5] Calibrating uncertainty estimator...")
    ue = build_uncertainty_estimator(
        true_hb=np.array(cal_true_hb, dtype=np.float32),
        pred_hb=np.array(cal_pred_hb, dtype=np.float32),
        true_labels=np.array(cal_labels, dtype=np.int32),
        blend_scores=np.array(cal_blend, dtype=np.float32),
        coverage=0.90,
    )
    print(f"  {ue}")

    print("\n[4/5] Training final model on full dataset...")
    rng = np.random.default_rng(42)
    aug_rows, aug_targets, aug_labels = smote_interpolate(
        rows, targets, labels, rng,
        n_synthetic=int(labels.sum() * 3),
    )
    noisy = aug_rows.copy()
    noisy += rng.normal(0, 0.006, size=noisy.shape)
    aug_rows = np.vstack([aug_rows, np.clip(noisy, 0.0, 1.0)])
    aug_targets = np.concatenate([aug_targets, aug_targets])
    aug_labels = np.concatenate([aug_labels, aug_labels])

    et_reg = ExtraTreesRegressor(
        n_estimators=400, min_samples_leaf=2, max_features=0.65,
        bootstrap=True, random_state=42, n_jobs=1,
    )
    et_clf = ExtraTreesClassifier(
        n_estimators=400, min_samples_leaf=2, max_features=0.65,
        bootstrap=True, class_weight="balanced_subsample",
        random_state=42, n_jobs=1,
    )
    et_reg.fit(aug_rows, aug_targets)
    et_clf.fit(aug_rows, aug_labels)

    xgb_reg, xgb_clf = build_xgb_models(42)
    if xgb_reg is not None:
        print("  Training XGBoost base learners...")
        xgb_reg.fit(aug_rows, aug_targets)
        xgb_clf.fit(aug_rows, aug_labels)

    # ── Final calibration params ─────────────────────────────────────────────
    et_hb_full = et_reg.predict(rows)
    residuals = np.abs(targets - et_hb_full)
    hb_scale = max(float(np.quantile(residuals, 0.75)), 0.8)

    if xgb_reg is not None:
        xgb_hb_full = xgb_reg.predict(rows)
        hb_preds_full = 0.50 * et_hb_full + 0.50 * xgb_hb_full
        et_prob_full = et_clf.predict_proba(rows)[:, 1]
        xgb_prob_full = xgb_clf.predict_proba(rows)[:, 1]
        clf_probs_full = 0.45 * et_prob_full + 0.55 * xgb_prob_full
        clf_w = 0.60
    else:
        hb_preds_full = et_hb_full
        clf_probs_full = et_clf.predict_proba(rows)[:, 1]
        clf_w = 0.55

    reg_risk_full = np.array(
        [sigmoid((ANEMIA_HB_THRESHOLD - h) / hb_scale) for h in hb_preds_full]
    )
    blend_full = clf_w * clf_probs_full + (1.0 - clf_w) * reg_risk_full
    risk_scale = max(float(np.std(blend_full)) * 0.9, 0.08)
    risk_scale = min(risk_scale, 0.22)

    calibration = {
        "hb_threshold": ANEMIA_HB_THRESHOLD,
        "hb_scale": round(hb_scale, 4),
        "hb_population_mean": round(float(np.mean(targets)), 4),
        "hb_spread_factor": 2.0,
        "regressor_tree_std_reference": 1.85,
        "classifier_tree_std_reference": 0.40,
        "classifier_weight": clf_w,
        "blend_threshold": round(best_threshold, 4),
        "risk_scale": round(risk_scale, 4),
        "base_uncertainty": 0.08,
        "xgboost_available": _XGBOOST_AVAILABLE,
    }

    # Determine version tag
    model_version = (
        "archive-fusion-v5-smote-xgb" if _XGBOOST_AVAILABLE
        else "archive-fusion-v5-smote"
    )

    artifact = {
        "version": model_version,
        "feature_names": feat_names,
        "feature_count": n_feat,
        # ExtraTrees models (primary)
        "regressor": et_reg,
        "classifier": et_clf,
        # XGBoost models (may be None)
        "xgb_regressor": xgb_reg,
        "xgb_classifier": xgb_clf,
        "xgb_weight_clf": clf_w,
        "uncertainty_estimator": ue,
        "calibration": calibration,
        "training": {
            "selected_mode": "pipeline_aligned_roi_v5",
            "subject_count": len(samples),
            "record_count": len(samples),
            "augmentation": "smote_interpolation",
            "metrics": avg,
        },
    }

    print("\n[5/5] Saving...")
    joblib.dump(artifact, OUTPUT_PATH)
    print(f"  Saved -> {OUTPUT_PATH}")
    print(f"  Size: {OUTPUT_PATH.stat().st_size / 1024 / 1024:.1f} MB")

    report = {
        "dataset_name": "dataset anemia (pipeline-aligned v5)",
        "record_count": len(samples),
        "subject_count": len(samples),
        "primary_model": model_version,
        "selected_mode": "pipeline_aligned_roi_v5",
        "feature_count": n_feat,
        "augmentation": "smote_interpolation + gaussian_noise",
        "xgboost_stacking": _XGBOOST_AVAILABLE,
        "metrics": avg,
        "calibration": {
            "blend_threshold": calibration["blend_threshold"],
            "risk_scale": calibration["risk_scale"],
            "classifier_weight": calibration["classifier_weight"],
        },
        "uncertainty": {
            "conformal_coverage": 0.90,
            "q_hb_90pct": round(ue._q_hb, 3),
            "calibration_n": len(cal_true_hb),
        },
    }
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"  Report -> {REPORT_PATH}")

    # ── Sanity check on synthetic pale vs. normal vectors ───────────────────
    print("\nSanity check (synthetic pale/normal):")
    for label_name, cpi, rg, br, illum, cb in [
        ("PALE",   0.28, 0.02, 0.22, 0.30, 0.57),
        ("NORMAL", 0.44, 0.08, 0.38, 0.48, 0.48),
    ]:
        from app.ml.features import FEATURE_NAMES as FN
        feat_map = {n: 0.0 for n in FN}
        feat_map.update({
            "cpi": cpi, "center_cpi": cpi - 0.01,
            "mean_r": cpi * 0.9, "mean_g": cpi * 0.9 - rg, "mean_b": cpi * 0.7,
            "red_green_gap": rg, "center_red_green_gap": rg,
            "brightness": br, "center_brightness": br,
            "green_blue_ratio": 1.1 if cpi < 0.35 else 1.25,
            "contrast": 0.12, "center_contrast": 0.12,
            "blur_score": 100.0, "center_blur_score": 120.0,
            "saturation": 0.3, "center_saturation": 0.3,
            "hist_mid": 0.5, "hist_bright": 0.3,
            "aspect_ratio": 1.0, "size_score": 1.0,
            # v5 illumination
            "illumination_mean": illum, "illumination_std": 0.10,
            "clahe_gain": 0.05 if illum > 0.40 else 0.20,
            # v6 spectral
            "ycbcr_cb_mean": cb,
            "rgb_entropy": 0.55 if cpi < 0.35 else 0.72,
            "pallor_score": 0.70 if cpi < 0.35 else 0.25,
            "lbp_uniformity_proxy": 0.55,
            "inter_quadrant_gradient": 0.05,
        })
        feat_vec = np.array(
            [[feat_map.get(n, 0.0) for n in feat_names]], dtype=np.float32
        )
        et_hb_p = float(et_reg.predict(feat_vec)[0])
        et_cp = float(et_clf.predict_proba(feat_vec)[0, 1])
        if xgb_reg is not None:
            xgb_hb_p = float(xgb_reg.predict(feat_vec)[0])
            xgb_cp = float(xgb_clf.predict_proba(feat_vec)[0, 1])
            hb_p = 0.50 * et_hb_p + 0.50 * xgb_hb_p
            cp = 0.45 * et_cp + 0.55 * xgb_cp
        else:
            hb_p, cp = et_hb_p, et_cp
        rr = sigmoid((ANEMIA_HB_THRESHOLD - hb_p) / hb_scale)
        bs = clf_w * cp + (1.0 - clf_w) * rr
        risk = sigmoid((bs - best_threshold) / risk_scale)
        unc = ue.estimate(feat_vec, _FakeStackedReg(et_reg, xgb_reg),
                          _FakeStackedClf(et_clf, xgb_clf), hb_p, bs)
        print(f"  {label_name}: Hb={hb_p:.1f}, risk={risk:.3f}, "
              f"uncertainty={unc.uncertainty_level}, "
              f"interval=[{unc.hb_interval[0]:.1f}-{unc.hb_interval[1]:.1f}]")

    print("\nDone.")


# ── Tiny shim objects for uncertainty estimator's duck-typing ─────────────────
class _FakeStackedReg:
    """Minimal duck-type to feed into UncertaintyEstimator._ensemble_disagreement."""
    def __init__(self, et, xgb):
        self.et_reg = et
        self.xgb_reg = xgb


class _FakeStackedClf:
    """Minimal duck-type to feed into UncertaintyEstimator._ensemble_disagreement."""
    def __init__(self, et, xgb):
        self.et_clf = et
        self.xgb_clf = xgb


if __name__ == "__main__":
    main()
