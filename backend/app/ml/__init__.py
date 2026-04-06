"""Offline-trainable ML utilities for AnemiaLens.

Enhanced modules (v8+):
- quality_gate: Pre-inference image quality gate
- advanced_preprocessing: CLAHE, denoise, rotation correction, gamma
- dynamic_ensemble: Quality-aware dynamic ensemble weighting
- model_confidence: Multi-dimensional confidence scoring
- explainability: Feature importance and "why this result" explanations
- inference_cache: Hash-based caching for repeated predictions
- fallback_prediction: Fallback predictions with uncertainty bounds
"""

# Core modules (existing)
from app.ml.features import (
    extract_eye_features,
    extract_ultimate_clinical_features,
    extract_v8_clinical_features,
    FEATURE_NAMES,
    TEXTURE_FEATURES,
    FULL_FEATURES,
    ALL_FEATURE_NAMES_V7,
    ULTIMATE_CLINICAL_FEATURE_NAMES,
    V8_CLINICAL_FEATURE_NAMES,
    load_image_bytes,
    load_image_path,
    vectorize_features,
    # v8+ additions
    extract_features_with_preprocessing,
    vectorize_features_fast,
    compute_feature_statistics,
)

# v8+ Enhanced modules
from app.ml.quality_gate import (
    ImageQualityGate,
    QualityGateResult,
    QualityGateIssue,
    get_quality_gate,
    evaluate_image_quality,
)

from app.ml.advanced_preprocessing import (
    AdvancedPreprocessor,
    PreprocessingConfig,
    PreprocessingReport,
    get_preprocessor,
    preprocess_image,
)

from app.ml.dynamic_ensemble import (
    DynamicEnsembleFuser,
    ModelPrediction,
    EnsembleResult,
    get_ensemble_fuser,
    fuse_predictions,
)

from app.ml.model_confidence import (
    ModelConfidenceScorer,
    ConfidenceComponents,
    ConfidenceResult,
    get_confidence_scorer,
    compute_confidence,
)

from app.ml.explainability import (
    FeatureImportanceCalculator,
    ExplanationGenerator,
    FeatureImportance,
    ExplainabilityResult,
    generate_explanation,
)

from app.ml.inference_cache import (
    InferenceCache,
    CacheEntry,
    get_inference_cache,
    cache_prediction,
    get_cached_prediction,
)

from app.ml.fallback_prediction import (
    FallbackPredictor,
    FallbackPrediction,
    FallbackMethod,
    FallbackReason,
    get_fallback_predictor,
    generate_fallback,
)

__all__ = [
    # Existing
    "extract_eye_features",
    "extract_ultimate_clinical_features",
    "extract_v8_clinical_features",
    "FEATURE_NAMES",
    "TEXTURE_FEATURES",
    "FULL_FEATURES",
    "ALL_FEATURE_NAMES_V7",
    "ULTIMATE_CLINICAL_FEATURE_NAMES",
    "V8_CLINICAL_FEATURE_NAMES",
    "load_image_bytes",
    "load_image_path",
    "vectorize_features",
    # v8+ Feature extraction
    "extract_features_with_preprocessing",
    "vectorize_features_fast",
    "compute_feature_statistics",
    # v8+ Quality gate
    "ImageQualityGate",
    "QualityGateResult",
    "QualityGateIssue",
    "get_quality_gate",
    "evaluate_image_quality",
    # v8+ Preprocessing
    "AdvancedPreprocessor",
    "PreprocessingConfig",
    "PreprocessingReport",
    "get_preprocessor",
    "preprocess_image",
    # v8+ Dynamic ensemble
    "DynamicEnsembleFuser",
    "ModelPrediction",
    "EnsembleResult",
    "get_ensemble_fuser",
    "fuse_predictions",
    # v8+ Confidence
    "ModelConfidenceScorer",
    "ConfidenceComponents",
    "ConfidenceResult",
    "get_confidence_scorer",
    "compute_confidence",
    # v8+ Explainability
    "FeatureImportanceCalculator",
    "ExplanationGenerator",
    "FeatureImportance",
    "ExplainabilityResult",
    "generate_explanation",
    # v8+ Cache
    "InferenceCache",
    "CacheEntry",
    "get_inference_cache",
    "cache_prediction",
    "get_cached_prediction",
    # v8+ Fallback
    "FallbackPredictor",
    "FallbackPrediction",
    "FallbackMethod",
    "FallbackReason",
    "get_fallback_predictor",
    "generate_fallback",
]
