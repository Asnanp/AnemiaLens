import sys
sys.path.insert(0, 'backend')
from PIL import Image
from app.services.prediction import ScreeningPredictor
from app.services.triage import TriageService
from app.services.image_quality import ImageQualityService
from app.schemas import SymptomInput

predictor = ScreeningPredictor()
triage_svc = TriageService()
quality_svc = ImageQualityService()

cases = [
    ('low-risk',     'frontend/public/demo-cases/low-risk-demo.jpg',     False, False, False, False),
    ('moderate',     'frontend/public/demo-cases/moderate-risk-demo.jpg', True,  True,  False, False),
    ('high-concern', 'frontend/public/demo-cases/high-concern-demo.jpg',  True,  True,  True,  True),
]

for name, path, fatigue, dizziness, pale_skin, sob in cases:
    with open(path, 'rb') as f:
        img_bytes = f.read()

    img = Image.open(path).convert('RGB')
    quality = quality_svc.evaluate(img_bytes)[0]
    prediction = predictor.predict(img, quality)
    symptoms = SymptomInput(fatigue=fatigue, dizziness=dizziness, pale_skin=pale_skin, shortness_of_breath=sob, heavy_menstrual_bleeding=None, poor_diet_low_iron=False)
    triage = triage_svc.assess(quality, prediction, symptoms)

    print(name)
    print("  quality passed=" + str(quality.passed))
    print("  risk=" + str(round(prediction.anemia_risk, 3)) + "  hb=" + str(prediction.predicted_hemoglobin) + "  unc=" + str(round(prediction.uncertainty, 3)) + "  reliability=" + prediction.reliability_flag)
    print("  triage band=" + triage.band + "  score=" + str(triage.score))
    print()
