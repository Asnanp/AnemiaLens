"""
Test the full inference pipeline (quality -> features -> predict) on real dataset images.
This simulates exactly what happens when a user uploads a photo.
"""
import sys, io
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

import numpy as np
from PIL import Image
from app.services.prediction import ScreeningPredictor
from app.services.image_quality import ImageQualityService
from app.ml.archive_model import _build_subject_catalog, ANEMIA_HB_THRESHOLD
from sklearn.metrics import accuracy_score, f1_score, recall_score, precision_score, roc_auc_score, mean_absolute_error

predictor = ScreeningPredictor()
quality_svc = ImageQualityService()

print("Model:", predictor.archive_model.get("version") if predictor.archive_model else "NONE")
print()

subjects = _build_subject_catalog(Path(__file__).parents[2] / "archive" / "dataset anemia")

# Test on original JPG images (what users actually upload)
results = []
blocked = 0
for s in subjects[:40]:  # first 40 for speed
    country = s["subject_id"].split("-")[0]
    num = s["subject_number"]
    jpg_path = Path(__file__).parents[2] / "archive" / "dataset anemia" / country / num
    jpgs = list(jpg_path.glob("*.jpg"))
    if not jpgs:
        continue
    
    with open(jpgs[0], "rb") as f:
        img_bytes = f.read()
    
    try:
        quality, rgb = quality_svc.evaluate(img_bytes)
        if not quality.passed:
            blocked += 1
            continue
        pred = predictor.predict(rgb, quality, symptom_score=0.0)
        results.append({
            "hb_true": s["hb"],
            "hb_pred": pred.predicted_hemoglobin,
            "risk": pred.anemia_risk,
            "label_true": int(s["hb"] < ANEMIA_HB_THRESHOLD),
            "label_pred": int(pred.anemia_risk >= 0.65) if pred.anemia_risk else 0,
            "screening_label": pred.screening_label,
        })
    except Exception as e:
        print(f"  Error on {s['subject_id']}: {e}")

print(f"Processed: {len(results)}, Blocked by quality: {blocked}")
print()

if not results:
    print("No results — all blocked by quality gate!")
else:
    labels_true = [r["label_true"] for r in results]
    labels_pred = [r["label_pred"] for r in results]
    risks = [r["risk"] for r in results if r["risk"] is not None]
    hb_true = [r["hb_true"] for r in results if r["hb_pred"] is not None]
    hb_pred = [r["hb_pred"] for r in results if r["hb_pred"] is not None]

    print(f"Accuracy:  {accuracy_score(labels_true, labels_pred):.3f}")
    print(f"Recall:    {recall_score(labels_true, labels_pred, zero_division=0):.3f}")
    print(f"Precision: {precision_score(labels_true, labels_pred, zero_division=0):.3f}")
    print(f"F1:        {f1_score(labels_true, labels_pred, zero_division=0):.3f}")
    if len(set(labels_true)) > 1 and risks:
        print(f"AUC:       {roc_auc_score(labels_true[:len(risks)], risks):.3f}")
    if hb_pred:
        print(f"Hb MAE:    {mean_absolute_error(hb_true, hb_pred):.3f} g/dL")
        print(f"Hb bias:   {float(np.mean(np.array(hb_pred) - np.array(hb_true))):.3f} g/dL")

    print("\nSample predictions:")
    for r in results[:10]:
        tag = "OK" if r["label_true"] == r["label_pred"] else "WRONG"
        print(f"  True={r['hb_true']:.1f}  Pred={r['hb_pred']}  Risk={r['risk']}  {r['screening_label']}  [{tag}]")
