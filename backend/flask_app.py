from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS
from PIL import UnidentifiedImageError
from dotenv import load_dotenv

from app.ml.features import load_image_bytes
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

BACKEND_ROOT = Path(__file__).resolve().parent
load_dotenv(BACKEND_ROOT / ".env")

app = Flask(__name__)
CORS(
    app,
    origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
)

quality_service = ImageQualityService()
predictor = ScreeningPredictor()
triage_service = TriageService()
guidance_service = GuidanceService()
case_insight_service = CaseInsightService()
clinical_brief_service = ClinicalBriefService()
handoff_service = HandoffSummaryService()


def _attempt_raw_frame_rescue(image_bytes: bytes, quality):
    if quality.passed or not quality_service.allows_raw_frame_rescue(quality):
        return quality, None, False

    raw_image = load_image_bytes(image_bytes).convert("RGB")
    raw_prediction = predictor.predict(raw_image, quality)
    if not predictor.should_accept_raw_frame_rescue(raw_prediction):
        return quality, None, False

    rescued_quality = quality_service.build_raw_frame_rescue_assessment(quality)
    return rescued_quality, raw_prediction, True


@app.get("/health")
def health() -> tuple[dict[str, object], int]:
    guidance_status = guidance_service.runtime_status()
    return {
        "status": "ok",
        "model_ready": predictor.is_ready(),
        "guidance_strategy": guidance_status.active_strategy,
    }, 200


@app.get("/api/runtime-status")
def runtime_status() -> tuple[object, int]:
    return jsonify(build_runtime_status(predictor, guidance_service).model_dump()), 200


@app.post("/api/quality-check")
def quality_check() -> tuple[object, int]:
    file = request.files.get("image")
    if file is None:
        return jsonify({"error": "Missing image file"}), 400

    image_bytes = file.read()
    try:
        quality, _ = quality_service.evaluate(image_bytes)
    except (UnidentifiedImageError, Exception) as exc:
        if isinstance(exc, UnidentifiedImageError) or "cannot identify image" in str(exc).lower():
            return jsonify({"error": "The uploaded file is not a valid image. Please upload a JPEG or PNG photo."}), 400
        raise
    return jsonify({"quality": quality.model_dump()}), 200


@app.post("/api/analyze")
def analyze() -> tuple[object, int]:
    started_at = time.perf_counter()
    request_id = str(uuid.uuid4())[:8]
    file = request.files.get("image")
    if file is None:
        return jsonify({"error": "Missing image file"}), 400

    try:
        symptoms = parse_symptoms(request.form.get("symptoms"))
        language = normalize_optional_text(request.form.get("language"), field_name="language")
        region = normalize_optional_text(request.form.get("region"), field_name="region")
    except InvalidRequestPayload as exc:
        return jsonify({"error": str(exc)}), 400

    image_bytes = file.read()
    try:
        quality, rgb = quality_service.evaluate(image_bytes)
    except (UnidentifiedImageError, Exception) as exc:
        if isinstance(exc, UnidentifiedImageError) or "cannot identify image" in str(exc).lower():
            return jsonify({"error": "The uploaded file is not a valid image. Please upload a JPEG or PNG photo."}), 400
        raise
    prediction = predictor.predict(rgb, quality) if quality.passed else None
    used_raw_frame_rescue = False
    if prediction is None:
        quality, prediction, used_raw_frame_rescue = _attempt_raw_frame_rescue(image_bytes, quality)
    signal_breakdown = triage_service.build_signal_breakdown(quality, prediction, symptoms)
    triage = triage_service.assess(
        quality,
        prediction,
        symptoms,
        signal_breakdown=signal_breakdown,
    )
    decision_audit = build_decision_audit(
        quality,
        prediction,
        triage,
        used_raw_frame_rescue=used_raw_frame_rescue,
    )
    guidance = guidance_service.generate(triage, symptoms, prediction, language, region)
    insight_pack = case_insight_service.build(
        quality,
        prediction,
        triage,
        decision_audit,
        guidance,
        symptoms,
    )
    handoff_summary = handoff_service.build(
        quality,
        prediction,
        triage,
        guidance,
        symptoms,
        language,
        region,
    )
    clinical_brief = clinical_brief_service.build(
        quality,
        prediction,
        triage,
        decision_audit,
        guidance,
        symptoms,
        insight_pack,
        handoff_summary,
        signal_breakdown,
    )
    analysis_meta = build_analysis_meta(
        request_id=request_id,
        api_version="flask-compat",
        processing_time_ms=(time.perf_counter() - started_at) * 1000,
        quality=quality,
        decision_audit=decision_audit,
        guidance=guidance,
        used_raw_frame_rescue=used_raw_frame_rescue,
    )

    payload = {
        "blocked": not quality.passed,
        "quality": quality.model_dump(),
        "prediction": prediction.model_dump() if prediction is not None else None,
        "decision_audit": decision_audit.model_dump(),
        "triage": triage.model_dump(),
        "guidance": guidance.model_dump(),
        "insight_pack": insight_pack.model_dump(),
        "clinical_brief": clinical_brief.model_dump(),
        "handoff_summary": handoff_summary.model_dump(),
        "analysis_meta": analysis_meta.model_dump(),
        "symptoms": symptoms.model_dump(),
        "language": language,
        "region": region,
    }
    return jsonify(payload), 200

if __name__ == "__main__":
    debug_enabled = os.getenv("FLASK_DEBUG", "").strip().lower() in {"1", "true", "yes"}
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug_enabled, use_reloader=debug_enabled)
