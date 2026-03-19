import joblib, sys
sys.path.insert(0, 'backend')
from app.ml.archive_model import predict_with_archive_model
from app.ml.features import FEATURE_NAMES

m = joblib.load('backend/models/archive_screening_model.joblib')

test_cases = [
    ("PALE (anemic)", 0.28, 0.02, 0.22),
    ("BORDERLINE",    0.35, 0.04, 0.30),
    ("NORMAL",        0.44, 0.08, 0.38),
    ("VERY HEALTHY",  0.48, 0.10, 0.42),
]

for label, cpi, rg, br in test_cases:
    feat_map = {n: 0.0 for n in FEATURE_NAMES}
    feat_map['cpi'] = cpi
    feat_map['center_cpi'] = cpi - 0.01
    feat_map['mean_r'] = cpi * 0.9
    feat_map['mean_g'] = cpi * 0.9 - rg
    feat_map['mean_b'] = cpi * 0.7
    feat_map['red_green_gap'] = rg
    feat_map['center_red_green_gap'] = rg
    feat_map['brightness'] = br
    feat_map['green_blue_ratio'] = 1.1 if cpi < 0.35 else 1.25
    feat_map['center_mean_r'] = feat_map['mean_r']
    feat_map['center_mean_g'] = feat_map['mean_g']
    feat_map['center_mean_b'] = feat_map['mean_b']
    feat_map['contrast'] = 0.12
    feat_map['center_contrast'] = 0.12
    feat_map['center_brightness'] = br
    feat_map['blur_score'] = 100.0
    feat_map['center_blur_score'] = 120.0
    feat_map['saturation'] = 0.3
    feat_map['center_saturation'] = 0.3
    feat_map['hist_mid'] = 0.5
    feat_map['hist_bright'] = 0.3
    feat_map['aspect_ratio'] = 1.0
    feat_map['size_score'] = 1.0
    result = predict_with_archive_model(m, feat_map, source_hint='roi_original')
    hb = result['predicted_hemoglobin']
    risk = result['anemia_risk']
    unc = result['uncertainty']
    decision = "ANEMIA LIKELY" if risk >= 0.65 else "unlikely"
    print(f"{label}: Hb={hb:.1f}, risk={risk:.3f}, uncertainty={unc:.3f} -> {decision}")
