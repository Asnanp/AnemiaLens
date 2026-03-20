import requests, io, json
from PIL import Image

img = Image.new('RGB', (400, 300), color=(200, 160, 140))
buf = io.BytesIO()
img.save(buf, format='JPEG')
buf.seek(0)

symptoms = json.dumps({
    "fatigue": True,
    "pale_skin": True,
    "dizziness": False,
    "shortness_of_breath": False,
    "heavy_menstrual_bleeding": None,
    "poor_diet_low_iron": False
})

r = requests.post(
    'http://localhost:8000/api/analyze',
    files={'image': ('test.jpg', buf, 'image/jpeg')},
    data={'symptoms': symptoms},
    timeout=30
)
print('Status:', r.status_code)
if r.status_code == 200:
    d = r.json()
    pred = d.get('prediction') or {}
    triage = d.get('triage') or {}
    print('Hb:', pred.get('predicted_hemoglobin'))
    print('Risk:', pred.get('anemia_risk'))
    print('Label:', pred.get('screening_label'))
    print('Model:', pred.get('model_source'))
    print('Triage band:', triage.get('band'))
    print('Blocked:', d.get('blocked'))
else:
    print('Error body:', r.text[:1000])
