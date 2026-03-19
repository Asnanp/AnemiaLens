"""
AnemiaLens FastAPI application — production-grade single entrypoint.

Phase 1 improvements:
- Lifespan context manager with model warm-up and DB table creation.
- Structured JSON logging with per-request trace ID.
- Rate-limiting middleware (token-bucket, in-process).
- Memory guard middleware (gc.collect after inference).
- Hard image-size gate before any decoding (prevents trivial DoS).
- Explicit 413 / 415 responses with clear error messages.
- PyTorch single-threaded for memory-constrained deployments.

Phase 2 improvements:
- Database integration: every screening is persisted.
- Auth routes: register, login, refresh, profile.
- History routes: list, detail, delete past screenings.
- Optional auth on screening endpoints (works anonymous, persists if logged in).
- Admin route stub for future analytics.
"""

from __future__ import annotations

import gc
import json
import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Request, UploadFile, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import UnidentifiedImageError

from app.config import BACKEND_ROOT, settings
from app.ml.features import load_image_bytes
from app.schemas import AnalyzeResponse, QualityCheckResponse, RuntimeStatusResponse
from app.services.analysis_meta import build_analysis_meta
from app.services.case_insight import CaseInsightService
from app.services.clinical_brief import ClinicalBriefService
from app.services.decision_audit import build_decision_audit
from app.services.guidance import GuidanceService
from app.services.handoff import HandoffSummaryService
from app.services.image_quality import ImageQualityService
from app.services.prediction import ScreeningPredictor
from app.services.request_parsing import (
    InvalidRequestPayload,
    normalize_optional_text,
    parse_symptoms,
)
from app.services.runtime_status import build_runtime_status
from app.services.triage import TriageService

load_dotenv(BACKEND_ROOT / ".env")

# ---------------------------------------------------------------------------
# Ensure PyTorch uses minimal threads (BEFORE any torch import in services)
# ---------------------------------------------------------------------------
try:
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
except Exception:
    pass

# ---------------------------------------------------------------------------
# Structured JSON Logging
# ---------------------------------------------------------------------------

class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "ts": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
                "request_id": getattr(record, "request_id", None),
            },
            ensure_ascii=False,
        )


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_JSONFormatter())
logging.root.handlers = [_handler]
logging.root.setLevel(getattr(logging, settings.log_level))

