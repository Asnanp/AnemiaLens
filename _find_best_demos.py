import sys, os
sys.path.insert(0, 'backend')
from PIL import Image
from app.ml.features import extract_eye_features
from app.ml.archive_model import predict_with_archive_model, load_archive_model
from app.ml.efficientnet_model import predict_with_efficientnet_model, load_efficientnet_checkpoint
from app.ml.runtime_stack import build_runtime_stack_prediction
from app.services.conjunctiva_roi import ConjunctivaRoiExtractor
from app.config import DEFAULT_ARCHIVE_MODEL_PATH, DEFAULT_EFFICIENTNET_MODEL_PATH

extractor = ConjunctivaRoiExtractor()
archive = load_archive_model(DEFAULT_ARCHIVE_MODEL_PATH)
efficientnet = load_efficientnet_checkpoint(DEFAULT_EFFICIENTNET_MODEL_PATH)

results = []
base = "archive/dataset anemia/India"

for subject in sorted(os.listdir(base), key=lambda x: int(x) if x.isdigit() else 999):
    folder = os.path.join(base, subject)
    if not os.path.isdir(folder): continue
    # prefer palpebral image (most relevant for conjunctiva)
    imgs = [f for f in os.listdir(folder) if f.endswith('_palpebral.png') and '(' not in f]
    if not imgs:
        imgs = [f for f in os.listdir(folder) if f.endswith('.jpg')]
    if not imgs: continue
    path = os.path.join(folder, imgs[0])
    try:
        img = Image.open(path).convert('RGB')
        roi = extractor.extract(img)
        features = extract_eye_features(roi.image)
        arch = predict_with_archive_model(archive, features)
        eff = predict_with_efficientnet_model(efficientnet, roi.image, mc_passes=8)
        stack = build_runtime_stack_prediction(arch, efficientnet_prediction=eff)
        risk = stack['anemia_risk']
        unc = stack['uncertainty']
        results.append((risk, unc, subject, path, arch['predicted_hemoglobin']))
    except Exception as e:
        pass

results.sort(key=lambda x: x[0])

print("=== LOW RISK candidates (risk < 0.35, unc < 0.45) ===")
low = [(r,u,s,p,h) for r,u,s,p,h in results if r < 0.35 and u < 0.45][:5]
for r,u,s,p,h in low:
    print(f"  subject={s} risk={round(r,3)} unc={round(u,3)} hb={round(h,1)} path={p}")

print("\n=== MODERATE candidates (0.45 < risk < 0.70, unc < 0.55) ===")
mod = [(r,u,s,p,h) for r,u,s,p,h in results if 0.45 < r < 0.70 and u < 0.55][:5]
for r,u,s,p,h in mod:
    print(f"  subject={s} risk={round(r,3)} unc={round(u,3)} hb={round(h,1)} path={p}")

print("\n=== HIGH CONCERN candidates (risk > 0.72, unc < 0.50) ===")
high = [(r,u,s,p,h) for r,u,s,p,h in results if r > 0.72 and u < 0.50][:5]
for r,u,s,p,h in high:
    print(f"  subject={s} risk={round(r,3)} unc={round(u,3)} hb={round(h,1)} path={p}")
