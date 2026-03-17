# AnemiaLens

AnemiaLens is a mobile-first screening app for early anemia risk detection from smartphone eye images. It combines a conjunctiva image-quality gate, a PyTorch EfficientNet-B0 screening model, symptom fusion, rule-based triage, Mistral AI guidance, and clinician-ready handoff output.

> Anemia affects an estimated 1.92 billion people globally (GBD Study 2021). This is a screening tool, not a diagnostic device.

## How it works

1. Capture an inner lower eyelid image on a phone
2. Image quality gate blocks blurry or poorly lit inputs
3. EfficientNet-B0 estimates anemia risk from conjunctival pallor
4. Symptom signals (fatigue, dizziness, etc.) are fused with image output
5. Four-band triage: Low Risk / Moderate Risk / High Concern / Retake Needed
6. Mistral AI generates personalized, grounded next-step guidance
7. Clinician-ready handoff summary is produced

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript + Vite |
| Backend | Flask + Pydantic |
| Vision model | PyTorch EfficientNet-B0 + archive model fusion |
| GenAI guidance | Mistral AI (`mistral-small-latest`) |
| Testing | Pytest (backend), TypeScript build (frontend) |

## Quick start

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python flask_app.py
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Frontend proxies to `http://127.0.0.1:5000` in dev mode automatically.

## Mistral AI setup

Create `backend/.env`:

```env
ANEMIALENS_MISTRAL_API_KEY=your_mistral_key_here
ANEMIALENS_MISTRAL_MODEL=mistral-small-latest
ANEMIALENS_MISTRAL_ENABLED=true
ANEMIALENS_GUIDANCE_TIMEOUT=20
```

Get a
 free API key at [console.mistral.ai](https://console.mistral.ai).

## Deployment (Render + Vercel)

**Backend → Render:**
1. New Web Service → Deploy from GitHub → select this repo
2. Runtime: Docker, uses `Dockerfile` automatically
3. Add env vars in Render dashboard:
   - `ANEMIALENS_MISTRAL_API_KEY`
   - `ANEMIALENS_MISTRAL_ENABLED=true`
   - `ANEMIALENS_MISTRAL_MODEL=mistral-small-latest`
   - `ANEMIALENS_GUIDANCE_TIMEOUT=20`
   - `PORT=5000`

**Frontend → Vercel:**
1. Import repo on Vercel
2. Build command: `cd frontend && npm install && npm run build`
3. Output directory: `frontend/dist`
4. Add env var: `VITE_API_BASE_URL` = your Render backend URL

## System layers

- Image quality gate: blur, brightness, framing, ROI visibility, retake blocking
- Vision model: anemia risk score, hemoglobin estimate, confidence, uncertainty, reliability flag
- Triage: low-risk / moderate-risk / high-concern / uncertain-retake-needed
- Symptom fusion: fatigue, dizziness, pale skin, shortness of breath, heavy menstrual bleeding, low iron intake
- Mistral AI guidance: explanation, urgency, dietary advice, next steps — grounded to screening data only
- Handoff: clinical brief, decision audit, shareable summary

## Safety

- Screening only — not a diagnosis, not a substitute for clinical evaluation
- Image quality gating runs before any prediction
- Uncertainty and reliability are always exposed in the response
- Mistral guidance is constrained to grounded inputs only — no diagnostic claims allowed
- Retake-first behavior preferred over overconfident output

## Run tests

```bash
cd backend
python -m pytest tests/
```
