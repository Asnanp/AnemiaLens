"""
AnemiaLens FastAPI application.

Improvements over the original:
- Lifespan context manager replaces deprecated on_event hooks.
- Structured JSON logging with a per-request trace ID injected via middleware.
- Hard image-size gate before any decoding (prevents trivial DoS).
- Explicit 413 / 415 responses with clear error messages.
- /api/analyze is fully async — no blocking I/O on the event loop.
- Runtime-status endpoint enriches model metadata from the training report.
- All service singletons are initialised once during lifespan startup and
  attached to app.state so tests can inject fakes without monkey-patching.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Request, UploadFile, status
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
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
log = logging.getLogger("anemialens")


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("AnemiaLens starting up …")
    app.state.quality_service = ImageQualityService()
    app.state.predictor = ScreeningPredictor()
    app.state.triage_service = TriageService()
    app.state.guidance_service = GuidanceService()
    app.state.case_insight_service = CaseInsightService()
    app.state.clinical_brief_service = ClinicalBriefService()
    app.state.handoff_service = HandoffSummaryService()
    log.info("All services initialised.")
    yield
    log.info("AnemiaLens shutting down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AnemiaLens API",
    version="0.3.0",
    description=(
        "Conjunctiva-based anemia screening API. "
        "All predictions are screening aids only — not medical diagnoses."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
# Routes
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
    """
    Returns which models are loaded, their validation metrics, and which
    guidance strategy is active.  Useful for operational dashboards.
    """
    return build_runtime_status(
        request.app.state.predictor,
        request.app.state.guidance_service,
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
    """
    Runs only the image-quality pipeline.  Use this for instant camera
    feedback before committing to a full (slower) analysis call.
    """
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
    Full pipeline:

    1. Parse and validate the symptom payload.
    2. Assess image quality; return early if blocking issues are found.
    3. Run ML screening inference on the quality-gated ROI.
    4. Compute a triage band from image + prediction + symptoms.
    5. Generate LLM-backed (or fallback) personalised guidance.

    When `blocked=true` in the response, `prediction` will be `null`.
    """
    rid = request.state.request_id
    svc = request.app.state

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
    analysis_meta = build_analysis_meta(
        request_id=rid,
        api_version=app.version,
        processing_time_ms=(time.perf_counter() - request.state.started_at) * 1000,
        quality=quality,
        decision_audit=decision_audit,
        guidance=guidance,
        used_raw_frame_rescue=used_raw_frame_rescue,
    )

    return AnalyzeResponse(
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
