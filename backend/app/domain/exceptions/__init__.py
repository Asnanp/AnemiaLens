"""
Domain exception hierarchy for AnemiaLens.

All business-layer errors derive from AnemiaLensError.
HTTP-facing code should catch these and translate them into
appropriate FastAPI HTTPException responses.

Usage:
    from app.domain.exceptions import ModelNotReadyError

    if not predictor.is_ready():
        raise ModelNotReadyError("Screening model has not finished loading.")
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Base exception
# ---------------------------------------------------------------------------


class AnemiaLensError(Exception):
    """Base class for all AnemiaLens domain errors."""

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ---------------------------------------------------------------------------
# Screening / ML pipeline errors
# ---------------------------------------------------------------------------


class ModelNotReadyError(AnemiaLensError):
    """Raised when the ML model is not loaded or ready for inference."""


class ModelLoadError(AnemiaLensError):
    """Raised when a model artifact cannot be loaded."""


class InferenceError(AnemiaLensError):
    """Raised when the ML inference pipeline encounters an unexpected failure."""


class CalibrationError(AnemiaLensError):
    """Raised when calibration or risk adjustment fails."""


class FeatureExtractionError(AnemiaLensError):
    """Raised when feature extraction from an image fails."""


class PredictionInputError(AnemiaLensError):
    """Raised when prediction input data is invalid."""


# ---------------------------------------------------------------------------
# Image quality errors
# ---------------------------------------------------------------------------


class ImageQualityError(AnemiaLensError):
    """Raised when image quality assessment encounters a problem."""


class ImageDecodeError(AnemiaLensError):
    """Raised when an uploaded image cannot be decoded."""


class ImageSizeExceededError(AnemiaLensError):
    """Raised when the uploaded image exceeds the maximum allowed size."""


class ROIExtractionError(AnemiaLensError):
    """Raised when ROI extraction from the image fails."""


# ---------------------------------------------------------------------------
# Triage / decision errors
# ---------------------------------------------------------------------------


class TriageError(AnemiaLensError):
    """Raised when triage assessment encounters an unexpected problem."""


class DecisionThresholdError(AnemiaLensError):
    """Raised when a decision threshold is missing or inconsistent."""


# ---------------------------------------------------------------------------
# Guidance errors
# ---------------------------------------------------------------------------


class GuidanceError(AnemiaLensError):
    """Raised when guidance generation fails."""


class LLMProviderError(GuidanceError):
    """Raised when the LLM provider (e.g., Mistral) returns an error."""


class LLMTimeoutError(GuidanceError):
    """Raised when the LLM provider times out."""


# ---------------------------------------------------------------------------
# Authentication / authorization errors
# ---------------------------------------------------------------------------


class AuthenticationError(AnemiaLensError):
    """Raised when authentication fails."""


class AuthorizationError(AnemiaLensError):
    """Raised when the user lacks permission for the requested action."""


class TokenExpiredError(AuthenticationError):
    """Raised when a JWT token has expired."""


class InvalidTokenError(AuthenticationError):
    """Raised when a JWT token is malformed or invalid."""


# ---------------------------------------------------------------------------
# User / account errors
# ---------------------------------------------------------------------------


class UserNotFoundError(AnemiaLensError):
    """Raised when a requested user does not exist."""


class UserAlreadyExistsError(AnemiaLensError):
    """Raised when attempting to create a user with a duplicate email."""


class ScanLimitExceededError(AnemiaLensError):
    """Raised when a free-plan user exceeds their scan quota."""


# ---------------------------------------------------------------------------
# Screening record errors
# ---------------------------------------------------------------------------


class ScreeningNotFoundError(AnemiaLensError):
    """Raised when a requested screening record does not exist."""


class ScreeningPersistenceError(AnemiaLensError):
    """Raised when saving a screening result to the database fails."""


# ---------------------------------------------------------------------------
# Configuration errors
# ---------------------------------------------------------------------------


class ConfigurationError(AnemiaLensError):
    """Raised when a required configuration value is missing or invalid."""


class SecretNotConfiguredError(ConfigurationError):
    """Raised when a required secret (API key, etc.) is not configured."""


# ---------------------------------------------------------------------------
# External service errors
# ---------------------------------------------------------------------------


class ExternalServiceError(AnemiaLensError):
    """Raised when an external service (Stripe, Google OAuth, etc.) fails."""


class PaymentProviderError(ExternalServiceError):
    """Raised when the payment provider (Stripe) returns an error."""


class EmailServiceError(AnemiaLensError):
    """Raised when sending email fails."""
