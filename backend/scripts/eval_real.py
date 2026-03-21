"""
Evaluate model on real dataset subjects with known Hb values.
Shows true Hb vs predicted Hb vs risk score.
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

import joblib, numpy as np
from app.ml.archive_model import (
    _build_subject_catalog, predict_with_archive_model, ANEMIA_HB_THRESHOLD
)

m = joblib.load(Path(__file__).parents[1] / "models" / "archive_screening_model.joblib")
cal = m["calibration"]
print("Model version:", m["version"])
print("Blend threshold:", cal["blend_threshold"])
print("Risk scale:", cal["risk_scale"])
print()

subjects = _build_subject_catalog(Path(__file__).parents[2] / "archive" / "dataset anemia")
print(f"Total subjects: {len(subjects)}")

anemic = [s for s in subjects if s["hb"] < 11.5][:8]
borderline = [s for s in subjects if 11.5 <= s["hb"] < 13.0][:4]
normal = [s for s in subjects if s["hb"] >= 13.0][:8]

correct = 0
total = 0

for group, cases in [("ANEMIC (Hb<11.5)", anemic), ("BORDERLINE", borderline), ("NORMAL (Hb>=13)", normal)]:
    print(f"--- {group} ---")
    for s in cases:
        feat = list(s["views"].values())[0]
        result = predict_with_archive_model(m, feat, source_hint="roi_original")
        hb_true = s["hb"]
        hb_pred = result["predicted_hemoglobin"]
        risk = result["anemia_risk"]
        predicted_anemic = risk >= 0.65
        actually_anemic = hb_true < ANEMIA_HB_THRESHOLD
        ok = predicted_anemic == actually_anemic
        correct += int(ok)
        total += 1
        tag = "OK" if ok else "WRONG"
        print(f"  True={hb_true:.1f}  Pred={hb_pred:.1f}  Risk={risk:.3f}  [{tag}]")
    print()

print(f"Accuracy on sample: {correct}/{total} = {correct/total*100:.0f}%")

# Full dataset accuracy
print("\n--- Full dataset ---")
all_risks = []
all_labels = []
all_hb_true = []
all_hb_pred = []
for s in subjects:
    feat = list(s["views"].values())[0]
    result = predict_with_archive_model(m, feat, source_hint="roi_original")
    all_risks.append(result["anemia_risk"])
    all_labels.append(int(s["hb"] < ANEMIA_HB_THRESHOLD))
    all_hb_true.append(s["hb"])
    all_hb_pred.append(result["predicted_hemoglobin"])

risks = np.array(all_risks)
labels = np.array(all_labels)
hb_true = np.array(all_hb_true)
hb_pred = np.array(all_hb_pred)

from sklearn.metrics import accuracy_score, f1_score, recall_score, precision_score, roc_auc_score, mean_absolute_error
preds = (risks >= 0.65).astype(int)
print(f"Accuracy:  {accuracy_score(labels, preds):.3f}")
print(f"Precision: {precision_score(labels, preds, zero_division=0):.3f}")
print(f"Recall:    {recall_score(labels, preds, zero_division=0):.3f}")
print(f"F1:        {f1_score(labels, preds, zero_division=0):.3f}")
print(f"AUC:       {roc_auc_score(labels, risks):.3f}")
print(f"Hb MAE:    {mean_absolute_error(hb_true, hb_pred):.3f} g/dL")
print(f"Hb bias:   {float(np.mean(hb_pred - hb_true)):.3f} g/dL (+ = overestimate)")
print(f"Risk dist anemic:  {np.percentile(risks[labels==1], [10,25,50,75,90]).round(3)}")
print(f"Risk dist normal:  {np.percentile(risks[labels==0], [10,25,50,75,90]).round(3)}")