log = logging.getLogger("anemialens")


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("AnemiaLens starting up …")

    # ---------- Database ----------
    from app.database import create_tables
    await create_tables()
    log.info("Database tables ensured.")

    # ---------- ML Services ----------
    app.state.quality_service = ImageQualityService()
    app.state.predictor = ScreeningPredictor()
    app.state.triage_service = TriageService()
    app.state.guidance_service = GuidanceService()
    app.state.case_insight_service = CaseInsightService()
    app.state.clinical_brief_service = ClinicalBriefService()
    app.state.handoff_service = HandoffSummaryService()
    log.info("All ML services initialised.")

    # ---------- Model warm-up ----------
    if app.state.predictor.is_ready():
        try:
            from PIL import Image
            import numpy as np
            dummy = Image.fromarray(
                np.random.randint(80, 200, (120, 200, 3), dtype=np.uint8), mode="RGB"
            )
            from app.schemas import QualityAssessment
            dummy_quality = QualityAssessment(
                passed=True, blur_score=100.0, brightness_score=0.3,
                contrast_score=0.15, framing_score=1.5, issues=[],
            )
            app.state.predictor.predict(dummy, dummy_quality)
            gc.collect()
            log.info("Model warm-up complete — first inference latency eliminated.")
        except Exception as exc:
            log.warning("Model warm-up failed (non-fatal): %s", exc)

    yield

    log.info("AnemiaLens shutting down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AnemiaLens API",
    version="1.0.0",
    description=(
        "Conjunctiva-based anemia screening API with authentication, "
        "scan history, and AI-powered guidance. "
        "All predictions are screening aids only — not medical diagnoses."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Middleware stack (order matters — outermost first)
# ---------------------------------------------------------------------------

# 1. CORS
# Explicitly allowing common Vercel/localhost origins to satisfy allow_credentials=True.
# If on a different Vercel preview domain, the wildcard '*' + credentials=False can also work,
# but for auth we generally prefer specific origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://anemialens.vercel.app",
        "https://anemia-lens.vercel.app",
        "https://asnanp.github.io",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Rate limiting
from app.middleware.rate_limit import RateLimitMiddleware
app.add_middleware(
    RateLimitMiddleware,
    analyze_rpm=10,
    quality_rpm=30,
    default_rpm=60,
)

# 3. Memory guard
from app.middleware.memory_guard import MemoryGuardMiddleware
app.add_middleware(MemoryGuardMiddleware)


# ---------------------------------------------------------------------------
# Middleware — request ID + timing
# ---------------------------------------------------------------------------

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    request.state.started_at = time.perf_counter()

    response = await call_next(request)

    elapsed_ms = (time.perf_counter() - request.state.started_at) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"

    log.info(
        "%s %s → %d (%.1fms) [%s]",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        request_id,
    )
    return response


# ---------------------------------------------------------------------------
# Include API route modules (Phase 2 & 3)
# ---------------------------------------------------------------------------

from app.api.auth import router as auth_router
from app.api.history import router as history_router
from app.api.admin import router as admin_router
from app.api.billing import router as billing_router

app.include_router(auth_router)
app.include_router(history_router)
app.include_router(admin_router)
app.include_router(billing_router)


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------

def _image_error_response(request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        content={
            "error": "The uploaded file is not a valid image.",
            "detail": "Please upload a JPEG or PNG photo of the inner lower eyelid.",
            "request_id": request_id,
        },
    )


def _too_large_response(request_id: str, max_mb: float) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        content={
            "error": f"Image exceeds the {max_mb:.0f} MB size limit.",
            "request_id": request_id,
        },
    )


def _attempt_raw_frame_rescue(services, image_bytes: bytes, quality):
    if quality.passed or not services.quality_service.allows_raw_frame_rescue(quality):
        return quality, None, False

    raw_image = load_image_bytes(image_bytes).convert("RGB")
    raw_prediction = services.predictor.predict(raw_image, quality)
    if not services.predictor.should_accept_raw_frame_rescue(raw_prediction):
        return quality, None, False

    rescued_quality = services.quality_service.build_raw_frame_rescue_assessment(quality)
    return rescued_quality, raw_prediction, True


# ---------------------------------------------------------------------------
# Screening persistence helper (Phase 2)
# ---------------------------------------------------------------------------

async def _persist_screening(
    request_id: str,
    analysis: AnalyzeResponse,
    user_id: int | None,
    processing_time_ms: float,
) -> None:
    """Save the screening result to the database."""
    try:
        from app.database import async_session_factory
        from app.models.screening import Screening

        screening = Screening(
            request_id=request_id,
            user_id=user_id,
            triage_band=analysis.triage.band,
            triage_score=analysis.triage.score,
            triage_label=analysis.triage.label,
            anemia_risk=analysis.prediction.anemia_risk if analysis.prediction else None,
            predicted_hemoglobin=analysis.prediction.predicted_hemoglobin if analysis.prediction else None,
            confidence=analysis.prediction.confidence if analysis.prediction else None,
            uncertainty=analysis.prediction.uncertainty if analysis.prediction else None,
            screening_label=analysis.prediction.screening_label if analysis.prediction else None,
            model_source=analysis.prediction.model_source if analysis.prediction else None,
            quality_passed=analysis.quality.passed,
            blocked=analysis.blocked,
            processing_path=analysis.decision_audit.processing_path,
            guidance_source=analysis.guidance.source,
            symptoms_json=json.dumps(analysis.symptoms.model_dump()),
            full_response_json=json.dumps(analysis.model_dump(), default=str),
            share_text=analysis.handoff_summary.share_text,
            urgency_label=analysis.handoff_summary.urgency_label,
            headline=analysis.handoff_summary.headline,
            processing_time_ms=processing_time_ms,
            language=analysis.language,
            region=analysis.region,
        )

        async with async_session_factory() as session:
            session.add(screening)
            await session.commit()

            # Update user scan count
            if user_id is not None:
                from app.models.user import User
                from sqlalchemy import select
                result = await session.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if user:
                    user.scan_count += 1
                    await session.commit()

    except Exception as exc:
        log.warning("Failed to persist screening (non-fatal): %s", exc)


# ---------------------------------------------------------------------------
# Routes — Health / Meta
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"], summary="Liveness probe")
async def health(request: Request) -> dict[str, object]:
    """Returns 200 OK when the server is alive."""
    guidance_status = request.app.state.guidance_service.runtime_status()
    return {
        "status": "ok",
        "model_ready": request.app.state.predictor.is_ready(),
        "guidance_strategy": guidance_status.active_strategy,
    }


@app.get("/readyz", tags=["meta"], summary="Readiness probe")
async def readyz(request: Request) -> JSONResponse:
    predictor = request.app.state.predictor
    guidance_status = request.app.state.guidance_service.runtime_status()
    ready = predictor.is_ready()
    return JSONResponse(
        status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "ready" if ready else "degraded",
            "model_ready": ready,
            "guidance_client_ready": guidance_status.client_ready,
            "guidance_strategy": guidance_status.active_strategy,
            "guidance_fallback_reason": guidance_status.fallback_reason,
        },
    )


