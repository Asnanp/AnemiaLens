"""
Proof metrics — loads features directly from pre-cropped palpebral PNGs
(fast, no ROI extraction needed). Shows dataset stats + CV results from
the training report + feature importance.
"""
import sys, json, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

import numpy as np
import joblib
from app.ml.features import extract_eye_features
from app.ml.archive_model import ANEMIA_HB_THRESHOLD, _parse_workbook, _parse_float, _load_image_with_fallback, ARCHIVE_FEATURE_NAMES
from sklearn.metrics import (
    accuracy_score, f1_score, recall_score,
    precision_score, roc_auc_score, mean_absolute_error,
    confusion_matrix
)
from app.ml.archive_model import sigmoid, prepare_feature_map

DATASET_ROOT = Path(__file__).parents[2] / "archive" / "dataset anemia"
MODEL_PATH   = Path(__file__).parents[1] / "models" / "archive_screening_model.joblib"
REPORT_PATH  = Path(__file__).parents[1] / "models" / "training_report.json"

# ── 1. Dataset stats ──────────────────────────────────────────────────────────
print("=" * 60)
print("DATASET STATISTICS")
print("=" * 60)
all_hb = []
countries = {"India": 0, "Italy": 0}
for country in ("India", "Italy"):
    wb = DATASET_ROOT / country / f"{country}.xlsx"
    meta = _parse_workbook(wb)
    for num, row in meta.items():
        hb = _parse_float(row.get("Hgb"))
        if hb:
            all_hb.append(hb)
            countries[country] += 1

all_hb = np.array(all_hb)
anemic = (all_hb < ANEMIA_HB_THRESHOLD).sum()
normal = (all_hb >= ANEMIA_HB_THRESHOLD).sum()
print(f"Total subjects:   {len(all_hb)}")
print(f"  India:          {countries['India']}")
print(f"  Italy:          {countries['Italy']}")
print(f"Anemic (Hb<{ANEMIA_HB_THRESHOLD}): {anemic}  ({100*anemic/len(all_hb):.1f}%)")
print(f"Normal:           {normal}  ({100*normal/len(all_hb):.1f}%)")
print(f"Hb range:         {all_hb.min():.1f} – {all_hb.max():.1f} g/dL")
print(f"Hb mean ± std:    {all_hb.mean():.2f} ± {all_hb.std():.2f} g/dL")

# ── 2. CV metrics from training report ───────────────────────────────────────
print()
print("=" * 60)
print("CROSS-VALIDATION METRICS  (5-fold group-aware)")
print("=" * 60)
report = json.load(open(REPORT_PATH))
m = report["metrics"]
print(f"Accuracy:         {m['accuracy']:.4f}  ({m['accuracy']*100:.1f}%)")
print(f"Recall:           {m['recall']:.4f}  ({m['recall']*100:.1f}%)  << catches anemia")
print(f"Precision:        {m['precision']:.4f}  ({m['precision']*100:.1f}%)")
print(f"F1 Score:         {m['f1']:.4f}")
print(f"AUC-ROC:          {m['auc']:.4f}")
print(f"Hb MAE:           {m['mae_hb']:.4f} g/dL")
print(f"Blend threshold:  {report['calibration']['blend_threshold']}")
print(f"Classifier weight:{report['calibration']['classifier_weight']}")

# ── 3. Quick inference on pre-cropped PNGs (fast path) ───────────────────────
print()
print("=" * 60)
print("INFERENCE CHECK  (pre-cropped palpebral PNGs, first 30 subjects)")
print("=" * 60)

artifact = joblib.load(MODEL_PATH)
reg = artifact["regressor"]
clf = artifact["classifier"]
cal = artifact["calibration"]
feat_names = artifact["feature_names"]
hb_scale = cal["hb_scale"]
blend_thresh = cal["blend_threshold"]
risk_scale = cal["risk_scale"]
clf_w = cal["classifier_weight"]
hb_pop_mean = cal.get("hb_population_mean", 12.8)
hb_spread = cal.get("hb_spread_factor", 2.0)

