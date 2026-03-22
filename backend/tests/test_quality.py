"""
Tests for ImageQualityService.

Each test creates a synthetic image designed to trigger (or avoid) a specific
quality gate.  This is deliberately independent of real photos so CI never
needs access to patient data.

Coverage targets:
- Flat/uniform images fail with a clear issue code.
- A synthetic eye-like pattern (iris + sclera + lower lid) passes.
- Mild lighting warnings are non-blocking.
- Bright but detailed images are not penalised.
- Non-eye close-ups fail with eye_not_visible before lighting feedback.
- Large real-world-style images trigger ROI cropping and pass.
- issue_codes and blocking_issues computed properties work correctly.
"""

from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.image_quality import ImageQualityService
from app.services.conjunctiva_roi import ConjunctivaRoiExtractor
from app.schemas import QualityIssue


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_bytes(array: np.ndarray, fmt: str = "PNG") -> bytes:
    img = Image.fromarray(array.astype("uint8"), mode="RGB")
    buf = BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def _eye_canvas(
    size: int = 360,
    bg: int = 45,
    iris_r: int = 55,
    sclera_rx: int = 120,
    sclera_ry: int = 70,
    iris_color: tuple = (20, 30, 45),
    sclera_color: tuple = (190, 120, 120),
    lid_boost: tuple = (35, 8, 8),
) -> np.ndarray:
    """Build a synthetic eye-like pattern centred in a square canvas."""
    canvas = np.full((size, size, 3), bg, dtype=np.uint8)
    cx, cy = size // 2, size // 2
    yy, xx = np.ogrid[:size, :size]

    iris_mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= iris_r ** 2
    sclera_mask = (xx - cx) ** 2 / sclera_rx ** 2 + (yy - cy) ** 2 / sclera_ry ** 2 <= 1

    canvas[sclera_mask] = sclera_color
    canvas[iris_mask] = iris_color

    # Lower-lid conjunctiva highlight
    lid_y_start, lid_y_end = cy - size // 20, cy + size // 4
    lid_x_start, lid_x_end = cx - sclera_rx + 10, cx + sclera_rx - 10
    canvas[lid_y_start:lid_y_end, lid_x_start:lid_x_end] = np.clip(
        canvas[lid_y_start:lid_y_end, lid_x_start:lid_x_end] + lid_boost, 0, 255
    )
    return canvas


SERVICE = ImageQualityService()
ROI_EXTRACTOR = ConjunctivaRoiExtractor()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_flat_uniform_image_fails() -> None:
    rgb = np.full((320, 320, 3), 140, dtype=np.uint8)
    quality, _ = SERVICE.evaluate(_to_bytes(rgb))

    assert quality.passed is False
    assert quality.issue_codes & {"eye_not_visible", "poor_lighting", "blur_detected"}


def test_eye_like_pattern_passes() -> None:
    canvas = _eye_canvas()
    quality, _ = SERVICE.evaluate(_to_bytes(canvas))
    assert quality.passed is True


def test_mild_lighting_warning_is_non_blocking() -> None:
    """Slightly dim image should warn but allow analysis to proceed."""
    canvas = _eye_canvas(bg=96, sclera_color=(214, 176, 176))
    quality, _ = SERVICE.evaluate(_to_bytes(canvas))

    assert quality.passed is True
    assert "poor_lighting" in quality.issue_codes
    assert len(quality.blocking_issues) == 0
    assert quality.lighting_condition
    assert quality.lighting_summary
    assert 0.0 <= quality.glare_risk <= 1.0
    assert 0.0 <= quality.shadow_risk <= 1.0


def test_bright_detailed_eye_is_not_blocked() -> None:
    """A well-lit image with a visible iris should not be rejected for brightness."""
    canvas = _eye_canvas(bg=148, sclera_color=(238, 210, 210), iris_color=(25, 35, 52))
    quality, _ = SERVICE.evaluate(_to_bytes(canvas))

    assert quality.brightness_score > 0.42
    assert quality.passed is True
    assert len(quality.blocking_issues) == 0
    assert quality.lighting_score > 0.35


def test_lighting_intelligence_detects_glare_heavy() -> None:
    score, condition, summary, glare_risk, shadow_risk = SERVICE._lighting_intelligence(
        brightness_score=0.56,
        contrast_score=0.16,
        center_brightness=0.62,
        center_contrast=0.15,
        bright_region_ratio=0.31,
        highlight_ratio=0.18,
        dark_region_ratio=0.05,
    )

    assert 0.0 <= score <= 1.0
    assert condition == "glare_heavy"
    assert glare_risk >= 0.72
    assert "glare" in summary.lower()
    assert 0.0 <= shadow_risk <= 1.0


