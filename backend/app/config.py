"""
Central configuration for AnemiaLens backend.

All tuneable knobs live here. Override any setting via environment variables
(e.g. ANEMIALENS_QWEN_MODEL=Qwen/Qwen2.5-7B-Instruct). Pydantic-settings
performs automatic type coercion and validation at startup so misconfigured
deployments fail fast with a clear error rather than silently misbehaving at
runtime.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Paths (not env-overridable — tied to repo layout)
# ---------------------------------------------------------------------------

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = BACKEND_ROOT / "models"

DEFAULT_MODEL_PATH = MODELS_DIR / "anemia_model.pt"
DEFAULT_ENSEMBLE_PATH = MODELS_DIR / "ensemble_model.json"
DEFAULT_DEEP_STACK_PATH = MODELS_DIR / "deep_stack_model.joblib"
DEFAULT_ARCHIVE_MODEL_PATH = MODELS_DIR / "archive_screening_model.joblib"
DEFAULT_EFFICIENTNET_MODEL_PATH = MODELS_DIR / "efficientnet_anemia.pth"
DEFAULT_EFFICIENTNET_REPORT_PATH = MODELS_DIR / "efficientnet_report.json"
DEFAULT_RUNTIME_STACK_REPORT_PATH = MODELS_DIR / "runtime_stack_report.json"
DEFAULT_DEPLOYED_SCREENING_REPORT_PATH = MODELS_DIR / "deployed_screening_report.json"
DEFAULT_TRAINING_REPORT_PATH = MODELS_DIR / "training_report.json"


# ---------------------------------------------------------------------------
# Disclaimer (single source of truth — used in schemas *and* triage)
# ---------------------------------------------------------------------------

SCREENING_DISCLAIMER = (
    "AnemiaLens is a screening aid only and does not diagnose anemia "
    "or replace the advice of a qualified medical professional."
)


# ---------------------------------------------------------------------------
# Settings (env-overridable)
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Prefix all env vars with ANEMIALENS_ (case-insensitive).
    Example .env file::

        ANEMIALENS_QWEN_ENABLED=true
        ANEMIALENS_QWEN_MODEL=Qwen/Qwen2.5-7B-Instruct
        ANEMIALENS_HF_API_KEY=your_key_here
        ANEMIALENS_HF_PROVIDER=hf-inference
        ANEMIALENS_GUIDANCE_TIMEOUT=20
        ANEMIALENS_LOG_LEVEL=DEBUG
    """

    model_config = SettingsConfigDict(
        env_prefix="ANEMIALENS_",
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Server ----------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
        ]
    )

    # --- Guidance (Mistral AI) -------------------------------------------
    mistral_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("ANEMIALENS_MISTRAL_ENABLED", "MISTRAL_ENABLED"),
    )
    mistral_model: str = Field(
        default="mistral-small-latest",
        validation_alias=AliasChoices("ANEMIALENS_MISTRAL_MODEL", "MISTRAL_MODEL"),
    )
    mistral_api_key: str = Field(
        default="",
        repr=False,
        validation_alias=AliasChoices("ANEMIALENS_MISTRAL_API_KEY"),
    )
    guidance_timeout: float = Field(
        default=20.0,
        ge=1.0,
        le=120.0,
        validation_alias=AliasChoices("ANEMIALENS_GUIDANCE_TIMEOUT", "GUIDANCE_TIMEOUT"),
    )
    guidance_max_tokens: int = Field(
        default=512,
        ge=64,
        le=2048,
        validation_alias=AliasChoices("ANEMIALENS_GUIDANCE_MAX_TOKENS", "GUIDANCE_MAX_TOKENS"),
    )
    # Keep old HF fields so existing env files don't break
    qwen_enabled: bool = Field(default=False, validation_alias=AliasChoices("ANEMIALENS_QWEN_ENABLED", "QWEN_ENABLED"))
    qwen_model: str = Field(default="", validation_alias=AliasChoices("ANEMIALENS_QWEN_MODEL", "QWEN_MODEL"))
    hf_api_key: str = Field(default="", repr=False, validation_alias=AliasChoices("ANEMIALENS_HF_API_KEY", "HF_API_KEY"))
    hf_provider: str = Field(default="", validation_alias=AliasChoices("ANEMIALENS_HF_PROVIDER", "HF_PROVIDER"))

    # --- Image quality thresholds ----------------------------------------
    min_blur_score: float = Field(default=60.0, ge=0.0, le=200.0)
    min_brightness: float = Field(default=0.20, ge=0.0, le=1.0)
    max_brightness: float = Field(default=0.92, ge=0.0, le=1.0)
    min_contrast: float = Field(default=0.08, ge=0.0, le=1.0)
    min_framing: float = Field(default=0.6, ge=0.0)

    # --- Triage band thresholds ------------------------------------------
    high_concern_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    moderate_risk_threshold: float = Field(default=0.40, ge=0.0, le=1.0)

    # --- Request validation ----------------------------------------------
    max_field_length: int = Field(default=48, ge=8, le=512)
    max_image_bytes: int = Field(default=20 * 1024 * 1024, ge=1024)  # 20 MB

    # --- Feature flags ---------------------------------------------------
    enable_roi_crop: bool = True
    enable_deep_stack: bool = False  # set True once model ships

    @field_validator("max_brightness")
    @classmethod
    def _brightness_range_sane(cls, v: float, info) -> float:
        min_b = info.data.get("min_brightness", 0.0)
        if v <= min_b:
            raise ValueError(
                f"max_brightness ({v}) must be greater than min_brightness ({min_b})"
            )
        return v

    @field_validator("high_concern_threshold")
    @classmethod
    def _high_above_moderate(cls, v: float, info) -> float:
        mod = info.data.get("moderate_risk_threshold", 0.0)
        if v <= mod:
            raise ValueError(
                f"high_concern_threshold ({v}) must exceed moderate_risk_threshold ({mod})"
            )
        return v

    @model_validator(mode="after")
    def _warn_missing_api_key(self) -> "Settings":
        if self.mistral_enabled and not self.mistral_api_key:
            import warnings
            warnings.warn(
                "No Mistral API key is set but Mistral guidance is enabled. "
                "Guidance calls will fall back to rule-based responses.",
                RuntimeWarning,
                stacklevel=2,
            )
        return self


# Module-level singleton — imported everywhere else.
settings = Settings()