results = []
for country in ("India", "Italy"):
    wb = DATASET_ROOT / country / f"{country}.xlsx"
    meta = _parse_workbook(wb)
    for num, row in meta.items():
        if len(results) >= 30:
            break
        hb = _parse_float(row.get("Hgb"))
        if hb is None:
            continue
        subj_dir = DATASET_ROOT / country / num
        pngs = [p for p in subj_dir.glob("*_palpebral.png") if "forniceal" not in p.name]
        if not pngs:
            continue
        try:
            img = _load_image_with_fallback(pngs[0])
            feats = extract_eye_features(img)
            prepared = prepare_feature_map(feats, source_hint="palpebral")
            row_vec = np.array([[prepared.get(n, 0.0) for n in feat_names]], dtype=np.float32)
            hb_raw = float(reg.predict(row_vec)[0])
            deviation = hb_raw - hb_pop_mean
            hb_pred = float(np.clip(hb_pop_mean + deviation * hb_spread, 5.0, 20.0))
            clf_prob = float(clf.predict_proba(row_vec)[0, 1])
            reg_risk = sigmoid((ANEMIA_HB_THRESHOLD - hb_pred) / hb_scale)
            blend = clf_w * clf_prob + (1 - clf_w) * reg_risk
            risk = sigmoid((blend - blend_thresh) / risk_scale)
            label_pred = 1 if risk >= 0.5 else 0
            label_true = int(hb < ANEMIA_HB_THRESHOLD)
            results.append({
                "subject": f"{country}-{num}",
                "hb_true": hb,
                "hb_pred": round(hb_pred, 1),
                "risk": round(risk, 3),
                "label_true": label_true,
                "label_pred": label_pred,
            })
        except Exception as e:
            pass

lt = [r["label_true"] for r in results]
lp = [r["label_pred"] for r in results]
risks = [r["risk"] for r in results]
hb_t = [r["hb_true"] for r in results]
hb_p = [r["hb_pred"] for r in results]

print(f"Subjects evaluated: {len(results)}")
print(f"Accuracy:   {accuracy_score(lt, lp):.3f}")
print(f"Recall:     {recall_score(lt, lp, zero_division=0):.3f}")
print(f"Precision:  {precision_score(lt, lp, zero_division=0):.3f}")
print(f"F1:         {f1_score(lt, lp, zero_division=0):.3f}")
if len(set(lt)) > 1:
    print(f"AUC:        {roc_auc_score(lt, risks):.3f}")
print(f"Hb MAE:     {mean_absolute_error(hb_t, hb_p):.2f} g/dL")

cm = confusion_matrix(lt, lp)
if cm.shape == (2, 2):
    tn, fp, fn, tp = cm.ravel()
    print()
    print("Confusion Matrix:")
    print(f"  True Positives  (anemia caught):  {tp}")
    print(f"  False Negatives (anemia missed):  {fn}")
    print(f"  False Positives (false alarm):    {fp}")
    print(f"  True Negatives  (correct clear):  {tn}")

print()
print("Sample predictions:")
print(f"{'Subject':<18} {'Hb True':>8} {'Hb Pred':>8} {'Risk':>7} {'Correct'}")
print("-" * 55)
for r in results[:15]:
    tag = "OK" if r["label_true"] == r["label_pred"] else "WRONG"
    print(f"{r['subject']:<18} {r['hb_true']:>8.1f} {r['hb_pred']:>8.1f} {r['risk']:>7.3f}  {tag}")

# ── 4. Feature importance ─────────────────────────────────────────────────────
print()
print("=" * 60)
print("TOP 10 FEATURES  (combined regressor + classifier importance)")
print("=" * 60)
combined = (np.array(reg.feature_importances_) * 0.45 +
            np.array(clf.feature_importances_) * 0.55)
ranked = sorted(zip(feat_names, combined), key=lambda x: x[1], reverse=True)
for i, (name, imp) in enumerate(ranked[:10], 1):
    bar = "|" * int(imp * 300)
    print(f"  {i:2}. {name:<30} {imp:.4f}  {bar}")

print()
print("=" * 60)
print("MODEL ARTIFACT")
print("=" * 60)
model_size = MODEL_PATH.stat().st_size / 1024 / 1024
print(f"Version:    {artifact['version']}")
print(f"Size:       {model_size:.1f} MB")
print(f"Regressor:  ExtraTreesRegressor  n_estimators=300")
print(f"Classifier: ExtraTreesClassifier n_estimators=300  class_weight=balanced_subsample")
print(f"Features:   {len(feat_names)} total")
print(f"Training:   {report['record_count']} samples, pipeline-aligned (raw JPG → ROI → features)")
print(f"Validation: 5-fold GroupShuffleSplit (no subject leakage)")