def test_lighting_intelligence_marks_balanced_capture() -> None:
    score, condition, summary, glare_risk, shadow_risk = SERVICE._lighting_intelligence(
        brightness_score=0.28,
        contrast_score=0.18,
        center_brightness=0.29,
        center_contrast=0.17,
        bright_region_ratio=0.08,
        highlight_ratio=0.01,
        dark_region_ratio=0.12,
    )

    assert condition == "balanced"
    assert score > 0.65
    assert "balanced" in summary.lower()
    assert glare_risk < 0.3
    assert shadow_risk < 0.3


def test_non_eye_closeup_fails_with_eye_not_visible_first() -> None:
    """
    A non-eye pattern should fail, and the first issue reported should be
    eye_not_visible — not a lighting complaint.
    """
    yy, xx = np.indices((360, 360))
    canvas = np.zeros((360, 360, 3), dtype=np.uint8)
    canvas[..., 0] = 164 + ((xx // 18) % 2) * 18
    canvas[..., 1] = 126 + ((yy // 18) % 2) * 12
    canvas[..., 2] = 106
    canvas[118:242, 118:242] = [106, 86, 70]

    quality, _ = SERVICE.evaluate(_to_bytes(canvas))

    assert quality.passed is False
    assert quality.issues[0].code == "eye_not_visible"
    assert "poor_lighting" not in quality.issue_codes


def test_large_image_triggers_roi_crop_and_passes() -> None:
    """
    A large photo with the eye off-centre (realistic phone photo) should be
    auto-cropped to the ROI and still pass quality.
    """
    canvas = np.full((900, 1200, 3), [214, 180, 165], dtype=np.uint8)
    yy, xx = np.indices((900, 1200))

    sclera = (xx - 650) ** 2 / 200 ** 2 + (yy - 520) ** 2 / 150 ** 2 <= 1
    iris = (xx - 650) ** 2 + (yy - 520) ** 2 <= 82 ** 2
    lower_lid = (xx - 650) ** 2 / 230 ** 2 + (yy - 650) ** 2 / 82 ** 2 <= 1
    finger = (xx - 680) ** 2 / 170 ** 2 + (yy - 810) ** 2 / 120 ** 2 <= 1

    canvas[sclera] = [198, 206, 212]
    canvas[iris] = [78, 92, 98]
    canvas[lower_lid] = [232, 182, 188]
    canvas[(lower_lid) & (yy >= 650)] = [192, 96, 108]
    canvas[finger] = [198, 158, 140]
    canvas[330:430, 220:980] = np.clip(canvas[330:430, 220:980] - [120, 120, 120], 0, 255)

    quality, roi_image = SERVICE.evaluate(_to_bytes(canvas))

    assert quality.passed is True
    assert "roi_cropped" in quality.issue_codes
    assert roi_image.size[0] < 500
    assert roi_image.size[1] < 260


def test_roi_extractor_falls_back_to_conjunctiva_band_when_iris_detection_misses() -> None:
    canvas = np.full((900, 1200, 3), [210, 178, 166], dtype=np.uint8)
    yy, xx = np.indices((900, 1200))

    lid_band = (xx - 620) ** 2 / 260 ** 2 + (yy - 560) ** 2 / 90 ** 2 <= 1
    canvas[lid_band] = [212, 118, 132]
    canvas[(lid_band) & (yy >= 560)] = [188, 88, 104]
    canvas[260:360, 140:1080] = np.clip(canvas[260:360, 140:1080] - [95, 95, 95], 0, 255)

    result = ROI_EXTRACTOR.extract(Image.fromarray(canvas.astype("uint8"), mode="RGB"))

    assert result.extracted is True
    assert result.image.size[0] < canvas.shape[1]
    assert result.image.size[1] < canvas.shape[0]
    assert result.image.size[0] >= 110
    assert result.image.size[1] >= 40


@pytest.mark.parametrize("fmt", ["JPEG", "PNG"])
def test_both_image_formats_accepted(fmt: str) -> None:
    canvas = _eye_canvas()
    quality, _ = SERVICE.evaluate(_to_bytes(canvas, fmt=fmt))
    assert quality.passed is True


def test_quality_assessment_computed_properties() -> None:
    canvas = _eye_canvas(bg=96, sclera_color=(214, 176, 176))
    quality, _ = SERVICE.evaluate(_to_bytes(canvas))

    # Validate cached_property helpers
    assert isinstance(quality.issue_codes, frozenset)
    assert isinstance(quality.blocking_issues, list)
    assert isinstance(quality.warning_issues, list)
    assert all(i.severity == "blocking" for i in quality.blocking_issues)
    assert all(i.severity == "warning" for i in quality.warning_issues)


def test_runtime_quality_issue_codes_validate_against_schema() -> None:
    QualityIssue(
        code="resolution_too_low",
        severity="blocking",
        title="Image is too small",
        message="Move closer and retake the photo.",
    )
    QualityIssue(
        code="bad_framing",
        severity="warning",
        title="Eye framing is loose",
        message="Center the exposed lower eyelid more tightly.",
    )


def test_roi_salvage_rule_allows_recoverable_crop() -> None:
    issues = [
        QualityIssue(
            code="roi_cropped",
            severity="warning",
            title="Lower eyelid region detected",
            message="ROI extracted.",
        ),
        QualityIssue(
            code="bad_framing",
            severity="blocking",
            title="Eye is not framed clearly",
            message="Fill the frame with one eye.",
        ),
    ]

    assert SERVICE._should_salvage_roi_capture(
        issues,
        roi_extracted=True,
        blur_score=220.0,
        brightness_score=0.41,
        contrast_score=0.14,
        framing_score=2.4,
    )

    softened = SERVICE._soften_salvageable_roi_blocks(
        issues,
        roi_extracted=True,
        blur_score=220.0,
        brightness_score=0.41,
        contrast_score=0.14,
        framing_score=2.4,
    )
    assert softened[1].severity == "warning"


def test_roi_salvage_rule_rejects_low_contrast_crop() -> None:
    issues = [
        QualityIssue(
            code="roi_cropped",
            severity="warning",
            title="Lower eyelid region detected",
            message="ROI extracted.",
        ),
        QualityIssue(
            code="eye_not_visible",
            severity="blocking",
            title="Eye is not clearly visible",
            message="Retake with the lower eyelid visible.",
        ),
    ]

    assert not SERVICE._should_salvage_roi_capture(
        issues,
        roi_extracted=True,
        blur_score=220.0,
        brightness_score=0.41,
        contrast_score=0.08,
        framing_score=2.8,
    )


def test_roi_salvage_rule_allows_clarity_exception_for_bad_framing() -> None:
    issues = [
        QualityIssue(
            code="roi_cropped",
            severity="warning",
            title="Lower eyelid region detected",
            message="ROI extracted.",
        ),
        QualityIssue(
            code="bad_framing",
            severity="blocking",
            title="Eye is not framed clearly",
            message="Fill the frame with one eye.",
        ),
    ]

    assert SERVICE._should_salvage_roi_capture(
        issues,
        roi_extracted=True,
        blur_score=340.0,
        brightness_score=0.56,
        contrast_score=0.17,
        framing_score=1.8,
    )


def test_raw_frame_rescue_allowed_for_framing_and_visibility_blocks() -> None:
    assessment = SERVICE.build_raw_frame_rescue_assessment(
        SERVICE.evaluate(_to_bytes(_eye_canvas(size=900, bg=70)))[0].model_copy(
            update={
                "passed": False,
                "issues": [
                    QualityIssue(
                        code="roi_cropped",
                        severity="warning",
                        title="Lower eyelid region detected",
                        message="ROI extracted.",
                    ),
                    QualityIssue(
                        code="eye_not_visible",
                        severity="blocking",
                        title="Eye is not clearly visible",
                        message="Retake with one eye filling the frame.",
                    ),
                ],
            }
        )
    )

    assert assessment.passed is True
    assert all(issue.severity == "warning" for issue in assessment.issues)


def test_raw_frame_rescue_allowed_for_isolated_poor_lighting_block() -> None:
    assessment = SERVICE.evaluate(_to_bytes(_eye_canvas(size=900, bg=70)))[0].model_copy(
        update={
            "passed": False,
            "issues": [
                QualityIssue(
                    code="poor_lighting",
                    severity="blocking",
                    title="Lighting is not usable",
                    message="Use bright, even light.",
                ),
            ],
        }
    )

    rescued = SERVICE.build_raw_frame_rescue_assessment(assessment)

    assert SERVICE.allows_raw_frame_rescue(assessment) is True
    assert rescued.passed is True
    assert rescued.issues[0].severity == "warning"


def test_raw_frame_rescue_not_allowed_for_mixed_lighting_and_blur_blocks() -> None:
    assessment = SERVICE.evaluate(_to_bytes(_eye_canvas(size=900, bg=70)))[0].model_copy(
        update={
            "passed": False,
            "issues": [
                QualityIssue(
                    code="poor_lighting",
                    severity="blocking",
                    title="Lighting is not usable",
                    message="Use bright, even light.",
                ),
                QualityIssue(
                    code="blur_detected",
                    severity="blocking",
                    title="Image looks blurry",
                    message="Hold steady and retake the photo.",
                ),
            ],
        }
    )

    assert SERVICE.allows_raw_frame_rescue(assessment) is False
