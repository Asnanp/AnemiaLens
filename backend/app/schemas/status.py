"""
Runtime status schemas for health and model state reporting.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import GuidanceSource


class GuidanceRuntimeStatus(BaseModel):
    active_strategy: GuidanceSource
    mistral_enabled: bool = False
    client_ready: bool = False
    api_key_configured: bool = False
    mistral_model: str | None = None
    provider: str | None = None
    fallback_reason: str | None = None
    last_provider_error: str | None = None


class ModelRuntimeStatus(BaseModel):
    primary_model: str
    deep_stack_loaded: bool
    legacy_loaded: bool
    artifact_ready: bool = False
    artifact_path: str | None = None
    load_error: str | None = None
    runtime_calibration_ready: bool | None = None
    runtime_calibration_method: str | None = None
    runtime_calibrated_threshold: float | None = None
    runtime_calibration_ece_before: float | None = None
    runtime_calibration_ece_after: float | None = None
    runtime_calibration_brier_before: float | None = None
    runtime_calibration_brier_after: float | None = None
    runtime_refiner_ready: bool | None = None
    runtime_refiner_method: str | None = None
    runtime_refined_threshold: float | None = None
    runtime_refined_accuracy: float | None = None
    runtime_refined_precision: float | None = None
    runtime_refined_recall: float | None = None
    runtime_refined_f1: float | None = None
    record_count: int | None = None
    validation_accuracy: float | None = None
    validation_f1: float | None = None
    split_strategy: str | None = None
    deployed_scope: str | None = None
    deployed_validation_size: int | None = None
    deployed_accuracy: float | None = None
    deployed_precision: float | None = None
    deployed_recall: float | None = None
    deployed_f1: float | None = None
    deployed_blocked_total: int | None = None
    deployed_likely_count: int | None = None
    deployed_uncertain_count: int | None = None


class RuntimeStatusResponse(BaseModel):
    api_status: Literal["ok"] = "ok"
    guidance: GuidanceRuntimeStatus
    model: ModelRuntimeStatus
    cache_hit_rate: float | None = Field(default=None, description="Cache hit rate (0.0-1.0)")
