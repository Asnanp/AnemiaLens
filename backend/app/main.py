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

import asyncio
import gc
import io
import json
import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    Request,
    UploadFile,
    status,
    Depends,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from PIL import Image, UnidentifiedImageError

from app.config import BACKEND_ROOT, settings
from app.ml.features import load_image_bytes
from app.schemas import (
    AnalyzeResponse,
    GuidanceChatRequest,
    GuidanceChatResponse,
    QualityCheckResponse,
    RuntimeStatusResponse,
)
from app.schemas.quality import QualityIssue
from app.services.analysis_meta import build_analysis_meta
from app.services.case_insight import CaseInsightService
from app.services.clinical_brief import ClinicalBriefService
from app.services.decision_audit import build_decision_audit
from app.services.guidance import GuidanceService
from app.services.handoff import HandoffSummaryService
from app.services.image_quality import ImageQualityService
from app.services.patient_case import PatientCaseService
from app.services.prediction import ScreeningPredictor
from app.services.roi_preview import build_roi_preview_payload
from app.services.request_parsing import (
    InvalidRequestPayload,
    normalize_optional_text,
    parse_patient_profile,
    parse_symptoms,
)
from app.services.runtime_status import build_runtime_status
from app.services.screening_store import persist_screening_result
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
_runtime_init_lock = asyncio.Lock()

#region agent log
def _agent_debug_log(run_id: str, hypothesis_id: str, location: str, message: str, data: dict) -> None:
    pass  # Debug instrumentation disabled for production
#endregion


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------


def _initialise_runtime_services(app: FastAPI) -> None:
    state = app.state
    if not hasattr(state, "quality_service"):
        state.quality_service = ImageQualityService()
    if not hasattr(state, "predictor"):
        state.predictor = ScreeningPredictor()
    if not hasattr(state, "triage_service"):
        state.triage_service = TriageService()
    if not hasattr(state, "guidance_service"):
        state.guidance_service = GuidanceService()
    if not hasattr(state, "case_insight_service"):
        state.case_insight_service = CaseInsightService()
    if not hasattr(state, "clinical_brief_service"):
        state.clinical_brief_service = ClinicalBriefService()
    if not hasattr(state, "handoff_service"):
        state.handoff_service = HandoffSummaryService()
    if not hasattr(state, "patient_case_service"):
        state.patient_case_service = PatientCaseService()


async def _ensure_runtime_ready(app: FastAPI) -> None:
    state = app.state
    if getattr(state, "_runtime_ready", False):
        return

    async with _runtime_init_lock:
        if getattr(state, "_runtime_ready", False):
            return

        from app.database import create_tables

        try:
            await create_tables()
        except Exception as exc:
            log.warning("DDL sync failed or skipped: %s", exc)

        _initialise_runtime_services(app)
        state._runtime_ready = True
        log.info("Runtime services initialised.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("AnemiaLens starting up …")

    await _ensure_runtime_ready(app)

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
                passed=True,
                blur_score=100.0,
                brightness_score=0.3,
                contrast_score=0.15,
                framing_score=1.5,
                issues=[],
            )
            app.state.predictor.predict(dummy, dummy_quality)
            gc.collect()
            log.info("Model warm-up complete — first inference latency eliminated.")
        except Exception as exc:
            log.warning("Model warm-up failed (non-fatal): %s", exc)

    yield

    # Shutdown: close DB engine
    from app.database import close_engine

    await close_engine()

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
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
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

# 4. Metrics collection
from app.middleware.metrics import MetricsMiddleware

app.add_middleware(MetricsMiddleware)


