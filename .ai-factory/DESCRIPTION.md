# AnemiaLens - Project Description

## Overview
AnemiaLens is an AI-powered medical screening platform that detects anemia through conjunctival image analysis. It combines advanced ML (EfficientNet, ensemble models) with clinical triage to provide accessible health screening.

## Tech Stack

### Frontend
- **React 18** + **TypeScript**
- **Vite 5** bundler
- **React Router DOM v7** (SPA with modal overlays)
- **Framer Motion** + **Three.js** for animations
- **Tailwind CSS v4** + Radix UI primitives
- **i18next** (en, es, hi)
- **Supabase** client (optional)
- **Stripe** for billing

### Backend
- **FastAPI** (Python async)
- **SQLAlchemy 2.0** async ORM
- **PostgreSQL** (Supabase) / SQLite (dev)
- **PyTorch 2.10** (CPU) + **scikit-learn 1.6.1**
- **OpenCV** + **Pillow** for image processing
- **Mistral AI** for clinical guidance
- **Redis** (optional) for rate limiting
- **Stripe** for subscriptions

## Core Features
- 4-step screening workflow (Capture → Quality → Intake → Result)
- ML-powered anemia detection with confidence scoring
- Clinical brief and AI guidance generation
- User authentication (email + Google OAuth)
- Screening history with export capabilities
- Multi-language support
- Offline mode fallback

## Scale Requirements
- Enterprise-grade security and compliance (HIPAA-ready)
- High availability (99.9% uptime)
- Support for 100K+ concurrent users
- Multi-tenant architecture capability
- Real-time processing (<5s response time)
- Global CDN and edge computing

## Architecture
See `.ai-factory/ARCHITECTURE.md` for detailed architecture guidelines.
Pattern: Clean Architecture + Modular Monolith (hybrid for medical AI)
