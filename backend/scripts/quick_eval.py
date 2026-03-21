"""Quick eval on first 15 subjects only — for proof/demo purposes."""
import sys, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

import numpy as np
from app.services.prediction import ScreeningPredictor
from app.services.image_quality import ImageQualityService
from app.ml.archive_model import _build_subject_catalog, ANEMIA_HB_THRESHOLD
from sklearn.metrics import (
    accuracy_score, f1_score, recall_score,
    precision_score, roc_auc_score, mean_absolute_error,
    confusion_matrix
)

predictor = ScreeningPredictor()
quality_svc = ImageQualityService()

print("Model:", predictor.archive_model.get("version"))
print("Threshold:", predictor.archive_model.get("calibration", {}).get("blend_threshold"))
print()

subjects = _build_subject_catalog(Path(__file__).parents[2] / "archive" / "dataset anemia")
print(f"Total subjects in dataset: {len(subjects)}")
anemic = sum(1 for s in subjects if s["label"] == 1)
normal = sum(1 for s in subjects if s["label"] == 0)
print(f"  Anemic (Hb < {ANEMIA_HB_THRESHOLD}): {anemic}")
print(f"  Normal (Hb >= {ANEMIA_HB_THRESHOLD}): {normal}")
print(f"  Hb range: {min(s['hb'] for s in subjects):.1f} - {max(s['hb'] for s in subjects):.1f} g/dL")
print(f"  Hb mean:  {np.mean([s['hb'] for s in subjects]):.2f} g/dL")
print(f"  Hb std:   {np.std([s['hb'] for s in subjects]):.2f} g/dL")
print()

# Quick eval on first 15 subjects
results = []
blocked = 0
errors = 0
for s in subjects[:15]:
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
            "subject": s["subject_id"],
            "hb_true": s["hb"],
            "hb_pred": pred.predicted_hemoglobin,
            "risk": pred.anemia_risk,
            "label_true": int(s["hb"] < ANEMIA_HB_THRESHOLD),
            "label_pred": 1 if pred.screening_label == "anemia_likely" else 0,
            "label": pred.screening_label,
            "uncertainty": pred.uncertainty,
            "confidence": pred.confidence,
        })
    except Exception as e:
        errors += 1
        print(f"  Error {s['subject_id']}: {e}")

print(f"Processed: {len(results)}, Blocked by quality: {blocked}, Errors: {errors}")
print()

if results:
    lt = [r["label_true"] for r in results]
    lp = [r["label_pred"] for r in results]
    risks = [r["risk"] for r in results]
    hb_t = [r["hb_true"] for r in results if r["hb_pred"]]
    hb_p = [r["hb_pred"] for r in results if r["hb_pred"]]

    print("=== SAMPLE METRICS (15 subjects) ===")
    print(f"Accuracy:  {accuracy_score(lt, lp):.3f}")
    print(f"Recall:    {recall_score(lt, lp, zero_division=0):.3f}  ← most important (catch anemia)")
    print(f"Precision: {precision_score(lt, lp, zero_division=0):.3f}")
    print(f"F1:        {f1_score(lt, lp, zero_division=0):.3f}")
    if len(set(lt)) > 1:
        print(f"AUC:       {roc_auc_score(lt, risks):.3f}")
    if hb_p:
        print(f"Hb MAE:    {mean_absolute_error(hb_t, hb_p):.2f} g/dL")

    cm = confusion_matrix(lt, lp)
    print()
    print("Confusion Matrix:")
    print("              Pred Normal  Pred Anemic")
    if cm.shape == (2,2):
        print(f"  True Normal     {cm[0][0]:3d}          {cm[0][1]:3d}")
        print(f"  True Anemic     {cm[1][0]:3d}          {cm[1][1]:3d}")
        tn, fp, fn, tp = cm.ravel()
        print(f"\n  True Positives (caught anemia): {tp}")
        print(f"  False Negatives (missed anemia): {fn}")
        print(f"  False Positives (false alarm):   {fp}")
        print(f"  True Negatives (correct clear):  {tn}")

    print()
    print("=== SAMPLE PREDICTIONS ===")
    print(f"{'Subject':<15} {'Hb True':>8} {'Hb Pred':>8} {'Risk':>6} {'Uncert':>7} {'Label':<20} {'Correct'}")
    print("-" * 80)
    for r in results:
        correct = "OK" if r["label_true"] == r["label_pred"] else "WRONG"
        hbp = f"{r['hb_pred']:.1f}" if r["hb_pred"] else "hidden"
        print(f"{r['subject']:<15} {r['hb_true']:>8.1f} {hbp:>8} {r['risk']:>6.3f} {r['uncertainty']:>7.3f} {r['label']:<20} {correct}")