@app.get(
    "/api/runtime-status",
    response_model=RuntimeStatusResponse,
    tags=["meta"],
    summary="Model and guidance runtime information",
)
async def runtime_status(request: Request) -> RuntimeStatusResponse:
    return build_runtime_status(
        request.app.state.predictor,
        request.app.state.guidance_service,
    )


# ---------------------------------------------------------------------------
# Routes — Screening
# ---------------------------------------------------------------------------

@app.post(
    "/api/quality-check",
    response_model=QualityCheckResponse,
    tags=["screening"],
    summary="Assess image quality before full analysis",
    status_code=status.HTTP_200_OK,
)
async def quality_check(
    request: Request,
    image: Annotated[UploadFile, File(description="Eye photo (JPEG or PNG).")],
) -> QualityCheckResponse | JSONResponse:
    rid = request.state.request_id
    image_bytes = await image.read()

    if len(image_bytes) > settings.max_image_bytes:
        return _too_large_response(rid, settings.max_image_bytes / 1024 / 1024)

    try:
        quality, _ = request.app.state.quality_service.evaluate(image_bytes)
    except (UnidentifiedImageError, ValueError):
        return _image_error_response(rid)

    return QualityCheckResponse(quality=quality)


@app.post(
    "/api/analyze",
    response_model=AnalyzeResponse,
    tags=["screening"],
    summary="Full conjunctiva screening pipeline",
    status_code=status.HTTP_200_OK,
)
async def analyze(
    request: Request,
    image: Annotated[UploadFile, File(description="Eye photo (JPEG or PNG).")],
    symptoms: Annotated[str | None, Form(description="JSON-encoded symptom flags.")] = None,
    language: Annotated[str | None, Form(description="Preferred language for guidance.")] = None,
    region: Annotated[str | None, Form(description="Geographic region for localised guidance.")] = None,
) -> AnalyzeResponse | JSONResponse:
    """
    Full pipeline: quality gate → ML inference → triage → guidance → insight packs.
    Works for both authenticated and anonymous users.
    Authenticated users get their results persisted to scan history.
    """
    rid = request.state.request_id
    svc = request.app.state

    from app.database import async_session_factory

    # --- Optional auth (get user if token present) -------------------------
    user_id: int | None = None
    user_tier: str = "free"
    user_scan_count: int = 0
    try:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            from app.utils.security import decode_token
            payload = decode_token(token)
            if payload and payload.get("type") == "access":
                from sqlalchemy import select
                from app.models.user import User
                async with async_session_factory() as session:
                    result = await session.execute(
                        select(User).where(User.uid == payload.get("sub"))
                    )
                    user = result.scalar_one_or_none()
                    if user and user.is_active:
                        user_id = user.id
                        user_tier = user.subscription_tier or "free"
                        user_scan_count = user.scan_count or 0
    except Exception:
        pass  # Anonymous is fine

    # --- Scan limit enforcement (free = 10 scans) --------------------------
    FREE_SCAN_LIMIT = 10
    if user_id is not None and user_tier == "free" and user_scan_count >= FREE_SCAN_LIMIT:
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content={
                "error": f"Free plan limit reached ({FREE_SCAN_LIMIT} scans). Upgrade to Pro for unlimited screenings.",
                "upgrade_required": True,
                "request_id": rid,
            },
        )

    # --- Input validation --------------------------------------------------
    try:
        symptom_input = parse_symptoms(symptoms)
        language = normalize_optional_text(language, field_name="language")
        region = normalize_optional_text(region, field_name="region")
    except InvalidRequestPayload as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": str(exc), "request_id": rid},
        )

    # --- Image loading ------------------------------------------------------
    image_bytes = await image.read()

    if len(image_bytes) > settings.max_image_bytes:
        return _too_large_response(rid, settings.max_image_bytes / 1024 / 1024)

    try:
        quality, rgb = svc.quality_service.evaluate(image_bytes)
    except (UnidentifiedImageError, ValueError):
        return _image_error_response(rid)

    # --- Inference (skipped on quality failure) -----------------------------
    prediction = svc.predictor.predict(rgb, quality) if quality.passed else None
    used_raw_frame_rescue = False
    if prediction is None:
        quality, prediction, used_raw_frame_rescue = _attempt_raw_frame_rescue(svc, image_bytes, quality)

    # --- Triage + guidance -------------------------------------------------
    signal_breakdown = svc.triage_service.build_signal_breakdown(quality, prediction, symptom_input)
    triage = svc.triage_service.assess(
        quality,
        prediction,
        symptom_input,
        signal_breakdown=signal_breakdown,
    )
    decision_audit = build_decision_audit(
        quality,
        prediction,
        triage,
        used_raw_frame_rescue=used_raw_frame_rescue,
    )
    guidance = svc.guidance_service.generate(
        triage, symptom_input, prediction, language, region
    )
    insight_pack = svc.case_insight_service.build(
        quality,
        prediction,
        triage,
        decision_audit,
        guidance,
        symptom_input,
    )
    handoff_summary = svc.handoff_service.build(
        quality,
        prediction,
        triage,
        guidance,
        symptom_input,
        language,
        region,
    )
    clinical_brief = svc.clinical_brief_service.build(
        quality,
        prediction,
        triage,
        decision_audit,
        guidance,
        symptom_input,
        insight_pack,
        handoff_summary,
        signal_breakdown,
    )

    processing_time_ms = (time.perf_counter() - request.state.started_at) * 1000

    analysis_meta = build_analysis_meta(
        request_id=rid,
        api_version=app.version,
        processing_time_ms=processing_time_ms,
        quality=quality,
        decision_audit=decision_audit,
        guidance=guidance,
        used_raw_frame_rescue=used_raw_frame_rescue,
    )

    response = AnalyzeResponse(
        blocked=not quality.passed,
        quality=quality,
        prediction=prediction,
        decision_audit=decision_audit,
        triage=triage,
        guidance=guidance,
        insight_pack=insight_pack,
        clinical_brief=clinical_brief,
        handoff_summary=handoff_summary,
        analysis_meta=analysis_meta,
        symptoms=symptom_input,
        language=language,
        region=region,
    )

    # --- Persist to database (async, non-blocking) -------------------------
    import asyncio
    asyncio.create_task(
        _persist_screening(rid, response, user_id, processing_time_ms)
    )

    return response
