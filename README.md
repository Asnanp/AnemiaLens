# AnemiaLens

AnemiaLens is a mobile-first screening app for early anemia risk checks from smartphone eye images. It combines a conjunctiva image-quality gate, a PyTorch screening model, symptom fusion, rule-based triage, grounded GenAI guidance, and clinician-ready handoff output.

This is a screening tool, not a diagnostic device. It is designed to help users decide when to retake an image, when to monitor, and when to seek formal medical follow-up.

## Why this project matters

Anemia is common, but early detection is still limited by cost, distance, and access to laboratory testing. AnemiaLens focuses on a simple real-world workflow:

1. Capture an inner lower eyelid image on a phone.
2. Block unsafe or low-quality inputs before prediction.
3. Estimate screening risk from the eye image.
4. Combine that signal with symptoms.
5. Generate grounded, non-diagnostic next-step guidance.

The goal is not to replace clinical testing. The goal is to create an accessible screening and triage layer that can help people act sooner and more safely.

## Why the GenAI layer is core

AnemiaLens does not use GenAI as cosmetic chat. The GenAI layer is responsible for converting structured medical-AI output into safe, useful guidance.

- It explains the result in plain language.
- It personalizes urgency and food advice from the current screening result.
- It adapts wording using language and region when provided.
- It stays grounded to only the current triage result, uncertainty, symptoms, and locale context.
- It falls back to deterministic rules when live GenAI is unavailable or the screening signal is too weak.

Current provider in this repo:

- `Qwen/Qwen2.5-7B-Instruct` via Hugging Face Inference Providers on the `together` route
- Safe local fallback when Qwen is disabled, unavailable, or intentionally skipped

## System layers

- Image quality and capture: blur, lighting, framing, ROI visibility, retake blocking
- Clinical prediction: anemia risk, hemoglobin estimate, confidence, uncertainty, reliability flag
- Safety and triage: low-risk, moderate-risk, high-concern, uncertain-retake-needed
- Symptom fusion: fatigue, dizziness, pale skin, shortness of breath, heavy menstrual bleeding, low iron intake
- GenAI guidance: grounded explanation, urgency, food advice, next steps
- Handoff and explainability: clinical brief, decision audit, runtime provenance, shareable summary

## Submission docs

- [Impact narrative](./docs/IMPACT_NARRATIVE.md)
- [AI stack and GenAI architecture](./docs/AI_STACK.md)
- [Judge guide](./docs/JUDGE_GUIDE.md)
- [Video script](./docs/VIDEO_SCRIPT.md)
- [Deployment guide](./docs/DEPLOYMENT.md)
- [Submission checklist](./docs/SUBMISSION_CHECKLIST.md)

## Stack

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + Flask compatibility API + Pydantic
- Vision model: PyTorch EfficientNet-B0 checkpoint with archive-model fusion fallback
- GenAI: Qwen 2.5 Instruct through Hugging Face Inference Providers
- Testing: Pytest for backend, TypeScript build checks for frontend

## Quick start

Backend:

```bash
cd backend
pip install -r requirements.txt
python flask_app.py
```

FastAPI alternative:

```bash
cd backend
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

The frontend defaults to `http://127.0.0.1:5000` in development. Override with `VITE_API_BASE_URL` if needed.

## GenAI provider setup

Create `backend/.env` or export these variables:

- `ANEMIALENS_HF_API_KEY`
- `ANEMIALENS_QWEN_MODEL=Qwen/Qwen2.5-7B-Instruct`
- `ANEMIALENS_HF_PROVIDER=together`
- `ANEMIALENS_QWEN_ENABLED=true`

You can start from [backend/.env.example](./backend/.env.example).

PowerShell example:

```powershell
$env:ANEMIALENS_HF_API_KEY="your_key_here"
$env:ANEMIALENS_QWEN_MODEL="Qwen/Qwen2.5-7B-Instruct"
$env:ANEMIALENS_HF_PROVIDER="together"
python flask_app.py
```

## Verification

Backend:

```bash
python -m pytest backend/tests
```

Frontend:

```bash
cd frontend
npm run build
```

## Safety

- Screening only: not a diagnosis and not a substitute for clinical evaluation
- Image quality gating runs before prediction
- Uncertainty and reliability are exposed in the response
- Guidance is constrained to grounded inputs and blocked from diagnostic claims
- Retake-first behavior is preferred over overconfident output
