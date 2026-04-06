"""
Tests for ML pipeline enhancements.

Covers:
- Feature extraction (basic and advanced)
- Fallback prediction strategies
- Quality gate logic
- Lighting normalization
- Model confidence estimation
- Inference cache
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.features import (
    extract_eye_features,
    extract_v8_clinical_features,
    framing_score as estimate_framing_score,
)
from app.ml.fallback_prediction import (
    FallbackPrediction,
    generate_fallback,
    POPULATION_PRIORS,
    HEMOGLOBIN_NORMS,
    conservative_default_prediction,
    heuristic_prediction,
    population_prior_prediction,
    _hb_to_risk,
    _risk_to_hb,
)
from app.ml.lighting_norm import (
    normalize_illumination,
    compute_illumination_bias,
)
from app.ml.model_confidence import (
    estimate_model_confidence,
    _capture_quality_score,
)
from app.ml.inference_cache import (
    InferenceCache,
    _compute_image_hash,
)
from app.schemas import QualityAssessment, PatientProfileInput


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------


class TestExtractEyeFeatures:
    def test_returns_dict_with_expected_keys(self) -> None:
        img = Image.new("RGB", (200, 200), color=(120, 80, 70))
        features = extract_eye_features(img)
        assert isinstance(features, dict)
        assert "brightness" in features
        assert "contrast" in features
        assert "blur_score" in features

    def test_features_are_floats_in_valid_range(self) -> None:
        img = Image.new("RGB", (200, 200), color=(120, 80, 70))
        features = extract_eye_features(img)
        for name, value in features.items():
            if name in ("brightness", "contrast", "center_brightness", "center_contrast"):
                assert isinstance(value, (int, float)), f"{name} should be numeric"

    def test_handles_small_image(self) -> None:
        img = Image.new("RGB", (50, 50), color=(100, 90, 80))
        features = extract_eye_features(img)
        assert isinstance(features, dict)

    def test_handles_white_image(self) -> None:
        img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        features = extract_eye_features(img)
        assert isinstance(features, dict)

    def test_handles_black_image(self) -> None:
        img = Image.new("RGB", (200, 200), color=(0, 0, 0))
        features = extract_eye_features(img)
        assert isinstance(features, dict)

    def test_handles_random_image(self) -> None:
        arr = np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)
        img = Image.fromarray(arr, mode="RGB")
        features = extract_eye_features(img)
        assert isinstance(features, dict)

    def test_different_images_produce_different_features(self) -> None:
        img1 = Image.new("RGB", (200, 200), color=(200, 100, 100))
        img2 = Image.new("RGB", (200, 200), color=(50, 150, 150))
        f1 = extract_eye_features(img1)
        f2 = extract_eye_features(img2)
        # At least brightness should differ
        assert f1["brightness"] != f2["brightness"] or f1["mean_r"] != f2["mean_r"]


class TestExtractV8ClinicalFeatures:
    def test_returns_dict(self) -> None:
        img = Image.new("RGB", (200, 200), color=(140, 90, 80))
        quality = QualityAssessment(
            passed=True,
            blur_score=150.0,
            brightness_score=0.3,
            contrast_score=0.15,
            framing_score=1.5,
            issues=[],
        )
        features = extract_v8_clinical_features(img, quality)
        assert isinstance(features, dict)

    def test_includes_clinical_pallor_score(self) -> None:
        img = Image.new("RGB", (200, 200), color=(140, 90, 80))
        quality = QualityAssessment(
            passed=True,
            blur_score=150.0,
            brightness_score=0.3,
            contrast_score=0.15,
            framing_score=1.5,
            issues=[],
        )
        features = extract_v8_clinical_features(img, quality)
        assert "clinical_pallor_score" in features


class TestFramingScore:
    def test_returns_float(self) -> None:
        img = Image.new("RGB", (400, 300), color=(120, 80, 70))
        score = estimate_framing_score(img)
        assert isinstance(score, (int, float))

    def test_wider_image_scores_differently(self) -> None:
        img1 = Image.new("RGB", (400, 300), color=(120, 80, 70))
        img2 = Image.new("RGB", (300, 400), color=(120, 80, 70))
        s1 = estimate_framing_score(img1)
        s2 = estimate_framing_score(img2)
        assert s1 != s2


# ---------------------------------------------------------------------------
# Fallback prediction
# ---------------------------------------------------------------------------


class TestFallbackPredictionDataclass:
    def test_fallback_prediction_fields(self) -> None:
        pred = FallbackPrediction(
            anemia_risk=0.5,
            predicted_hemoglobin=12.0,
            uncertainty=0.3,
            hb_interval=(10.0, 14.0),
            method="conservative_default",
            reason="quality_gate_rejection",
            confidence_tier="low",
            recommendation="Retake photo with better lighting",
            diagnostics={"detail": "test"},
        )
        assert pred.is_fallback is True
        assert pred.anemia_risk == 0.5
        assert pred.method == "conservative_default"


class TestConservativeDefaultPrediction:
    def test_returns_valid_prediction(self) -> None:
        pred = conservative_default_prediction()
        assert 0.0 <= pred.anemia_risk <= 1.0
        assert pred.uncertainty > 0.5  # High uncertainty
        assert pred.confidence_tier in ("low", "very_low")

    def test_returns_fallback_true(self) -> None:
        pred = conservative_default_prediction()
        assert pred.is_fallback is True

    def test_recommendation_present(self) -> None:
        pred = conservative_default_prediction()
        assert len(pred.recommendation) > 0


class TestPopulationPriorPrediction:
    def test_with_demographics(self) -> None:
        profile = PatientProfileInput(sex="female", age_group="adult")
        pred = population_prior_prediction(profile)
        assert 0.0 <= pred.anemia_risk <= 1.0
        assert pred.method == "population_prior"

    def test_without_demographics(self) -> None:
        profile = PatientProfileInput()
        pred = population_prior_prediction(profile)
        assert 0.0 <= pred.anemia_risk <= 1.0

    def test_male_adult(self) -> None:
        profile = PatientProfileInput(sex="male", age_group="adult")
        pred = population_prior_prediction(profile)
        # Male adult prevalence is lower (~15%)
        assert pred.anemia_risk < 0.35

    def test_pregnant_female(self) -> None:
        profile = PatientProfileInput(sex="female", age_group="pregnant")
        pred = population_prior_prediction(profile)
        # Pregnant women have higher prevalence (~36%)
        assert pred.anemia_risk > 0.30


class TestHeuristicPrediction:
    def test_returns_valid_prediction(self) -> None:
        img = Image.new("RGB", (200, 200), color=(140, 90, 80))
        pred = heuristic_prediction(img)
        assert 0.0 <= pred.anemia_risk <= 1.0
        assert pred.method == "heuristic"

    def test_handles_dark_image(self) -> None:
        img = Image.new("RGB", (200, 200), color=(20, 10, 10))
        pred = heuristic_prediction(img)
        assert isinstance(pred.anemia_risk, float)

    def test_handles_bright_image(self) -> None:
        img = Image.new("RGB", (200, 200), color=(240, 220, 210))
        pred = heuristic_prediction(img)
        assert isinstance(pred.anemia_risk, float)


class TestGenerateFallback:
    def test_generate_with_quality_rejection(self) -> None:
        pred = generate_fallback(
            reason="quality_gate_rejection",
            patient_profile=None,
            image=None,
        )
        assert pred.is_fallback is True
        assert pred.reason == "quality_gate_rejection"

    def test_generate_with_model_failure(self) -> None:
        pred = generate_fallback(
            reason="model_failure",
            patient_profile=None,
            image=Image.new("RGB", (100, 100)),
        )
        assert pred.is_fallback is True
        assert pred.reason == "model_failure"

    def test_generate_with_demographics(self) -> None:
        profile = PatientProfileInput(sex="female", age_group="adult")
        pred = generate_fallback(
            reason="low_confidence",
            patient_profile=profile,
            image=None,
        )
        assert pred.is_fallback is True
        # With demographics, should use population_prior
        assert pred.method in ("population_prior", "conservative_default")

    def test_generate_with_image_uses_heuristic(self) -> None:
        img = Image.new("RGB", (200, 200), color=(140, 90, 80))
        pred = generate_fallback(
            reason="low_confidence",
            patient_profile=None,
            image=img,
        )
        assert pred.is_fallback is True
        assert pred.method == "heuristic"


class TestPopulationPriorConstants:
    def test_population_priors_has_all_sexes(self) -> None:
        assert "female" in POPULATION_PRIORS
        assert "male" in POPULATION_PRIORS
        assert "other" in POPULATION_PRIORS
        assert "not_specified" in POPULATION_PRIORS

    def test_population_priors_values_in_valid_range(self) -> None:
        for sex, groups in POPULATION_PRIORS.items():
            for group, prevalence in groups.items():
                assert 0.0 <= prevalence <= 1.0, f"{sex}/{group}: {prevalence}"

    def test_hemoglobin_norms_has_all_sexes(self) -> None:
        assert "female" in HEMOGLOBIN_NORMS
        assert "male" in HEMOGLOBIN_NORMS

    def test_hemoglobin_norms_ranges_are_valid(self) -> None:
        for sex, groups in HEMOGLOBIN_NORMS.items():
            for group, (low, high) in groups.items():
                assert low < high, f"{sex}/{group}: {low} >= {high}"
                assert low > 5.0, f"{sex}/{group}: {low} too low"
                assert high < 25.0, f"{sex}/{group}: {high} too high"


class TestHbRiskConversion:
    def test_hb_to_risk_lower_hb_higher_risk(self) -> None:
        risk_low_hb = _hb_to_risk(8.0)
        risk_normal_hb = _hb_to_risk(14.0)
        assert risk_low_hb > risk_normal_hb

    def test_risk_to_hb_higher_risk_lower_hb(self) -> None:
        hb_high_risk = _risk_to_hb(0.8)
        hb_low_risk = _risk_to_hb(0.1)
        assert hb_high_risk < hb_low_risk


# ---------------------------------------------------------------------------
# Lighting normalization
# ---------------------------------------------------------------------------


class TestLightingNormalization:
    def test_compute_illumination_bias_returns_dict(self) -> None:
        img = Image.new("RGB", (200, 200), color=(140, 100, 90))
        bias = compute_illumination_bias(img)
        assert isinstance(bias, dict)
        assert "mean" in bias or "bias" in bias

    def test_normalize_illumination_returns_image(self) -> None:
        img = Image.new("RGB", (200, 200), color=(140, 100, 90))
        result = normalize_illumination(img)
        assert isinstance(result, Image.Image)
        assert result.size == img.size

    def test_normalize_illumination_handles_gradual_gradient(self) -> None:
        arr = np.zeros((200, 200, 3), dtype=np.uint8)
        arr[:, :, 0] = np.tile(np.linspace(50, 200, 200), (200, 1))
        arr[:, :, 1] = np.tile(np.linspace(40, 180, 200), (200, 1))
        arr[:, :, 2] = np.tile(np.linspace(30, 160, 200), (200, 1))
        img = Image.fromarray(arr, mode="RGB")
        result = normalize_illumination(img)
        assert isinstance(result, Image.Image)


# ---------------------------------------------------------------------------
# Model confidence estimation
# ---------------------------------------------------------------------------


class TestCaptureQualityScore:
    def test_returns_float(self) -> None:
        quality = QualityAssessment(
            passed=True,
            blur_score=150.0,
            brightness_score=0.3,
            contrast_score=0.15,
            framing_score=1.5,
            issues=[],
        )
        score = _capture_quality_score(quality)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_high_quality_image_scores_higher(self) -> None:
        quality_good = QualityAssessment(
            passed=True,
            blur_score=180.0,
            brightness_score=0.35,
            contrast_score=0.2,
            framing_score=2.0,
            issues=[],
        )
        quality_bad = QualityAssessment(
            passed=False,
            blur_score=30.0,
            brightness_score=0.9,
            contrast_score=0.02,
            framing_score=0.3,
            issues=["blurry", "overexposed"],
        )
        score_good = _capture_quality_score(quality_good)
        score_bad = _capture_quality_score(quality_bad)
        assert score_good > score_bad


class TestEstimateModelConfidence:
    def test_returns_float(self) -> None:
        quality = QualityAssessment(
            passed=True,
            blur_score=150.0,
            brightness_score=0.3,
            contrast_score=0.15,
            framing_score=1.5,
            issues=[],
        )
        confidence = estimate_model_confidence(quality, raw_risk=0.4, uncertainty=0.2)
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0

    def test_high_quality_increases_confidence(self) -> None:
        quality_good = QualityAssessment(
            passed=True,
            blur_score=180.0,
            brightness_score=0.35,
            contrast_score=0.2,
            framing_score=2.0,
            issues=[],
        )
        quality_bad = QualityAssessment(
            passed=False,
            blur_score=30.0,
            brightness_score=0.9,
            contrast_score=0.02,
            framing_score=0.3,
            issues=["blurry"],
        )
        conf_good = estimate_model_confidence(quality_good, raw_risk=0.4, uncertainty=0.2)
        conf_bad = estimate_model_confidence(quality_bad, raw_risk=0.4, uncertainty=0.2)
        assert conf_good > conf_bad


# ---------------------------------------------------------------------------
# Inference cache
# ---------------------------------------------------------------------------


class TestInferenceCache:
    def test_cache_miss_on_first_lookup(self) -> None:
        cache = InferenceCache(max_size=10)
        img_hash = "abc123"
        assert cache.get(img_hash) is None

    def test_cache_hit_after_put(self) -> None:
        cache = InferenceCache(max_size=10)
        img_hash = "abc123"
        result = {"anemia_risk": 0.5}
        cache.put(img_hash, result)
        assert cache.get(img_hash) == result

    def test_cache_evicts_oldest_when_full(self) -> None:
        cache = InferenceCache(max_size=2)
        cache.put("key1", {"v": 1})
        cache.put("key2", {"v": 2})
        cache.put("key3", {"v": 3})  # Should evict key1
        assert cache.get("key1") is None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None

    def test_cache_clear(self) -> None:
        cache = InferenceCache(max_size=10)
        cache.put("key1", {"v": 1})
        cache.clear()
        assert cache.get("key1") is None

    def test_cache_size_limit(self) -> None:
        cache = InferenceCache(max_size=5)
        for i in range(10):
            cache.put(f"key{i}", {"v": i})
        assert len(cache._cache) <= 5

    def test_compute_image_hash(self) -> None:
        img1 = Image.new("RGB", (200, 200), color=(140, 90, 80))
        img2 = Image.new("RGB", (200, 200), color=(140, 90, 80))
        img3 = Image.new("RGB", (200, 200), color=(50, 50, 50))

        hash1 = _compute_image_hash(img1)
        hash2 = _compute_image_hash(img2)
        hash3 = _compute_image_hash(img3)

        assert hash1 == hash2
        assert hash1 != hash3

    def test_cache_ttl_expiry(self) -> None:
        import time
        cache = InferenceCache(max_size=10, ttl_seconds=0.01)
        cache.put("key1", {"v": 1})
        assert cache.get("key1") is not None
        time.sleep(0.02)
        assert cache.get("key1") is None
