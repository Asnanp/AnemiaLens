"""
Domain layer for AnemiaLens.

Contains business logic, exceptions, and domain models that are
independent of framework and infrastructure concerns.
"""

from __future__ import annotations

from app.domain.exceptions import (
    AnemiaLensError,
    ModelNotReadyError,
    ModelLoadError,
    InferenceError,
    CalibrationError,
    FeatureExtractionError,
    PredictionInputError,
    ImageQualityError,
    ImageDecodeError,
    ImageSizeExceededError,
    ROIExtractionError,
    TriageError,
    DecisionThresholdError,
    GuidanceError,
    LLMProviderError,
    LLMTimeoutError,
    AuthenticationError,
    AuthorizationError,
    TokenExpiredError,
    InvalidTokenError,
    UserNotFoundError,
    UserAlreadyExistsError,
    ScanLimitExceededError,
    ScreeningNotFoundError,
    ScreeningPersistenceError,
    ConfigurationError,
    SecretNotConfiguredError,
    ExternalServiceError,
    PaymentProviderError,
    EmailServiceError,
)

__all__ = [
    "AnemiaLensError",
    "ModelNotReadyError",
    "ModelLoadError",
    "InferenceError",
    "CalibrationError",
    "FeatureExtractionError",
    "PredictionInputError",
    "ImageQualityError",
    "ImageDecodeError",
    "ImageSizeExceededError",
    "ROIExtractionError",
    "TriageError",
    "DecisionThresholdError",
    "GuidanceError",
    "LLMProviderError",
    "LLMTimeoutError",
    "AuthenticationError",
    "AuthorizationError",
    "TokenExpiredError",
    "InvalidTokenError",
    "UserNotFoundError",
    "UserAlreadyExistsError",
    "ScanLimitExceededError",
    "ScreeningNotFoundError",
    "ScreeningPersistenceError",
    "ConfigurationError",
    "SecretNotConfiguredError",
    "ExternalServiceError",
    "PaymentProviderError",
    "EmailServiceError",
]
