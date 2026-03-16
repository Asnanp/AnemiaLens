# Deployment

## Local setup

### Backend

```bash
cd backend
pip install -r requirements.txt
python flask_app.py
```

FastAPI option:

```bash
cd backend
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Required environment variables

Start from `backend/.env.example`.

Core GenAI variables:

- `ANEMIALENS_HF_API_KEY`
- `ANEMIALENS_QWEN_MODEL`
- `ANEMIALENS_HF_PROVIDER` with value `together`
- `ANEMIALENS_QWEN_ENABLED`

Useful runtime variables:

- `ANEMIALENS_GUIDANCE_TIMEOUT`
- `ANEMIALENS_GUIDANCE_MAX_TOKENS`
- `ANEMIALENS_LOG_LEVEL`

## Production deployment shape

Frontend:

- deploy as a static React app
- point `VITE_API_BASE_URL` to the backend URL

Backend:

- deploy FastAPI or Flask behind a standard Python web process
- ensure model artifacts remain available under `backend/models/`
- configure the Hugging Face API token in the production environment

## Recommended deployment checks

Before submission, verify:

```bash
python -m pytest backend/tests
cd frontend && npm run build
```

Then verify in the deployed app:

1. `/health` returns OK
2. `/api/runtime-status` shows the loaded model and guidance strategy
3. `/api/quality-check` blocks weak images
4. `/api/analyze` returns guidance, insight, handoff, and clinical brief objects

## Demo reliability tips

- Keep one known-good sample image ready
- Keep one intentionally bad sample image ready
- Preconfigure the GenAI API key before recording
- If live GenAI fails, show that the fallback still preserves safe next steps