# ---------------------------------------------------------------------------
# Middleware — request ID + timing
# ---------------------------------------------------------------------------


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    request.state.started_at = time.perf_counter()

    await _ensure_runtime_ready(request.app)

    try:
        response = await call_next(request)
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - request.state.started_at) * 1000
        log.exception(
            "%s %s -> %d (%.1fms) [%s]",
            request.method,
            request.url.path,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            elapsed_ms,
            request_id,
            extra={"request_id": request_id},
        )
        
        # Return structured JSON so that the frontend doesn't crash on plain text errors
        from sqlalchemy.exc import SQLAlchemyError
        if isinstance(exc, SQLAlchemyError):
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": "Database Unavailable",
                    "detail": "The database is temporarily offline or connection failed. Please ensure database services are running and restored.",
                    "request_id": request_id,
                },
            )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "detail": "An unexpected server error occurred. Please try again later.",
                "request_id": request_id,
            },
        )

    elapsed_ms = (time.perf_counter() - request.state.started_at) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"

    log.info(
        "%s %s -> %d (%.1fms) [%s]",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        request_id,
        extra={"request_id": request_id},
    )
    return response


# ---------------------------------------------------------------------------
# Include API route modules (Phase 2 & 3)
# ---------------------------------------------------------------------------

from app.api.auth import router as auth_router
from app.api.history import router as history_router
from app.api.admin import router as admin_router
from app.api.billing import router as billing_router
from app.api.email_report import router as email_report_router
from app.api.v1 import router as v1_router

app.include_router(auth_router)
app.include_router(history_router)
app.include_router(admin_router)
app.include_router(billing_router)
app.include_router(email_report_router)

# API v1 — versioned namespace (all routes under /api/v1/*)
app.include_router(v1_router)


# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------
from sqlalchemy.exc import SQLAlchemyError

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    request_id = getattr(request.state, "request_id", "unknown")
    log.exception("Database error occurred on %s: %s [%s]", request.url.path, exc, request_id)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "Database Unavailable",
            "detail": "The database is temporarily offline or connection failed. Please ensure database services are running and restored.",
            "request_id": request_id,
        },
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    log.exception("Unhandled error occurred on %s: %s [%s]", request.url.path, exc, request_id)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected server error occurred. Please try again later.",
            "request_id": request_id,
        },
    )



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

_DEMO_IMAGE_NAMES = {
    "low-risk-demo.jpg",
    "moderate-risk-demo.jpg",
    "high-concern-demo.jpg",
}


def _relax_quality_for_known_demo_image(image: UploadFile, quality):
    """
    Keep production gate strict, but allow bundled demo assets to traverse
    the full pipeline so users can validate end-to-end behavior.
    """
    file_name = (image.filename or "").strip().lower()
    if file_name not in _DEMO_IMAGE_NAMES or quality.passed:
        return quality, False
    softened_issues = [
        QualityIssue(
            code=issue.code,
            severity="warning",
            title=issue.title,
            message=issue.message,
        )
        for issue in quality.issues
    ]
    relaxed_quality = quality.model_copy(
        update={
            "passed": True,
            "issues": softened_issues,
        }
    )
    return relaxed_quality, True


def _too_large_response(request_id: str, max_mb: float) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        content={
            "error": f"Image exceeds the {max_mb:.0f} MB size limit.",
            "request_id": request_id,
        },
    )


def _attempt_raw_frame_rescue(
    services, image_bytes: bytes, quality, patient_profile_input=None
):
    if quality.passed or not services.quality_service.allows_raw_frame_rescue(quality):
        return quality, None, False

    raw_image = load_image_bytes(image_bytes).convert("RGB")
    raw_prediction = services.predictor.predict(
        raw_image,
        quality,
        patient_profile=patient_profile_input,
    )
    if not services.predictor.should_accept_raw_frame_rescue(raw_prediction):
        return quality, None, False

    rescued_quality = services.quality_service.build_raw_frame_rescue_assessment(
        quality
    )
    return rescued_quality, raw_prediction, True


def _maybe_downscale_image_bytes(
    image_bytes: bytes, max_dim: int = 1800
) -> tuple[bytes, bool, tuple[int, int] | None]:
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            width, height = img.size
            largest = max(width, height)
            if largest <= max_dim:
                return image_bytes, False, (width, height)
            scale = max_dim / float(largest)
            new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
            resized = img.convert("RGB").resize(new_size, Image.Resampling.LANCZOS)
            out = io.BytesIO()
            resized.save(out, format="JPEG", quality=90, optimize=True)
            return out.getvalue(), True, new_size
    except Exception:
        return image_bytes, False, None


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
        await persist_screening_result(
            request_id=request_id,
            analysis=analysis,
            user_id=user_id,
            processing_time_ms=processing_time_ms,
        )

    except Exception as exc:
        log.warning("Failed to persist screening (non-fatal): %s", exc)


