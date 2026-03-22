<div align="center">

<img src="https://img.shields.io/badge/AnemiaLens-AI%20Screening-C8001E?style=for-the-badge&logoColor=white" />

# AnemiaLens

### Non-invasive anemia screening using smartphone camera + AI

**No lab. No needle. No waiting.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-anemia--lens.vercel.app-C8001E?style=flat-square)](https://anemia-lens.vercel.app)
[![Backend](https://img.shields.io/badge/Backend-Hugging%20Face%20Spaces-46E3B7?style=flat-square)](https://asnannp-anemialens.hf.space/health)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)](https://react.dev)

</div>

---

## What is AnemiaLens?

AnemiaLens turns a smartphone camera into a first-pass anemia screening tool. It analyzes conjunctival pallor from the inner lower eyelid, combines that visual signal with symptom context, and returns a grounded risk assessment in seconds.

> **1.92 billion people** are affected by anemia globally. Many cases stay undetected because lab testing still depends on access, cost, and time that many communities do not have.

The current live product is built around four trust signals:
- quality-gated capture before prediction
- lighting-aware screening with glare and shadow detection
- confidence breakdown instead of a single opaque score
- one-click report sharing by email from the live app

---

## Demo

| Step | Description |
|------|-------------|
| Upload | Take or upload a photo of the inner lower eyelid |
| Quality Check | AI scores sharpness, framing, lighting balance, glare risk, and shadow risk |
| Symptoms | Answer a short symptom survey |
| Analysis | Multi-stage ML pipeline produces risk score, hemoglobin estimate, and confidence breakdown |
| Result | Get risk level, explainability, grounded clinical guidance, and an email-ready report |

**Frontend:** [https://anemia-lens.vercel.app](https://anemia-lens.vercel.app)  
**Backend health:** [https://asnannp-anemialens.hf.space/health](https://asnannp-anemialens.hf.space/health)  
**Backend docs:** [https://asnannp-anemialens.hf.space/docs](https://asnannp-anemialens.hf.space/docs)

---

## Tech Stack

### Backend
- **FastAPI** for the API
- **SQLAlchemy + asyncpg** for persistence
- **PostgreSQL (Supabase)** for production data
- **PyTorch + EfficientNet-B0** for vision inference
- **scikit-learn** for fusion and ensemble models
- **Mistral AI** for grounded clinical guidance
- **Gmail API** for hosted email report delivery
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
- Lighting intelligence with balanced, dim, overexposed, glare-heavy, and shadow-heavy states
- Risk levels: Low / Moderate / High Concern / Retake Needed
- Hemoglobin estimate with uncertainty handling
- Confidence breakdown across capture quality, model stability, and decision margin
- Explainability panel with signal breakdown
- Clinical safety language and retake guidance
- Email-ready screening report sent from the live app

### Product
- Guest-first screening flow
- Supabase-backed account login and registration
- Guest-to-account save flow for the current screening
- Auth, history, and admin surfaces
- Export and share actions
- Doctor view and user view result modes
- Dashboard and admin analytics
- Saved case history with account-level trend tracking

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
| `ANEMIALENS_EMAIL_PROVIDER` | `gmail_api` |
| `ANEMIALENS_GMAIL_CLIENT_ID` | Google OAuth client ID |
| `ANEMIALENS_GMAIL_CLIENT_SECRET` | Google OAuth client secret |
| `ANEMIALENS_GMAIL_REFRESH_TOKEN` | Gmail refresh token with `gmail.send` scope |
| `ANEMIALENS_EMAIL_FROM_NAME` | `AnemiaLens` |
| `ANEMIALENS_EMAIL_FROM_EMAIL` | Your verified Gmail address |
| `ANEMIALENS_EMAIL_REPLY_TO` | Your verified Gmail address |
| `PORT` | `5000` |

5. Apply the SQL schema from `backend/supabase_schema.sql` to the target Supabase database before first login
6. Auth, history, and save-to-account flows depend on the Supabase Postgres database being available at startup

### Frontend -> Vercel

1. Connect the GitHub repo to Vercel
2. Build from the repo root
3. The root `vercel.json` rewrites `/api`, `/health`, and `/api/runtime-status` to the Hugging Face backend

---

## Project Structure

```text
AnemiaLens/
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |-- ml/
|   |   |-- models/
|   |   |-- services/
|   |   |-- middleware/
|   |   |-- config.py
|   |   |-- database.py
|   |   `-- main.py
|   |-- models/
|   `-- start_server.py
|-- frontend/
|   |-- src/
|   `-- tests/
|-- vercel.json
`-- archive/
```

---

## Notes

- The backend host is **Hugging Face Spaces**.
- The frontend proxy is already configured for the live Hugging Face backend.
- Hosted email delivery now uses **Gmail API over HTTPS**, which fits Hugging Face Spaces outbound networking rules.
- The result page is designed to keep the main story short: result, why it happened, confidence, next step, and actions.
- The quality gate is intentionally stricter than a simple blur check because judges and clinicians trust systems that know when the image is weak.

---

## Disclaimer

AnemiaLens is a screening aid only and does not diagnose anemia or replace the advice of a qualified medical professional.

---

<div align="center">

**Because a photo should be enough to save a life.**

[Live Demo](https://anemia-lens.vercel.app) | [Backend API](https://asnannp-anemialens.hf.space/docs) | [GitHub](https://github.com/Asnanp/AnemiaLens)

</div>
