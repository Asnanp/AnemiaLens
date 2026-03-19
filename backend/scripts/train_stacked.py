"""
train_stacked.py â€” AnemiaLens stacked-ensemble-v4 training script.

Architecture
------------
Level-0 base learners (out-of-fold predictions via cross_val_predict):
  â€¢ XGBoost regressor   â†’ OOF Hb predictions
  â€¢ XGBoost classifier  â†’ OOF anemia probabilities
  â€¢ ExtraTrees regressor  â†’ OOF Hb predictions
  â€¢ ExtraTrees classifier â†’ OOF anemia probabilities

Level-1 meta-learners:
  â€¢ Ridge regression        â†’ final Hb estimate
  â€¢ Logistic Regression     â†’ final anemia risk probability

Data augmentation (training folds only):
  â€¢ Gaussian noise on color features (sigma=0.01)
  â€¢ CPI jitter Â±0.02
  â€¢ 3Ã— oversampling of anemic class (label=1)

Run from workspace root:
    python backend/scripts/train_stacked.py
"""
from __future__ import annotations

import sys
import json
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import numpy as np
import joblib
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score, f1_score, mean_absolute_error,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit, RandomizedSearchCV
from sklearn.model_selection import cross_val_predict

try:
    from xgboost import XGBClassifier, XGBRegressor
    _HAS_XGB = True
except ImportError:
    _HAS_XGB = False
    print("WARNING: xgboost not installed â€” falling back to ExtraTrees-only stack.")
    print("         Install with: pip install xgboost")

from app.ml.archive_model import (
    ANEMIA_HB_THRESHOLD,
    _build_subject_catalog,
    _samples_for_mode,
    _rows_from_samples,
    clamp,
    sigmoid,
)
from app.ml.features import FEATURE_NAMES, COLOR_FEATURES
from app.ml.stacked_model import StackedRegressor, StackedClassifier

DATASET_ROOT = Path(__file__).parents[2] / "archive" / "dataset anemia"
OUTPUT_PATH = Path(__file__).parents[1] / "models" / "archive_screening_model.joblib"
OUTPUT_PATH_V4 = Path(__file__).parents[1] / "models" / "archive_screening_model_v4.joblib"
REPORT_PATH = Path(__file__).parents[1] / "models" / "training_report.json"

# Feature names for the v4 artifact (includes source flags)
V4_FEATURE_NAMES = FEATURE_NAMES + [
    "source_roi_original",
    "source_segmented",
    "source_forniceal_palpebral",
]

# Indices of color features used for augmentation
_COLOR_IDX = [V4_FEATURE_NAMES.index(n) for n in COLOR_FEATURES if n in V4_FEATURE_NAMES]
# Index of CPI feature for jitter
_CPI_IDX = V4_FEATURE_NAMES.index("cpi")