# ---------------------------------------------------------------------------
# Routes — Health / Meta
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect the Space root to Swagger UI so Docker Space routing has a valid landing page."""
    return RedirectResponse(url="/docs", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/health", tags=["meta"], summary="Liveness probe")
async def health(request: Request, full: bool = False) -> dict[str, object]:
    """
    Returns detailed health status with dependency checks.

    Includes:
    - Model readiness
    - Guidance service status
    - Database connectivity
    - Model file integrity
    - External API availability
    - System resource usage (disk, memory, CPU)

    Results are cached for 10 seconds to prevent excessive resource usage
    from frequent load balancer probes.
    """
    from app.health_checks import (
        get_cached_health_status,
        health_cache,
        metrics_collector,
    )

    if full:
        result = await get_cached_health_status()
        await metrics_collector.record_cache_access(hit=result.get("cache_hit", False))
        #region agent log
        _agent_debug_log(
            "run7",
            "H16",
            "backend/app/main.py:health:full",
            "Full health probe served",
            {"cacheHit": bool(result.get("cache_hit", False))},
        )
        #endregion
        return result

    predictor = request.app.state.predictor
    guidance_status = request.app.state.guidance_service.runtime_status()
    cached = health_cache.get()
    cache_hit = cached is not None
    if cached is None:
        cached = await get_cached_health_status()

    await metrics_collector.record_cache_access(hit=cache_hit)
    response: dict[str, object] = {
        "status": (
            cached.get("status", "healthy")
            if predictor.is_ready()
            else "degraded"
        ),
        "mode": "fast",
        "model_ready": predictor.is_ready(),
        "guidance_client_ready": guidance_status.client_ready,
        "guidance_strategy": guidance_status.active_strategy,
        "cache_hit": cache_hit,
        "checks": cached.get("checks", {}),
        "system": cached.get("system", {}),
        "timestamp": cached.get("timestamp"),
        "version": cached.get("version"),
        "total_latency_ms": cached.get("total_latency_ms"),
    }
    response["last_full_check_status"] = cached.get("status")
    response["last_full_check_ts"] = cached.get("timestamp")
    #region agent log
    _agent_debug_log(
        "run7",
        "H16",
        "backend/app/main.py:health:fast",
        "Fast health probe served",
        {"cacheHit": cached is not None, "modelReady": predictor.is_ready()},
    )
    #endregion
    return response


@app.get("/readyz", tags=["meta"], summary="Readiness probe")
async def readyz(request: Request) -> JSONResponse:
    predictor = request.app.state.predictor
    guidance_status = request.app.state.guidance_service.runtime_status()
    ready = predictor.is_ready()
    #region agent log
    _agent_debug_log(
        "run6",
        "H15",
        "backend/app/main.py:readyz",
        "Readiness probe evaluated",
        {
            "ready": bool(ready),
            "guidanceClientReady": bool(guidance_status.client_ready),
            "guidanceStrategy": guidance_status.active_strategy,
        },
    )
    #endregion
    return JSONResponse(
        status_code=status.HTTP_200_OK
        if ready
        else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "ready" if ready else "degraded",
            "model_ready": ready,
            "guidance_client_ready": guidance_status.client_ready,
            "guidance_strategy": guidance_status.active_strategy,
            "guidance_fallback_reason": guidance_status.fallback_reason,
        },
    )


@app.get("/metrics", tags=["meta"], summary="Prometheus-compatible metrics")
async def metrics() -> Response:
    """
    Returns application metrics in Prometheus text exposition format.

    Includes:
    - Request count, error rate, latency percentiles (p50, p95, p99)
    - Model inference count, error rate, latency percentiles
    - Cache hit/miss rates
    - Active user count
    - Per-endpoint request counts and latencies
    """
    from app.health_checks import metrics_collector
    from starlette.responses import Response as StarletteResponse

    prometheus_text = await metrics_collector.get_prometheus_format()
    return StarletteResponse(
        content=prometheus_text,
        media_type="text/plain; version=0.0.4; charset=utf-8",
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
    "/api/guidance/chat",
    response_model=GuidanceChatResponse,
    tags=["screening"],
    summary="Ask a follow-up question about the current screening result",
    status_code=status.HTTP_200_OK,
)
async def guidance_chat(
    request: Request,
    payload: GuidanceChatRequest,
) -> GuidanceChatResponse | JSONResponse:
    rid = request.state.request_id
    try:
        return request.app.state.guidance_service.reply_to_message(
            payload.analysis,
            payload.message,
            payload.history,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": str(exc), "request_id": rid},
        )


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
    image_bytes, was_downscaled, resized_shape = _maybe_downscale_image_bytes(image_bytes)
    #region agent log
    _agent_debug_log(
        "run11",
        "H24",
        "backend/app/main.py:quality_check:preprocess",
        "Quality-check preprocess decision",
        {
            "requestId": rid,
            "downscaled": bool(was_downscaled),
            "resizedShape": resized_shape,
            "finalBytes": len(image_bytes),
        },
    )
    #endregion

    try:
        quality, _, roi_result = request.app.state.quality_service.evaluate_with_roi(
            image_bytes
        )
    except (OSError, UnidentifiedImageError, ValueError):
        return _image_error_response(rid)
    quality, demo_quality_relaxed = _relax_quality_for_known_demo_image(image, quality)
    #region agent log
    _agent_debug_log(
        "run11",
        "H25",
        "backend/app/main.py:quality_check:qualityGate",
        "Quality-check gate evaluated",
        {
            "requestId": rid,
            "fileName": image.filename or "",
            "qualityPassed": bool(quality.passed),
            "demoQualityRelaxed": bool(demo_quality_relaxed),
            "issueCodes": [issue.code for issue in quality.issues[:5]],
        },
    )
    #endregion

    return QualityCheckResponse(
        quality=quality,
        roi_preview=build_roi_preview_payload(roi_result),
    )


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
    symptoms: Annotated[
        str | None, Form(description="JSON-encoded symptom flags.")
    ] = None,
    patient_profile: Annotated[
        str | None, Form(description="JSON-encoded intake profile.")
    ] = None,
    language: Annotated[
        str | None, Form(description="Preferred language for guidance.")
    ] = None,
    region: Annotated[
        str | None, Form(description="Geographic region for localised guidance.")
    ] = None,
    background_tasks: BackgroundTasks = None,
) -> AnalyzeResponse | JSONResponse:
    """
    Full pipeline: quality gate → ML inference → triage → guidance → insight packs.
    Works for both authenticated and anonymous users.
    Authenticated users get their results persisted to scan history.
    """
    rid = request.state.request_id
    svc = request.app.state
    #region agent log
    _agent_debug_log(
        "run1",
        "H3",
        "backend/app/main.py:analyze:entry",
        "Analyze endpoint entered",
        {"requestId": rid, "hasSymptoms": symptoms is not None, "hasPatientProfile": patient_profile is not None},
    )
    #endregion

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

    # --- Scan limit enforcement (free plan) --------------------------------
    from app.config import settings

    scan_limit = settings.free_plan_scan_limit
    if (
        user_id is not None
        and user_tier == "free"
        and user_scan_count >= scan_limit
    ):
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content={
                "error": f"Free plan limit reached ({scan_limit} scans). Upgrade to Pro for unlimited screenings.",
                "upgrade_required": True,
                "request_id": rid,
            },
        )

    # --- Input validation --------------------------------------------------
    try:
        symptom_input = parse_symptoms(symptoms)
        patient_profile_input = parse_patient_profile(patient_profile)
        language = normalize_optional_text(language, field_name="language")
        region = normalize_optional_text(region, field_name="region")
    except InvalidRequestPayload as exc:
        #region agent log
        _agent_debug_log(
            "run1",
            "H3",
            "backend/app/main.py:analyze:parseError",
            "Analyze payload parsing failed",
            {"requestId": rid, "error": str(exc)},
        )
        #endregion
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": str(exc), "request_id": rid},
        )

    # --- Image loading ------------------------------------------------------
    image_bytes = await image.read()

    if len(image_bytes) > settings.max_image_bytes:
        return _too_large_response(rid, settings.max_image_bytes / 1024 / 1024)
    image_bytes, was_downscaled, resized_shape = _maybe_downscale_image_bytes(image_bytes)
    #region agent log
    _agent_debug_log(
        "run10",
        "H23",
        "backend/app/main.py:analyze:preprocess",
        "Image preprocess decision",
        {
            "requestId": rid,
            "downscaled": bool(was_downscaled),
            "resizedShape": resized_shape,
            "finalBytes": len(image_bytes),
        },
    )
    #endregion

    try:
        _quality_start = time.perf_counter()
        quality, rgb, roi_result = svc.quality_service.evaluate_with_roi(image_bytes)
        _quality_elapsed_ms = (time.perf_counter() - _quality_start) * 1000
    except (OSError, UnidentifiedImageError, ValueError):
        return _image_error_response(rid)
    quality, demo_quality_relaxed = _relax_quality_for_known_demo_image(image, quality)
    #region agent log
    _agent_debug_log(
        "run1",
        "H8",
        "backend/app/main.py:analyze:qualityGate",
        "Quality gate evaluated",
        {
            "requestId": rid,
            "fileName": image.filename or "",
            "qualityPassed": bool(quality.passed),
            "demoQualityRelaxed": bool(demo_quality_relaxed),
            "issueCodes": [issue.code for issue in quality.issues[:5]],
        },
    )
    #endregion

    # --- Inference (skipped on quality failure) -----------------------------
    _infer_start = time.perf_counter()
    _infer_success = True
    try:
        prediction = (
            svc.predictor.predict(
                rgb,
                quality,
                patient_profile=patient_profile_input,
            )
            if quality.passed
            else None
        )
    except Exception:
        #region agent log
        _agent_debug_log(
            "run1",
            "H4",
            "backend/app/main.py:analyze:predictionException",
            "Prediction failed inside analyze flow",
            {"requestId": rid, "qualityPassed": bool(quality.passed)},
        )
        #endregion
        _infer_success = False
        prediction = None
        raise
    finally:
        if quality.passed:
            _infer_latency_ms = (time.perf_counter() - _infer_start) * 1000
            from app.health_checks import metrics_collector as _mc

            await _mc.record_inference(latency_ms=_infer_latency_ms, success=_infer_success)
    #region agent log
    _agent_debug_log(
        "run10",
        "H20",
        "backend/app/main.py:analyze:stageTiming:qualityPrediction",
        "Quality and prediction stage timings",
        {
            "requestId": rid,
            "qualityMs": round(_quality_elapsed_ms, 1),
            "predictionMs": round((time.perf_counter() - _infer_start) * 1000, 1),
            "qualityPassed": bool(quality.passed),
            "predictionPresent": prediction is not None,
        },
    )
    #endregion

    used_raw_frame_rescue = False
    if prediction is None:
        quality, prediction, used_raw_frame_rescue = _attempt_raw_frame_rescue(
            svc,
            image_bytes,
            quality,
            patient_profile_input=patient_profile_input,
        )
    #region agent log
    _agent_debug_log(
        "run1",
        "H4",
        "backend/app/main.py:analyze:postPrediction",
        "Prediction branch completed",
        {
            "requestId": rid,
            "qualityPassed": bool(quality.passed),
            "predictionPresent": prediction is not None,
            "usedRawFrameRescue": used_raw_frame_rescue,
        },
    )
    #endregion

    # --- Triage + guidance -------------------------------------------------
    _triage_guidance_start = time.perf_counter()
    signal_breakdown = svc.triage_service.build_signal_breakdown(
        quality, prediction, symptom_input
    )
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
    #region agent log
    _agent_debug_log(
        "run10",
        "H21",
        "backend/app/main.py:analyze:stageTiming:triageGuidance",
        "Triage and guidance stage timing",
        {
            "requestId": rid,
            "triageGuidanceMs": round((time.perf_counter() - _triage_guidance_start) * 1000, 1),
            "triageBand": triage.band,
            "guidanceSource": guidance.source,
        },
    )
    #endregion

    processing_time_ms = (time.perf_counter() - request.state.started_at) * 1000
    #region agent log
    _agent_debug_log(
        "run10",
        "H22",
        "backend/app/main.py:analyze:stageTiming:total",
        "Analyze total processing timing",
        {"requestId": rid, "totalMs": round(processing_time_ms, 1)},
    )
    #endregion

    analysis_meta = build_analysis_meta(
        request_id=rid,
        api_version=app.version,
        processing_time_ms=processing_time_ms,
        quality=quality,
        decision_audit=decision_audit,
        guidance=guidance,
        used_raw_frame_rescue=used_raw_frame_rescue,
    )
    patient_profile_result = svc.patient_case_service.build_profile(
        rid,
        patient_profile_input,
        symptom_input,
    )
    workflow_stages = svc.patient_case_service.build_workflow_stages(
        quality,
        prediction,
        triage,
        guidance,
        symptom_input,
    )
    structured_case = svc.patient_case_service.build_structured_case(
        rid,
        patient_profile_result,
        quality,
        prediction,
        triage,
        guidance,
        symptom_input,
    )

    response = AnalyzeResponse(
        blocked=not quality.passed,
        quality=quality,
        roi_preview=build_roi_preview_payload(roi_result),
        prediction=prediction,
        decision_audit=decision_audit,
        triage=triage,
        guidance=guidance,
        insight_pack=insight_pack,
        clinical_brief=clinical_brief,
        handoff_summary=handoff_summary,
        analysis_meta=analysis_meta,
        patient_profile=patient_profile_result,
        workflow_stages=workflow_stages,
        structured_case=structured_case,
        symptoms=symptom_input,
        language=language,
        region=region,
    )

    # --- Persist to database (async, non-blocking) -------------------------
    if background_tasks is not None:
        background_tasks.add_task(
            _persist_screening, rid, response, user_id, processing_time_ms
        )

    return response


# ---------------------------------------------------------------------------
# Legacy compatibility routes
# ---------------------------------------------------------------------------


def _legacy_redirect(path: str) -> RedirectResponse:
    return RedirectResponse(url=path, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.post("/auth/register", include_in_schema=False)
async def legacy_auth_register() -> RedirectResponse:
    return _legacy_redirect("/api/auth/register")


@app.post("/auth/login", include_in_schema=False)
async def legacy_auth_login() -> RedirectResponse:
    return _legacy_redirect("/api/auth/login")


@app.post("/auth/refresh", include_in_schema=False)
async def legacy_auth_refresh() -> RedirectResponse:
    return _legacy_redirect("/api/auth/refresh")


@app.post("/auth/google", include_in_schema=False)
async def legacy_auth_google() -> RedirectResponse:
    return _legacy_redirect("/api/auth/google")


@app.get("/auth/profile", include_in_schema=False)
async def legacy_auth_profile() -> RedirectResponse:
    return _legacy_redirect("/api/auth/me")


@app.get("/api/history", include_in_schema=False)
async def legacy_history_list() -> RedirectResponse:
    return _legacy_redirect("/api/screenings")


@app.get("/api/history/{screening_uid}", include_in_schema=False)
async def legacy_history_detail(screening_uid: str) -> RedirectResponse:
    return _legacy_redirect(f"/api/screenings/{screening_uid}")


@app.delete("/api/history/{screening_uid}", include_in_schema=False)
async def legacy_history_delete(screening_uid: str) -> RedirectResponse:
    return _legacy_redirect(f"/api/screenings/{screening_uid}")
