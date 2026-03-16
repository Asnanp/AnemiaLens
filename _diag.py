import sys
sys.path.insert(0, 'backend')
from PIL import Image
from app.ml.features import extract_eye_features
from app.ml.archive_model import predict_with_archive_model, load_archive_model
from app.ml.efficientnet_model import predict_with_efficientnet_model, load_efficientnet_checkpoint
from app.services.conjunctiva_roi import ConjunctivaRoiExtractor
from app.config import DEFAULT_ARCHIVE_MODEL_PATH, DEFAULT_EFFICIENTNET_MODEL_PATH

extractor = ConjunctivaRoiExtractor()
archive = load_archive_model(DEFAULT_ARCHIVE_MODEL_PATH)
efficientnet = load_efficientnet_checkpoint(DEFAULT_EFFICIENTNET_MODEL_PATH)

cases = [
    ('low-risk',     'frontend/public/demo-cases/low-risk-demo.jpg'),
    ('moderate',     'frontend/public/demo-cases/moderate-risk-demo.jpg'),
    ('high-concern', 'frontend/public/demo-cases/high-concern-demo.jpg'),
]

for name, path in cases:
    img = Image.open(path).convert('RGB')
    roi = extractor.extract(img)
    work_img = roi.image

    features = extract_eye_features(work_img)
    arch = predict_with_archive_model(archive, features)
    eff  = predict_with_efficientnet_model(efficientnet, work_img, mc_passes=10)

    print(name, "roi_extracted=" + str(roi.extracted))
    print("  archive  risk=" + str(round(arch['anemia_risk'],3)) + "  hb=" + str(round(arch['predicted_hemoglobin'],1)) + "  unc=" + str(round(arch['uncertainty'],3)))
    print("  effnet   risk=" + str(round(eff['anemia_risk'],3))  + "  hb=" + str(round(eff['predicted_hemoglobin'],1))  + "  unc=" + str(round(eff['uncertainty'],3)))
    print("  features mean_r=" + str(round(features['mean_r'],3)) + " mean_g=" + str(round(features['mean_g'],3)) + " red_green_gap=" + str(round(features['red_green_gap'],3)))
    print()
