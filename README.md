<div align="center">

<img src="https://img.shields.io/badge/AnemiaLens-AI%20Screening-C8001E?style=for-the-badge&logoColor=white" />

# AnemiaLens

### Non-invasive anemia screening using smartphone camera + AI

**No lab. No needle. No waiting.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-anemialens.vercel.app-C8001E?style=flat-square)](https://anemialens.vercel.app)
[![Backend](https://img.shields.io/badge/Backend-Hugging%20Face%20Spaces-46E3B7?style=flat-square)](https://asnanp1-anemialens.hf.space/health)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)](https://react.dev)

</div>

---

## What is AnemiaLens?

AnemiaLens turns a smartphone camera into a first-pass anemia screening tool. It analyzes the color and pallor of the inner lower eyelid and combines that signal with a symptom survey to produce an instant risk assessment.

> **1.92 billion people** are affected by anemia globally. Most cases go undetected because lab testing requires access, cost, and time that many communities do not have.

---

## Demo

| Step | Description |
|------|-------------|
| Upload | Take or upload a photo of the inner lower eyelid |
| Quality Check | AI validates image clarity, lighting, and framing |
| Symptoms | Answer a short symptom survey |
| Analysis | Multi-stage ML pipeline produces risk score and hemoglobin estimate |
| Result | Get risk level, explainability, and grounded clinical guidance |

**Frontend:** [https://anemialens.vercel.app](https://anemialens.vercel.app)  
**Backend health:** [https://asnanp1-anemialens.hf.space/health](https://asnanp1-anemialens.hf.space/health)  
**Backend docs:** [https://asnanp1-anemialens.hf.space/docs](https://asnanp1-anemialens.hf.space/docs)

---

## Tech Stack

### Backend
- **FastAPI** for the API
- **SQLAlchemy + asyncpg** for persistence
- **PostgreSQL (Supabase)** for production data
- **PyTorch + EfficientNet-B0** for vision inference
- **scikit-learn** for ensemble models
- **Mistral AI** for grounded clinical guidance
- **JWT** for authentication
- **Hugging Face Spaces** for backend hosting

### Frontend
- **React 18 + TypeScript**
- **Vite**
- **Framer Motion**
- **Three.js**
- **Vercel** for frontend hosting

---

## Features

### Core
- Guided multi-step screening flow
- Image quality validation before analysis
- Risk levels: Low / Moderate / High Concern / Retake Needed
- Hemoglobin estimate with uncertainty handling
- Explainability panel with signal breakdown
- Clinical safety language and retake guidance

### Product
- Guest-first screening flow
- Auth, history, and admin surfaces
- Export and share actions
- Doctor view / user view result modes
- Dashboard and admin analytics

---

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python start_server.py
```

Or run directly:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

---

## Deployment

### Backend -> Hugging Face Spaces

1. Create a **Docker Space**
2. Upload the repo `Dockerfile` and the `backend/` directory to the Space
3. Set the Space metadata to use `app_port: 5000`
4. Add the required secrets:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Your Supabase transaction pooler URL |
| `JWT_SECRET_KEY` | A long random string |
| `JWT_ALGORITHM` | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `30` |
| `ANEMIALENS_MISTRAL_API_KEY` | Your Mistral API key |
| `ANEMIALENS_MISTRAL_ENABLED` | `true` |
| `ANEMIALENS_MISTRAL_MODEL` | `mistral-small-latest` |
| `ANEMIALENS_GUIDANCE_TIMEOUT` | `20` |
| `PORT` | `5000` |

### Frontend -> Vercel

1. Connect the GitHub repo to Vercel
2. Build from the repo root
3. The root `vercel.json` rewrites `/api`, `/health`, and `/api/runtime-status` to the Hugging Face backend

---

## Project Structure

```text
AnemiaLens/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── ml/
│   │   ├── models/
│   │   ├── services/
│   │   ├── middleware/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── models/
│   └── start_server.py
├── frontend/
│   ├── src/
│   └── tests/
├── vercel.json
└── archive/
```

---

## Notes

- The backend host is **Hugging Face Spaces**.
- The frontend proxy is already configured for the live Hugging Face backend.
- Gmail SMTP on port `465` is not suitable for Hugging Face Spaces because of outbound port restrictions, so hosted email delivery should use an HTTPS email provider later.

---

## Disclaimer

AnemiaLens is a screening aid only and does not diagnose anemia or replace the advice of a qualified medical professional.

---

<div align="center">

**Because a photo should be enough to save a life.**

[Live Demo](https://anemialens.vercel.app) · [Backend API](https://asnanp1-anemialens.hf.space/docs) · [GitHub](https://github.com/Asnanp/AnemiaLens)

</div>
