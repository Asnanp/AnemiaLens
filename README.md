<div align="center">

<img src="https://img.shields.io/badge/AnemiaLens-AI%20Screening-C8001E?style=for-the-badge&logoColor=white" />

# AnemiaLens

### Non-invasive anemia screening using smartphone camera + AI

**No lab. No needle. No waiting.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-anemialens.vercel.app-C8001E?style=flat-square)](https://anemialens.vercel.app)
[![Backend](https://img.shields.io/badge/Backend-Render-46E3B7?style=flat-square)](https://anemialens-3.onrender.com/health)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)](https://react.dev)

</div>

---

## What is AnemiaLens?

AnemiaLens turns a smartphone camera into a **first-pass anemia screening tool**. It analyzes the color and pallor of the inner lower eyelid (palpebral conjunctiva) — a signal clinicians have used for decades — and combines it with a symptom survey to produce an instant risk assessment.

> **1.92 billion people** are affected by anemia globally. Most cases go undetected because lab testing requires access, cost, and time that many communities don't have. AnemiaLens is designed to change that.

---

## Demo

| Step | Description |
|------|-------------|
| 📸 Upload | Take or upload a photo of the inner lower eyelid |
| 🔍 Quality Check | AI validates image clarity, lighting, and framing |
| 📋 Symptoms | Answer a short symptom survey (fatigue, dizziness, diet, etc.) |
| 🧠 Analysis | 7-layer ML pipeline produces risk score + hemoglobin estimate |
| 📄 Result | Get risk level, signal breakdown, and Mistral AI clinical guidance |

**Try it:** [anemialens.vercel.app](https://anemialens.vercel.app)

---

## The Science

The inner lower eyelid becomes pale when hemoglobin drops. This is called **conjunctival pallor** and is a well-established clinical sign of anemia. AnemiaLens teaches a computer vision model to read this signal from a smartphone photo.

```
Conjunctival pallor → Color feature extraction → Risk score
```

Trained on **710 real clinical specimens** from the India conjunctiva dataset.

---

## Architecture

### 7-Layer Pipeline

```
01 Image Capture
      ↓
02 Feature Extraction     (CPI, redness uniformity, green-blue ratio)
      ↓
03 EfficientNet-B0        (fine-tuned on 710 conjunctival specimens)
      ↓
04 Clinical Ensemble      (ExtraTrees 500 trees + classifier 700 trees)
      ↓
05 Confidence Fusion      (isotonic calibration + Platt scaling)
      ↓
06 Symptom Fusion         (learned MLP fusion model)
      ↓
07 Mistral AI             (clinical narrative generation)
```

### ML Modules

| Module | Purpose |
|--------|---------|
| `calibration.py` | Temperature scaling, isotonic calibration, Platt scaling, ECE |
| `uncertainty.py` | MC Dropout, ensemble uncertainty, retake trigger |
| `roi_confidence.py` | ROI extraction confidence scoring |
| `learned_fusion.py` | Pure numpy MLP for symptom+vision fusion |
| `augmentation.py` | Conjunctiva-specific data augmentation pipeline |
| `lightweight_model.py` | MobileNetV2-based fallback model |

### Safety Design

> "Confidence is dangerous. Uncertainty is a feature."

- **Image quality gate** — blocks bad inputs before any model runs
- **Uncertainty score** — exposed on every prediction
- **Hemoglobin hidden** — when uncertainty ≥ 70%
- **Mistral output filtered** — regex safety filter blocks diagnostic claims
- **NOT A DIAGNOSIS** — screening aid only

---

## Tech Stack

### Backend
- **FastAPI** — async Python API
- **SQLAlchemy + asyncpg** — async ORM
- **PostgreSQL** (Supabase) — production database
- **PyTorch + EfficientNet-B0** — vision model
- **scikit-learn** — ensemble models
- **Mistral AI** (`mistral-small-latest`) — clinical guidance
- **JWT** — authentication
- **Render** — deployment

### Frontend
- **React 18 + TypeScript** — UI framework
- **Vite** — build tool
- **Framer Motion** — animations
- **Three.js** — 3D background
- **Vercel** — deployment

---

## Features

### Core
- 4-step guided screening flow
- Image quality validation before analysis
- Risk levels: Low / Moderate / High Concern
- Hemoglobin estimate with uncertainty range
- Signal breakdown explainability panel
- Emergency alert for high-risk results

### AI
- Mistral AI clinical guidance panel
- Offline fallback (symptom-only assessment)
- Clinical mode toggle
- Share with provider (clipboard)

### SaaS
- JWT authentication (register / login)
- Free tier: 10 scans/month
- Pro tier: unlimited scans
- Stripe demo checkout
- Scan history with CSV export
- HbA sparkline trend chart
- Admin dashboard (user management, stats)

### Accessibility
- Hindi language toggle for symptoms
- Guest mode (no account required)
- Auth gate with sign-in or guest option
- Offline mode banner + fallback

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:
```env
DATABASE_URL=sqlite+aiosqlite:///./anemialens.db
JWT_SECRET_KEY=your-secret-key-here
ANEMIALENS_MISTRAL_API_KEY=your-mistral-key
ANEMIALENS_MISTRAL_ENABLED=true
ANEMIALENS_MISTRAL_MODEL=mistral-small-latest
STRIPE_PRO_PRICE_ID=price_demo_pro_monthly
```

```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:
```env
VITE_API_BASE_URL=http://localhost:8000
```

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

---

## Deployment

### Backend → Render

1. Connect your GitHub repo to Render
2. Set **Root Directory** to `backend`
3. Set **Start Command** to `python start_render.py`
4. Add environment variables:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Your Supabase transaction pooler URL |
| `JWT_SECRET_KEY` | A long random string |
| `ANEMIALENS_MISTRAL_API_KEY` | Your Mistral API key |
| `ANEMIALENS_MISTRAL_ENABLED` | `true` |
| `ANEMIALENS_MISTRAL_MODEL` | `mistral-small-latest` |
| `STRIPE_PRO_PRICE_ID` | `price_demo_pro_monthly` |

### Frontend → Vercel

1. Connect your GitHub repo to Vercel
2. Set **Root Directory** to `frontend`
3. Vercel auto-detects Vite — no extra config needed
4. The `vercel.json` in the repo root handles API proxying to Render

---

## Project Structure

```
AnemiaLens/
├── backend/
│   ├── app/
│   │   ├── api/          # Auth, history, billing, admin routes
│   │   ├── ml/           # ML modules (calibration, uncertainty, fusion...)
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── services/     # Triage, prediction, guidance, ROI extraction
│   │   ├── middleware/   # Rate limiting, memory guard
│   │   ├── config.py     # Settings (pydantic-settings)
│   │   ├── database.py   # Async SQLAlchemy engine
│   │   └── main.py       # FastAPI app entrypoint
│   ├── models/           # Trained model artifacts (.pth, .joblib)
│   └── start_render.py   # Render startup script
├── frontend/
│   ├── src/
│   │   ├── components/   # UI components (UploadZone, ResultView, etc.)
│   │   ├── hooks/        # useScreening, useAuth, useStats
│   │   ├── pages/        # Dashboard, Admin, Landing sections
│   │   ├── api.ts        # API client with auth token injection
│   │   └── App.tsx       # App shell + auth gate
│   └── vite.config.ts
├── vercel.json           # Vercel rewrites → Render proxy
└── archive/
    └── dataset anemia/   # India conjunctiva dataset (710 specimens)
```

---

## Built With GenAI Tools

| Tool | Role |
|------|------|
| **Kiro IDE** | Built the full React frontend with AI-native UI/UX design system |
| **OpenAI Codex** | Wrote and debugged the FastAPI backend, ML pipeline, API routes |
| **Mistral AI** | Powers real-time clinical guidance inside the product |

> *"I built this in 6 days. Codex handled the backend. Kiro handled the frontend. That freed me to focus on what actually matters — the medical AI pipeline."*

---

## Dataset

The model was trained on the **India Conjunctiva Dataset** — 710 real clinical specimens collected from patients in India, with labeled hemoglobin values and anemia status. Each sample includes:
- Full eye photograph
- Forniceal conjunctiva crop
- Palpebral conjunctiva crop
- Combined crop

Located in `archive/dataset anemia/India/`

---

## Disclaimer

> AnemiaLens is a **screening aid only** and does not diagnose anemia or replace the advice of a qualified medical professional. Always consult a doctor for diagnosis and treatment.

---

## License

MIT © 2026 [Asnanp](https://github.com/Asnanp)

---

<div align="center">

**Because a photo should be enough to save a life.**

[Live Demo](https://anemialens.vercel.app) · [Backend API](https://anemialens-3.onrender.com/docs) · [GitHub](https://github.com/Asnanp/AnemiaLens)

</div>