N_CV_SPLITS = 5
RANDOM_STATE = 42


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Augmentation
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def augment_training_data(
    rows: np.ndarray,
    targets: np.ndarray,
    labels: np.ndarray,
    groups: np.ndarray,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Augment training data:
    1. Add Gaussian noise (sigma=0.01) to color features for ALL samples.
    2. Oversample anemic class (label=1) 3Ã— with CPI jitter Â±0.02.
    Returns augmented arrays (originals + augmented copies).
    """
    n = len(rows)

    # --- noise augmentation for all samples ---
    noisy = rows.copy()
    noise = rng.normal(0, 0.01, size=(n, len(_COLOR_IDX)))
    noisy[:, _COLOR_IDX] += noise
    noisy = np.clip(noisy, 0.0, 1.0)

    aug_rows = [rows, noisy]
    aug_targets = [targets, targets]
    aug_labels = [labels, labels]
    aug_groups = [groups, groups]

    # --- 3Ã— oversample anemic samples with CPI jitter ---
    anemic_idx = np.where(labels == 1)[0]
    for _ in range(3):
        copies = rows[anemic_idx].copy()
        jitter = rng.uniform(-0.02, 0.02, size=len(anemic_idx))
        copies[:, _CPI_IDX] = np.clip(copies[:, _CPI_IDX] + jitter, 0.0, 1.0)
        # Also add small noise to other color features
        color_noise = rng.normal(0, 0.01, size=(len(anemic_idx), len(_COLOR_IDX)))
        copies[:, _COLOR_IDX] = np.clip(copies[:, _COLOR_IDX] + color_noise, 0.0, 1.0)
        aug_rows.append(copies)
        aug_targets.append(targets[anemic_idx])
        aug_labels.append(labels[anemic_idx])
        aug_groups.append(groups[anemic_idx])

    return (
        np.vstack(aug_rows),
        np.concatenate(aug_targets),
        np.concatenate(aug_labels),
        np.concatenate(aug_groups),
    )


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Base learner builders
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _et_regressor(rs: int = RANDOM_STATE) -> ExtraTreesRegressor:
    return ExtraTreesRegressor(
        n_estimators=300, min_samples_leaf=2, max_features=0.7,
        bootstrap=True, random_state=rs, n_jobs=1,
    )


def _et_classifier(rs: int = RANDOM_STATE) -> ExtraTreesClassifier:
    return ExtraTreesClassifier(
        n_estimators=300, min_samples_leaf=2, max_features=0.7,
        bootstrap=True, class_weight="balanced_subsample",
        random_state=rs, n_jobs=1,
    )


def _xgb_regressor(rs: int = RANDOM_STATE) -> "XGBRegressor":
    return XGBRegressor(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        random_state=rs, n_jobs=1, verbosity=0,
    )


def _xgb_classifier(rs: int = RANDOM_STATE) -> "XGBClassifier":
    return XGBClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        use_label_encoder=False, eval_metric="logloss",
        random_state=rs, n_jobs=1, verbosity=0,
    )


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Hyperparameter tuning
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def tune_et_regressor(rows: np.ndarray, targets: np.ndarray) -> ExtraTreesRegressor:
    param_dist = {
        "n_estimators": [100, 200, 300, 400],
        "min_samples_leaf": [1, 2, 3, 4],
        "max_features": [0.5, 0.6, 0.7, 0.8, "sqrt"],
    }
    base = ExtraTreesRegressor(bootstrap=True, random_state=RANDOM_STATE, n_jobs=1)
    search = RandomizedSearchCV(
        base, param_dist, n_iter=20, cv=3, scoring="neg_mean_absolute_error",
        random_state=RANDOM_STATE, n_jobs=1, refit=True,
    )
    search.fit(rows, targets)
    print(f"  ET regressor best params: {search.best_params_}", flush=True)
    return search.best_estimator_


def tune_et_classifier(rows: np.ndarray, labels: np.ndarray) -> ExtraTreesClassifier:
    param_dist = {
        "n_estimators": [100, 200, 300, 400],
        "min_samples_leaf": [1, 2, 3, 4],
        "max_features": [0.5, 0.6, 0.7, 0.8, "sqrt"],
    }
    base = ExtraTreesClassifier(
        bootstrap=True, class_weight="balanced_subsample",
        random_state=RANDOM_STATE, n_jobs=1,
    )
    search = RandomizedSearchCV(
        base, param_dist, n_iter=20, cv=3, scoring="f1",
        random_state=RANDOM_STATE, n_jobs=1, refit=True,
    )
    search.fit(rows, labels)
    print(f"  ET classifier best params: {search.best_params_}", flush=True)
    return search.best_estimator_


def tune_xgb_regressor(rows: np.ndarray, targets: np.ndarray) -> "XGBRegressor":
    param_dist = {
        "n_estimators": [100, 200, 300, 400, 500],
        "max_depth": [3, 4, 5, 6],
        "learning_rate": [0.01, 0.03, 0.05, 0.1, 0.15],
        "subsample": [0.6, 0.7, 0.8, 0.9, 1.0],
        "colsample_bytree": [0.6, 0.7, 0.8, 0.9, 1.0],
    }
    base = XGBRegressor(random_state=RANDOM_STATE, n_jobs=1, verbosity=0)
    search = RandomizedSearchCV(
        base, param_dist, n_iter=20, cv=3, scoring="neg_mean_absolute_error",
        random_state=RANDOM_STATE, n_jobs=1, refit=True,
    )
    search.fit(rows, targets)
    print(f"  XGB regressor best params: {search.best_params_}", flush=True)
    return search.best_estimator_


def tune_xgb_classifier(rows: np.ndarray, labels: np.ndarray) -> "XGBClassifier":
    param_dist = {
        "n_estimators": [100, 200, 300, 400, 500],
        "max_depth": [3, 4, 5, 6],
        "learning_rate": [0.01, 0.03, 0.05, 0.1, 0.15],
        "subsample": [0.6, 0.7, 0.8, 0.9, 1.0],
        "colsample_bytree": [0.6, 0.7, 0.8, 0.9, 1.0],
    }
    base = XGBClassifier(
        use_label_encoder=False, eval_metric="logloss",
        random_state=RANDOM_STATE, n_jobs=1, verbosity=0,
    )
    search = RandomizedSearchCV(
        base, param_dist, n_iter=20, cv=3, scoring="f1",
        random_state=RANDOM_STATE, n_jobs=1, refit=True,
    )
    search.fit(rows, labels)
    print(f"  XGB classifier best params: {search.best_params_}", flush=True)
    return search.best_estimator_


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Stacking helpers
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _group_kfold_indices(
    groups: np.ndarray, n_splits: int, random_state: int
) -> list[tuple[np.ndarray, np.ndarray]]:
    """GroupShuffleSplit folds for OOF stacking."""
    splitter = GroupShuffleSplit(n_splits=n_splits, test_size=0.2, random_state=random_state)
    return list(splitter.split(np.zeros(len(groups)), groups=groups))


def build_oof_meta_features(
    rows: np.ndarray,
    targets: np.ndarray,
    labels: np.ndarray,
    groups: np.ndarray,
    et_reg: ExtraTreesRegressor,
    et_clf: ExtraTreesClassifier,
    xgb_reg: object | None,
    xgb_clf: object | None,
    n_splits: int = N_CV_SPLITS,
) -> np.ndarray:
    """
    Build out-of-fold meta-features using group-aware splits.
    Always returns 4 columns: [et_hb, xgb_hb, et_prob, xgb_prob].
    If XGBoost unavailable, xgb columns are zeros.
    """
    n = len(rows)
    oof = np.zeros((n, 4), dtype=np.float32)
    rng = np.random.default_rng(RANDOM_STATE)

    folds = _group_kfold_indices(groups, n_splits, RANDOM_STATE)

    for fold_i, (train_idx, val_idx) in enumerate(folds):
        print(f"  OOF fold {fold_i + 1}/{n_splits}...", flush=True)

        tr_rows, tr_targets, tr_labels, tr_groups = augment_training_data(
            rows[train_idx], targets[train_idx], labels[train_idx], groups[train_idx], rng
        )
        val_rows = rows[val_idx]

        import copy
        fold_et_reg = copy.deepcopy(et_reg)
        fold_et_clf = copy.deepcopy(et_clf)
        fold_et_reg.fit(tr_rows, tr_targets)
        fold_et_clf.fit(tr_rows, tr_labels)

        oof[val_idx, 0] = fold_et_reg.predict(val_rows)
        oof[val_idx, 2] = fold_et_clf.predict_proba(val_rows)[:, 1]

        if xgb_reg is not None and xgb_clf is not None:
            fold_xgb_reg = copy.deepcopy(xgb_reg)
            fold_xgb_clf = copy.deepcopy(xgb_clf)
            fold_xgb_reg.fit(tr_rows, tr_targets)
            fold_xgb_clf.fit(tr_rows, tr_labels)
            oof[val_idx, 1] = fold_xgb_reg.predict(val_rows)
            oof[val_idx, 3] = fold_xgb_clf.predict_proba(val_rows)[:, 1]
        else:
            oof[val_idx, 1] = oof[val_idx, 0]   # mirror ET if no XGB
            oof[val_idx, 3] = oof[val_idx, 2]

    return oof


def find_best_threshold(labels: np.ndarray, scores: np.ndarray) -> float:
    """Threshold maximising recall-weighted F1 (medical screening priority)."""
    best_score, best_thresh = -1.0, 0.5
    for t in np.linspace(0.20, 0.75, 56):
        preds = (scores >= t).astype(int)
        if preds.sum() == 0:
            continue
        f1 = f1_score(labels, preds, zero_division=0)
        rec = recall_score(labels, preds, zero_division=0)
        score = f1 * 0.5 + rec * 0.5
        if score > best_score:
            best_score = score
            best_thresh = float(t)
    return best_thresh


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CV evaluation of the full stacked pipeline
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def evaluate_stacked(
    rows: np.ndarray,
    targets: np.ndarray,
    labels: np.ndarray,
    groups: np.ndarray,
    et_reg: ExtraTreesRegressor,
    et_clf: ExtraTreesClassifier,
    xgb_reg: object | None,
    xgb_clf: object | None,
    n_splits: int = N_CV_SPLITS,
) -> dict[str, float]:
    """
    Outer CV loop: for each fold, build OOF meta-features on the train portion,
    fit meta-learners, evaluate on the held-out test fold.
    """
    import copy
    splitter = GroupShuffleSplit(n_splits=n_splits, test_size=0.2, random_state=RANDOM_STATE + 1)
    all_metrics: list[dict[str, float]] = []
    rng = np.random.default_rng(RANDOM_STATE + 99)

    for fold_i, (train_idx, test_idx) in enumerate(splitter.split(rows, labels, groups)):
        print(f"  Outer CV fold {fold_i + 1}/{n_splits}...", flush=True)

        tr_rows_raw = rows[train_idx]
        tr_targets_raw = targets[train_idx]
        tr_labels_raw = labels[train_idx]
        tr_groups_raw = groups[train_idx]
        te_rows = rows[test_idx]
        te_targets = targets[test_idx]
        te_labels = labels[test_idx]

        # Build OOF meta-features on training portion (inner loop)
        oof_meta = build_oof_meta_features(
            tr_rows_raw, tr_targets_raw, tr_labels_raw, tr_groups_raw,
            copy.deepcopy(et_reg), copy.deepcopy(et_clf),
            copy.deepcopy(xgb_reg) if xgb_reg else None,
            copy.deepcopy(xgb_clf) if xgb_clf else None,
            n_splits=3,
        )

        # Fit meta-learners on OOF
        meta_reg = Ridge(alpha=1.0)
        meta_clf = LogisticRegression(C=1.0, max_iter=500, random_state=RANDOM_STATE, solver="lbfgs")
        meta_reg.fit(oof_meta, tr_targets_raw)
        meta_clf.fit(oof_meta, tr_labels_raw)

        # Build test meta-features: retrain base learners on augmented full train
        aug_rows, aug_targets, aug_labels, _ = augment_training_data(
            tr_rows_raw, tr_targets_raw, tr_labels_raw, tr_groups_raw, rng
        )

        fold_et_reg = copy.deepcopy(et_reg); fold_et_reg.fit(aug_rows, aug_targets)
        fold_et_clf = copy.deepcopy(et_clf); fold_et_clf.fit(aug_rows, aug_labels)

        te_meta = np.zeros((len(te_rows), 4), dtype=np.float32)
        te_meta[:, 0] = fold_et_reg.predict(te_rows)
        te_meta[:, 2] = fold_et_clf.predict_proba(te_rows)[:, 1]

        if xgb_reg is not None:
            fold_xgb_reg = copy.deepcopy(xgb_reg); fold_xgb_reg.fit(aug_rows, aug_targets)
            fold_xgb_clf = copy.deepcopy(xgb_clf); fold_xgb_clf.fit(aug_rows, aug_labels)
            te_meta[:, 1] = fold_xgb_reg.predict(te_rows)
            te_meta[:, 3] = fold_xgb_clf.predict_proba(te_rows)[:, 1]
        else:
            te_meta[:, 1] = te_meta[:, 0]
            te_meta[:, 3] = te_meta[:, 2]

        hb_pred = meta_reg.predict(te_meta)
        clf_prob = meta_clf.predict_proba(te_meta)[:, 1]

        # Blend: same scheme as legacy model
        hb_scale = max(float(np.quantile(np.abs(tr_targets_raw - fold_et_reg.predict(tr_rows_raw)), 0.75)), 0.8)
        reg_risk = np.array([sigmoid((ANEMIA_HB_THRESHOLD - h) / hb_scale) for h in hb_pred])
        blend = 0.55 * clf_prob + 0.45 * reg_risk
        thresh = find_best_threshold(te_labels, blend)
        preds = (blend >= thresh).astype(int)

        all_metrics.append({
            "accuracy": accuracy_score(te_labels, preds),
            "precision": precision_score(te_labels, preds, zero_division=0),
            "recall": recall_score(te_labels, preds, zero_division=0),
            "f1": f1_score(te_labels, preds, zero_division=0),
            "auc": roc_auc_score(te_labels, blend),
            "mae_hb": mean_absolute_error(te_targets, hb_pred),
            "threshold": thresh,
        })

    avg = {k: round(float(np.mean([m[k] for m in all_metrics])), 4) for k in all_metrics[0]}
    return avg


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Main
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def main() -> None:
    print("=" * 60, flush=True)
    print("AnemiaLens â€” stacked-ensemble-v4 training", flush=True)
    print("=" * 60, flush=True)

    # â”€â”€ 1. Load dataset â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[1/6] Loading dataset...", flush=True)
    subjects = _build_subject_catalog(DATASET_ROOT)
    print(f"  Subjects: {len(subjects)}", flush=True)

    samples = _samples_for_mode(subjects, "hybrid_dual")
    print(f"  Samples (hybrid_dual): {len(samples)}", flush=True)

    rows, targets, labels, groups = _rows_from_samples(samples)
    print(f"  Class balance: {labels.sum()} anemic / {(labels == 0).sum()} non-anemic", flush=True)

    # â”€â”€ 2. Hyperparameter tuning â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[2/6] Tuning hyperparameters (RandomizedSearchCV, 20 iter each)...", flush=True)
    rng = np.random.default_rng(RANDOM_STATE)
    aug_rows, aug_targets, aug_labels, _ = augment_training_data(rows, targets, labels, groups, rng)

    print("  Tuning ExtraTrees regressor...", flush=True)
    et_reg = tune_et_regressor(aug_rows, aug_targets)

    print("  Tuning ExtraTrees classifier...", flush=True)
    et_clf = tune_et_classifier(aug_rows, aug_labels)

    if _HAS_XGB:
        print("  Tuning XGBoost regressor...", flush=True)
        xgb_reg = tune_xgb_regressor(aug_rows, aug_targets)
        print("  Tuning XGBoost classifier...", flush=True)
        xgb_clf = tune_xgb_classifier(aug_rows, aug_labels)
    else:
        xgb_reg = xgb_clf = None

    # â”€â”€ 3. CV evaluation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[3/6] Cross-validating stacked ensemble...", flush=True)
    cv_metrics = evaluate_stacked(rows, targets, labels, groups, et_reg, et_clf, xgb_reg, xgb_clf)
    print(f"\n  CV metrics: {cv_metrics}", flush=True)

    # â”€â”€ 4. Build final OOF meta-features on all data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[4/6] Building final OOF meta-features on full dataset...", flush=True)
    oof_meta = build_oof_meta_features(
        rows, targets, labels, groups, et_reg, et_clf, xgb_reg, xgb_clf, n_splits=N_CV_SPLITS
    )

    # â”€â”€ 5. Fit final meta-learners â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[5/6] Fitting meta-learners on OOF predictions...", flush=True)
    meta_reg = Ridge(alpha=1.0)
    meta_clf = LogisticRegression(C=1.0, max_iter=500, random_state=RANDOM_STATE, solver="lbfgs")
    meta_reg.fit(oof_meta, targets)
    meta_clf.fit(oof_meta, labels)

    # Retrain base learners on full augmented data for inference
    rng2 = np.random.default_rng(RANDOM_STATE + 1)
    full_aug_rows, full_aug_targets, full_aug_labels, _ = augment_training_data(
        rows, targets, labels, groups, rng2
    )
    et_reg.fit(full_aug_rows, full_aug_targets)
    et_clf.fit(full_aug_rows, full_aug_labels)
    if xgb_reg is not None:
        xgb_reg.fit(full_aug_rows, full_aug_targets)
        xgb_clf.fit(full_aug_rows, full_aug_labels)

    # â”€â”€ 6. Instantiate module-level stacked wrappers for inference â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    stacked_reg = StackedRegressor(et_reg, xgb_reg, et_clf, xgb_clf, meta_reg)
    stacked_clf = StackedClassifier(et_clf, xgb_clf, et_reg, xgb_reg, meta_clf)

    # â”€â”€ Calibration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    hb_preds_full = stacked_reg.predict(rows)
    residuals = np.abs(targets - hb_preds_full)
    hb_scale = max(float(np.quantile(residuals, 0.75)), 0.8)

    hb_population_mean = float(np.mean(targets))
    pred_std = float(np.std(hb_preds_full))
    true_std = float(np.std(targets))
    hb_spread_factor = float(np.clip(true_std / max(pred_std, 0.5), 1.0, 2.0))

    clf_probs_full = stacked_clf.predict_proba(rows)[:, 1]
    reg_risk_full = np.array([sigmoid((ANEMIA_HB_THRESHOLD - h) / hb_scale) for h in hb_preds_full])
    blend_full = 0.55 * clf_probs_full + 0.45 * reg_risk_full
    best_threshold = find_best_threshold(labels, blend_full)
    risk_scale = max(float(np.std(blend_full)) * 0.9, 0.08)
    risk_scale = min(risk_scale, 0.22)

    calibration = {
        "hb_threshold": ANEMIA_HB_THRESHOLD,
        "hb_scale": round(hb_scale, 4),
        "hb_population_mean": round(hb_population_mean, 4),
        "hb_spread_factor": round(hb_spread_factor, 4),
        "regressor_tree_std_reference": 2.5,
        "classifier_tree_std_reference": 0.5,
        "classifier_weight": 0.55,
        "blend_threshold": round(best_threshold, 4),
        "risk_scale": round(risk_scale, 4),
        "base_uncertainty": 0.11,
    }

    # â”€â”€ Save artifact â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[6/6] Saving model...", flush=True)
    artifact = {
        "version": "stacked-ensemble-v4",
        "feature_names": V4_FEATURE_NAMES,
        "regressor": stacked_reg,
        "classifier": stacked_clf,
        "calibration": calibration,
        "training": {
            "selected_mode": "hybrid_dual",
            "subject_count": len(subjects),
            "record_count": len(samples),
            "metrics": cv_metrics,
            "xgboost_available": _HAS_XGB,
        },
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, OUTPUT_PATH)
    joblib.dump(artifact, OUTPUT_PATH_V4)  # keep versioned copy too
    print(f"  Saved â†’ {OUTPUT_PATH}", flush=True)
    print(f"  Saved â†’ {OUTPUT_PATH_V4}", flush=True)

    report = {
        "dataset_name": "dataset anemia",
        "record_count": len(samples),
        "subject_count": len(subjects),
        "primary_model": "stacked-ensemble-v4",
        "selected_mode": "hybrid_dual",
        "metrics": cv_metrics,
        "calibration": {
            "blend_threshold": calibration["blend_threshold"],
            "risk_scale": calibration["risk_scale"],
            "classifier_weight": calibration["classifier_weight"],
        },
    }
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"  Report â†’ {REPORT_PATH}", flush=True)

    # â”€â”€ Sanity check â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\nâ”€â”€ Sanity check â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€", flush=True)
    feat_idx = {n: i for i, n in enumerate(V4_FEATURE_NAMES)}

    test_cases = [
        ("PALE (anemic)",  0.28, 0.02, 0.22),
        ("BORDERLINE",     0.35, 0.04, 0.30),
        ("NORMAL",         0.44, 0.08, 0.38),
        ("VERY HEALTHY",   0.48, 0.10, 0.42),
    ]
    for label, cpi_val, rg_val, br_val in test_cases:
        row = np.zeros((1, len(V4_FEATURE_NAMES)), dtype=np.float32)
        row[0, feat_idx["cpi"]] = cpi_val
        row[0, feat_idx["center_cpi"]] = cpi_val - 0.01
        row[0, feat_idx["mean_r"]] = cpi_val * 0.9
        row[0, feat_idx["mean_g"]] = cpi_val * 0.9 - rg_val
        row[0, feat_idx["mean_b"]] = cpi_val * 0.7
        row[0, feat_idx["center_mean_r"]] = cpi_val * 0.9
        row[0, feat_idx["center_mean_g"]] = cpi_val * 0.9 - rg_val
        row[0, feat_idx["center_mean_b"]] = cpi_val * 0.7
        row[0, feat_idx["red_green_gap"]] = rg_val
        row[0, feat_idx["center_red_green_gap"]] = rg_val
        row[0, feat_idx["brightness"]] = br_val
        row[0, feat_idx["center_brightness"]] = br_val
        row[0, feat_idx["contrast"]] = 0.12
        row[0, feat_idx["center_contrast"]] = 0.12
        row[0, feat_idx["blur_score"]] = 100.0
        row[0, feat_idx["center_blur_score"]] = 120.0
        row[0, feat_idx["saturation"]] = 0.3
        row[0, feat_idx["center_saturation"]] = 0.3
        row[0, feat_idx["green_blue_ratio"]] = 1.1 if cpi_val < 0.35 else 1.25
        row[0, feat_idx["hist_mid"]] = 0.5
        row[0, feat_idx["hist_bright"]] = 0.3
        row[0, feat_idx["aspect_ratio"]] = 1.0
        row[0, feat_idx["size_score"]] = 1.0
        row[0, feat_idx["source_roi_original"]] = 1.0

        hb_p = float(stacked_reg.predict(row)[0])
        cp = float(stacked_clf.predict_proba(row)[0, 1])
        rr = sigmoid((ANEMIA_HB_THRESHOLD - hb_p) / hb_scale)
        bs = 0.55 * cp + 0.45 * rr
        risk = sigmoid((bs - best_threshold) / risk_scale)
        decision = "ANEMIA LIKELY" if risk >= 0.65 else "unlikely"
        print(f"  {label}: Hb={hb_p:.1f}, clf_prob={cp:.3f}, risk={risk:.3f} -> {decision}", flush=True)

    print("\nDone.", flush=True)


if __name__ == "__main__":
    main()

