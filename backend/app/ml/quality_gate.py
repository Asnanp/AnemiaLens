"""
quality_gate.py — Pre-inference image quality gate for AnemiaLens.

Rejects images that are too blurry, dark, or otherwise unsuitable for ML
inference *before* feature extraction, providing specific actionable feedback.

This is a fast, lightweight gate (<10ms) that runs before the expensive
feature extraction pipeline, saving compute and giving users immediate
feedback on why their image was rejected.

Quality Gate Levels
-------------------
- PASS: Image meets all quality thresholds; proceed to ML inference.
- WARN: Image has quality issues but is still usable; proceed with caution.
- REJECT: Image is too degraded for reliable inference; request retake.

Metrics Evaluated
-----------------
1. Blur: Laplacian variance of grayscale image.
2. Brightness: Mean luminance relative to expected range.
3. Contrast: Standard deviation of luminance.
4. Noise: Estimated noise level via bilateral filter residual.
5. Overexposure: Fraction of pixels at saturation (255).
6. Underexposure: Fraction of pixels near black (0).
7. Resolution: Minimum pixel dimensions.
8. Color validity: Check for monochrome or near-monochrome images.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from PIL import Image, ImageFilter, ImageStat

QualityGateDecision = Literal["pass", "warn", "reject"]


@dataclass(frozen=True)
class QualityGateIssue:
    """A single quality gate finding."""
    metric: str            # e.g. "blur", "brightness", "noise"
    severity: QualityGateDecision  # "reject" or "warn"
    value: float           # Measured value
    threshold: float       # Threshold that was crossed
    message: str           # User-facing explanation
    suggestion: str        # Actionable fix suggestion
    # Enhanced fields for detailed feedback
    improvement_steps: list[str] = field(default_factory=list)  # Step-by-step improvement guide
    severity_score: float = 0.0  # Normalized severity [0, 1] for prioritization
    estimated_impact: str = ""   # "critical", "high", "medium", "low"


@dataclass(frozen=True)
class QualityGateResult:
    """Result of the pre-inference quality gate."""
    decision: QualityGateDecision  # "pass", "warn", "reject"
    overall_score: float         # Composite quality score [0, 1]
    issues: list[QualityGateIssue] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    rejection_reason: str | None = None  # Set when decision == "reject"
    can_proceed: bool = True             # False only when decision == "reject"
    # Enhanced fields for detailed feedback
    detailed_feedback: str = ""          # Comprehensive feedback for the user
    improvement_plan: list[str] = field(default_factory=list)  # Prioritized steps
    estimated_quality_if_fixed: float = 0.0  # Predicted score if suggestions followed


# ─────────────────────────────────────────────────────────────────────────────
# Thresholds — tuned for conjunctival smartphone photography
# ─────────────────────────────────────────────────────────────────────────────

# Blur: Laplacian variance thresholds
_BLUR_REJECT_THRESHOLD = 15.0   # Below this = definitely too blurry
_BLUR_WARN_THRESHOLD = 45.0     # Below this = somewhat soft

# Brightness: Mean luminance [0, 255]
_BRIGHTNESS_REJECT_LOW = 15     # Near-black
_BRIGHTNESS_WARN_LOW = 30       # Very dim
_BRIGHTNESS_REJECT_HIGH = 245   # Near-white (overexposed)
_BRIGHTNESS_WARN_HIGH = 230     # Too bright

# Contrast: Std of luminance [0, 255]
_CONTRAST_REJECT_THRESHOLD = 5.0   # Flat image
_CONTRAST_WARN_THRESHOLD = 12.0    # Low contrast

# Noise: Estimated noise level (bilateral residual std)
_NOISE_REJECT_THRESHOLD = 35.0  # Very noisy
_NOISE_WARN_THRESHOLD = 20.0    # Noticeable noise

# Overexposure: Fraction of saturated pixels
_OVEREXPOSE_REJECT_FRACTION = 0.15   # >15% saturated
_OVEREXPOSE_WARN_FRACTION = 0.05     # >5% saturated

# Underexposure: Fraction of near-black pixels
_UNDEREXPOSE_REJECT_FRACTION = 0.20   # >20% near-black
_UNDEREXPOSE_WARN_FRACTION = 0.10     # >10% near-black

# Resolution
_MIN_WIDTH_REJECT = 64
_MIN_HEIGHT_REJECT = 32
_MIN_WIDTH_WARN = 100
_MIN_HEIGHT_WARN = 50

# Color validity: Saturation threshold
_MONOCHROME_REJECT_THRESHOLD = 0.02   # Nearly grayscale
_MONOCHROME_WARN_THRESHOLD = 0.05     # Very low saturation


class ImageQualityGate:
    """
    Fast pre-inference quality gate that rejects unusable images.

    Usage
    -----
    gate = ImageQualityGate()
    result = gate.evaluate(pil_image)
    if not result.can_proceed:
        return error_response(result.rejection_reason)
    """

    def evaluate(self, image: Image.Image) -> QualityGateResult:
        """
        Evaluate an image against all quality gates.

        Parameters
        ----------
        image : PIL.Image — RGB input

        Returns
        -------
        QualityGateResult with decision, issues, and metrics
        """
        issues: list[QualityGateIssue] = []
        metrics: dict[str, float] = {}

        # Convert to working representations
        gray = image.convert("L")
        gray_arr = np.asarray(gray, dtype=np.float64)
        width, height = image.size

        # ── 1. Blur detection ───────────────────────────────────────────────
        blur_score = self._measure_blur(gray)
        metrics["blur_score"] = blur_score
        if blur_score < _BLUR_REJECT_THRESHOLD:
            severity_score = max(0.0, 1.0 - blur_score / _BLUR_REJECT_THRESHOLD)
            issues.append(QualityGateIssue(
                metric="blur",
                severity="reject",
                value=blur_score,
                threshold=_BLUR_REJECT_THRESHOLD,
                message="The image is too blurry for reliable analysis.",
                suggestion="Hold the camera steady, tap to focus on the eye, and retake.",
                improvement_steps=[
                    "Rest your elbows on a stable surface.",
                    "Tap the screen where the eye appears to set focus.",
                    "Wait for the camera to lock focus before capturing.",
                    "Use burst mode and select the sharpest image.",
                ],
                severity_score=round(severity_score, 3),
                estimated_impact="critical",
            ))
        elif blur_score < _BLUR_WARN_THRESHOLD:
            severity_score = max(0.0, 1.0 - blur_score / _BLUR_WARN_THRESHOLD) * 0.5
            issues.append(QualityGateIssue(
                metric="blur",
                severity="warn",
                value=blur_score,
                threshold=_BLUR_WARN_THRESHOLD,
                message="The image is slightly soft; results may be less reliable.",
                suggestion="Try to keep the camera steady and ensure good focus.",
                improvement_steps=[
                    "Hold the phone closer to your face for stability.",
                    "Ensure adequate lighting so the camera can use a faster shutter speed.",
                ],
                severity_score=round(severity_score, 3),
                estimated_impact="medium",
            ))

        # ── 2. Brightness assessment ────────────────────────────────────────
        brightness = float(gray_arr.mean())
        metrics["brightness_raw"] = brightness
        if brightness < _BRIGHTNESS_REJECT_LOW:
            issues.append(QualityGateIssue(
                metric="brightness",
                severity="reject",
                value=brightness,
                threshold=_BRIGHTNESS_REJECT_LOW,
                message="The image is too dark to analyze.",
                suggestion="Move to a brighter location or turn on the flash.",
                improvement_steps=[
                    "Move near a window or turn on room lights.",
                    "Enable the camera flash.",
                    "Avoid taking photos in dimly lit rooms.",
                ],
                severity_score=round(max(0.0, 1.0 - brightness / _BRIGHTNESS_REJECT_LOW), 3),
                estimated_impact="critical",
            ))
        elif brightness < _BRIGHTNESS_WARN_LOW:
            issues.append(QualityGateIssue(
                metric="brightness",
                severity="warn",
                value=brightness,
                threshold=_BRIGHTNESS_WARN_LOW,
                message="The image is dim; subtle details may be lost.",
                suggestion="Use brighter, even lighting.",
                improvement_steps=["Add more light sources or move closer to existing light."],
                severity_score=round(max(0.0, 1.0 - brightness / _BRIGHTNESS_WARN_LOW) * 0.5, 3),
                estimated_impact="medium",
            ))
        elif brightness > _BRIGHTNESS_REJECT_HIGH:
            issues.append(QualityGateIssue(
                metric="brightness",
                severity="reject",
                value=brightness,
                threshold=_BRIGHTNESS_REJECT_HIGH,
                message="The image is overexposed; details are washed out.",
                suggestion="Reduce brightness or move away from direct light.",
                improvement_steps=[
                    "Step away from direct sunlight or bright lamps.",
                    "Tap the screen to set exposure on the brightest area.",
                    "Use exposure compensation to reduce brightness.",
                ],
                severity_score=round(min(1.0, (brightness - _BRIGHTNESS_REJECT_HIGH) / (255 - _BRIGHTNESS_REJECT_HIGH)), 3),
                estimated_impact="critical",
            ))
        elif brightness > _BRIGHTNESS_WARN_HIGH:
            issues.append(QualityGateIssue(
                metric="brightness",
                severity="warn",
                value=brightness,
                threshold=_BRIGHTNESS_WARN_HIGH,
                message="The image is quite bright.",
                suggestion="Soften the lighting to preserve tissue detail.",
                improvement_steps=["Diffuse harsh light with a thin cloth or move to indirect lighting."],
                severity_score=round(min(1.0, (brightness - _BRIGHTNESS_WARN_HIGH) / (255 - _BRIGHTNESS_WARN_HIGH)) * 0.5, 3),
                estimated_impact="low",
            ))

        # ── 3. Contrast assessment ──────────────────────────────────────────
        contrast = float(gray_arr.std())
        metrics["contrast_raw"] = contrast
        if contrast < _CONTRAST_REJECT_THRESHOLD:
            issues.append(QualityGateIssue(
                metric="contrast",
                severity="reject",
                value=contrast,
                threshold=_CONTRAST_REJECT_THRESHOLD,
                message="The image has almost no contrast.",
                suggestion="Ensure proper focus and adequate lighting.",
                improvement_steps=[
                    "Clean the camera lens — smudges reduce contrast.",
                    "Ensure the eye is well-lit from the side, not front-on.",
                    "Avoid foggy or steamy environments.",
                ],
                severity_score=round(max(0.0, 1.0 - contrast / _CONTRAST_REJECT_THRESHOLD), 3),
                estimated_impact="critical",
            ))
        elif contrast < _CONTRAST_WARN_THRESHOLD:
            issues.append(QualityGateIssue(
                metric="contrast",
                severity="warn",
                value=contrast,
                threshold=_CONTRAST_WARN_THRESHOLD,
                message="The image has low contrast.",
                suggestion="Improve lighting to enhance tissue detail.",
                improvement_steps=["Try side-lighting instead of front-lighting for better tissue definition."],
                severity_score=round(max(0.0, 1.0 - contrast / _CONTRAST_WARN_THRESHOLD) * 0.5, 3),
                estimated_impact="medium",
            ))

        # ── 4. Noise estimation ─────────────────────────────────────────────
        noise_level = self._estimate_noise(image)
        metrics["noise_level"] = noise_level
        if noise_level > _NOISE_REJECT_THRESHOLD:
            issues.append(QualityGateIssue(
                metric="noise",
                severity="reject",
                value=noise_level,
                threshold=_NOISE_REJECT_THRESHOLD,
                message="The image has excessive noise/grain.",
                suggestion="Use better lighting; avoid high ISO or digital zoom.",
                improvement_steps=[
                    "Increase ambient lighting — noise is worse in low light.",
                    "Avoid digital zoom; move closer instead.",
                    "Use the rear camera (typically less noisy than front).",
                    "Turn off night mode if it introduces grain.",
                ],
                severity_score=round(min(1.0, noise_level / (_NOISE_REJECT_THRESHOLD * 1.5)), 3),
                estimated_impact="critical",
            ))
        elif noise_level > _NOISE_WARN_THRESHOLD:
            issues.append(QualityGateIssue(
                metric="noise",
                severity="warn",
                value=noise_level,
                threshold=_NOISE_WARN_THRESHOLD,
                message="The image has noticeable noise.",
                suggestion="Improve lighting conditions to reduce grain.",
                improvement_steps=["Add more light to reduce camera sensor noise."],
                severity_score=round(min(1.0, noise_level / (_NOISE_REJECT_THRESHOLD * 1.5)) * 0.5, 3),
                estimated_impact="medium",
            ))

        # ── 5. Overexposure check ───────────────────────────────────────────
        rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
        overexposed_frac = float(np.any(rgb >= 255, axis=2).sum()) / max(rgb.shape[0] * rgb.shape[1], 1)
        metrics["overexposed_fraction"] = overexposed_frac
        if overexposed_frac > _OVEREXPOSE_REJECT_FRACTION:
            issues.append(QualityGateIssue(
                metric="overexposure",
                severity="reject",
                value=overexposed_frac,
                threshold=_OVEREXPOSE_REJECT_FRACTION,
                message="Too much of the image is blown out by bright light.",
                suggestion="Turn off flash and avoid direct light on the eye.",
                improvement_steps=[
                    "Turn off the camera flash.",
                    "Angle the light source to the side, not directly at the eye.",
                    "Use exposure lock on a bright area before capturing.",
                ],
                severity_score=round(min(1.0, overexposed_frac / (_OVEREXPOSE_REJECT_FRACTION * 1.5)), 3),
                estimated_impact="critical",
            ))
        elif overexposed_frac > _OVEREXPOSE_WARN_FRACTION:
            issues.append(QualityGateIssue(
                metric="overexposure",
                severity="warn",
                value=overexposed_frac,
                threshold=_OVEREXPOSE_WARN_FRACTION,
                message="Some areas are overexposed.",
                suggestion="Soften the lighting to preserve detail.",
                improvement_steps=["Diffuse harsh light or reduce flash intensity."],
                severity_score=round(min(1.0, overexposed_frac / (_OVEREXPOSE_REJECT_FRACTION * 1.5)) * 0.5, 3),
                estimated_impact="medium",
            ))

        # ── 6. Underexposure check ──────────────────────────────────────────
        underexposed_frac = float(np.all(rgb < 10, axis=2).sum()) / max(rgb.shape[0] * rgb.shape[1], 1)
        metrics["underexposed_fraction"] = underexposed_frac
        if underexposed_frac > _UNDEREXPOSE_REJECT_FRACTION:
            issues.append(QualityGateIssue(
                metric="underexposure",
                severity="reject",
                value=underexposed_frac,
                threshold=_UNDEREXPOSE_REJECT_FRACTION,
                message="Most of the image is too dark to analyze.",
                suggestion="Add more light and retake the photo.",
                improvement_steps=[
                    "Move to a well-lit area or turn on lights.",
                    "Enable the camera flash or use a lamp.",
                    "Gently pull down the eyelid to expose more tissue.",
                ],
                severity_score=round(min(1.0, underexposed_frac / (_UNDEREXPOSE_REJECT_FRACTION * 1.5)), 3),
                estimated_impact="critical",
            ))
        elif underexposed_frac > _UNDEREXPOSE_WARN_FRACTION:
            issues.append(QualityGateIssue(
                metric="underexposure",
                severity="warn",
                value=underexposed_frac,
                threshold=_UNDEREXPOSE_WARN_FRACTION,
                message="Significant portions of the image are very dark.",
                suggestion="Improve lighting for better visibility.",
                improvement_steps=["Add ambient light or use a soft light source near the eye."],
                severity_score=round(min(1.0, underexposed_frac / (_UNDEREXPOSE_REJECT_FRACTION * 1.5)) * 0.5, 3),
                estimated_impact="medium",
            ))

        # ── 7. Resolution check ─────────────────────────────────────────────
        metrics["width"] = float(width)
        metrics["height"] = float(height)
        if width < _MIN_WIDTH_REJECT or height < _MIN_HEIGHT_REJECT:
            issues.append(QualityGateIssue(
                metric="resolution",
                severity="reject",
                value=min(width, height),
                threshold=max(_MIN_WIDTH_REJECT, _MIN_HEIGHT_REJECT),
                message="The image resolution is too low.",
                suggestion="Move closer to the eye and use a higher resolution camera.",
                improvement_steps=[
                    "Move the camera closer so the eye fills most of the frame.",
                    "Use the highest resolution setting on your camera.",
                    "Avoid cropping — capture the full image and let the system crop.",
                ],
                severity_score=round(max(0.0, 1.0 - min(width, height) / max(_MIN_WIDTH_REJECT, _MIN_HEIGHT_REJECT)), 3),
                estimated_impact="critical",
            ))
        elif width < _MIN_WIDTH_WARN or height < _MIN_HEIGHT_WARN:
            issues.append(QualityGateIssue(
                metric="resolution",
                severity="warn",
                value=min(width, height),
                threshold=max(_MIN_WIDTH_WARN, _MIN_HEIGHT_WARN),
                message="The image is quite small.",
                suggestion="Move closer for better detail.",
                improvement_steps=["Move closer so the eye fills about half the frame."],
                severity_score=round(max(0.0, 1.0 - min(width, height) / max(_MIN_WIDTH_WARN, _MIN_HEIGHT_WARN)) * 0.5, 3),
                estimated_impact="low",
            ))

        # ── 8. Color validity check ─────────────────────────────────────────
        saturation = self._mean_saturation(image)
        metrics["saturation"] = saturation
        if saturation < _MONOCHROME_REJECT_THRESHOLD:
            issues.append(QualityGateIssue(
                metric="color_validity",
                severity="reject",
                value=saturation,
                threshold=_MONOCHROME_REJECT_THRESHOLD,
                message="The image appears to be grayscale; color is needed for analysis.",
                suggestion="Ensure the camera is capturing in color mode.",
                improvement_steps=[
                    "Check that your camera is not set to black-and-white mode.",
                    "Disable any monochrome filters.",
                    "Ensure proper color lighting (avoid sodium-vapor orange lighting).",
                ],
                severity_score=round(max(0.0, 1.0 - saturation / _MONOCHROME_REJECT_THRESHOLD), 3),
                estimated_impact="critical",
            ))
        elif saturation < _MONOCHROME_WARN_THRESHOLD:
            issues.append(QualityGateIssue(
                metric="color_validity",
                severity="warn",
                value=saturation,
                threshold=_MONOCHROME_WARN_THRESHOLD,
                message="The image has very low color saturation.",
                suggestion="Ensure good lighting and color capture.",
                improvement_steps=["Use natural daylight or white LED light for accurate colors."],
                severity_score=round(max(0.0, 1.0 - saturation / _MONOCHROME_WARN_THRESHOLD) * 0.5, 3),
                estimated_impact="medium",
            ))

        # ── Decision logic ──────────────────────────────────────────────────
        reject_issues = [i for i in issues if i.severity == "reject"]
        warn_issues = [i for i in issues if i.severity == "warn"]

        if reject_issues:
            decision: QualityGateDecision = "reject"
            rejection_reason = self._build_rejection_message(reject_issues)
            can_proceed = False
        elif warn_issues:
            decision = "warn"
            rejection_reason = None
            can_proceed = True
        else:
            decision = "pass"
            rejection_reason = None
            can_proceed = True

        overall_score = self._compute_overall_score(metrics, issues)
        metrics["overall_quality_score"] = overall_score

        # Generate detailed feedback
        detailed_feedback = self._build_detailed_feedback(issues, overall_score, metrics)
        improvement_plan = self._build_improvement_plan(issues)
        estimated_if_fixed = self._estimate_quality_if_fixed(overall_score, issues)

        return QualityGateResult(
            decision=decision,
            overall_score=round(overall_score, 3),
            issues=issues,
            metrics=metrics,
            rejection_reason=rejection_reason,
            can_proceed=can_proceed,
            detailed_feedback=detailed_feedback,
            improvement_plan=improvement_plan,
            estimated_quality_if_fixed=round(estimated_if_fixed, 3),
        )

    # ──────────────────────────────────────────────────────────────────────
    # Private measurement helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _measure_blur(gray: Image.Image) -> float:
        """Laplacian variance as blur metric."""
        kernel = ImageFilter.Kernel(
            (3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1, offset=0
        )
        edge_img = gray.filter(kernel)
        return float(ImageStat.Stat(edge_img).var[0])

    @staticmethod
    def _estimate_noise(image: Image.Image) -> float:
        """
        Estimate noise level via bilateral filter residual.

        The bilateral filter smooths while preserving edges. The residual
        (original - smoothed) gives us a noise estimate.
        """
        # Resize for speed
        small = image.resize((128, 128)).convert("L")
        arr = np.asarray(small, dtype=np.float64)

        # Approximate bilateral with Gaussian blur (PIL doesn't have bilateral)
        smoothed = np.asarray(small.filter(ImageFilter.GaussianBlur(radius=2)), dtype=np.float64)
        residual = arr - smoothed
        return float(np.std(residual))

    @staticmethod
    def _mean_saturation(image: Image.Image) -> float:
        """Compute mean saturation in HSV space."""
        hsv = image.convert("HSV")
        s_channel = hsv.split()[1]
        return float(ImageStat.Stat(s_channel).mean[0]) / 255.0

    @staticmethod
    def _compute_overall_score(
        metrics: dict[str, float],
        issues: list[QualityGateIssue],
    ) -> float:
        """
        Composite quality score [0, 1].

        Weighted combination of individual metrics, penalized by issues.
        """
        # Individual scores normalized to [0, 1]
        blur_score = min(metrics.get("blur_score", 50.0) / 200.0, 1.0)
        brightness_raw = metrics.get("brightness_raw", 128.0)
        brightness_score = 1.0 - abs(brightness_raw - 128.0) / 128.0
        contrast_raw = metrics.get("contrast_raw", 40.0)
        contrast_score = min(contrast_raw / 80.0, 1.0)
        noise_level = metrics.get("noise_level", 10.0)
        noise_score = max(0.0, 1.0 - noise_level / 50.0)
        overexp = metrics.get("overexposed_fraction", 0.0)
        overexp_score = max(0.0, 1.0 - overexp / 0.2)
        saturation = metrics.get("saturation", 0.2)
        saturation_score = min(saturation / 0.15, 1.0)

        weighted = (
            blur_score * 0.25
            + brightness_score * 0.15
            + contrast_score * 0.15
            + noise_score * 0.15
            + overexp_score * 0.10
            + saturation_score * 0.10
            + 0.10  # base score
        )

        # Penalty for issues
        reject_penalty = len([i for i in issues if i.severity == "reject"]) * 0.15
        warn_penalty = len([i for i in issues if i.severity == "warn"]) * 0.05

        return max(0.0, min(1.0, weighted - reject_penalty - warn_penalty))

    @staticmethod
    def _build_rejection_message(issues: list[QualityGateIssue]) -> str:
        """Build a user-friendly rejection message from blocking issues."""
        messages = [i.message for i in issues]
        if len(messages) == 1:
            return messages[0]
        return "Multiple quality issues detected: " + "; ".join(messages)

    @staticmethod
    def _build_detailed_feedback(
        issues: list[QualityGateIssue],
        overall_score: float,
        metrics: dict[str, float],
    ) -> str:
        """
        Build comprehensive, actionable feedback for the user.

        Provides specific diagnosis of what went wrong and
        prioritized steps to improve image quality.
        """
        if not issues:
            return "Image quality is excellent. Proceeding with analysis."

        # Categorize issues
        reject_issues = [i for i in issues if i.severity == "reject"]
        warn_issues = [i for i in issues if i.severity == "warn"]

        parts = []

        # Overall assessment
        if overall_score < 0.3:
            parts.append("Image quality is too low for reliable analysis.")
        elif overall_score < 0.5:
            parts.append("Image quality is below optimal. Results may be less reliable.")
        elif warn_issues:
            parts.append("Image is usable but could be improved for better accuracy.")

        # Specific issue breakdowns with metrics
        for issue in reject_issues + warn_issues:
            severity_label = "Critical" if issue.severity == "reject" else "Notice"
            parts.append(f"[{severity_label}] {issue.message}")

            # Add metric context if available
            metric_context = ""
            if issue.metric == "blur":
                metric_context = f"(Sharpness score: {issue.value:.0f}, needed: {issue.threshold:.0f})"
            elif issue.metric == "brightness":
                metric_context = f"(Brightness: {issue.value:.0f}/255, optimal range: 30-230)"
            elif issue.metric == "contrast":
                metric_context = f"(Contrast: {issue.value:.0f}, minimum: {issue.threshold:.0f})"
            elif issue.metric == "noise":
                metric_context = f"(Noise level: {issue.value:.1f}, maximum: {issue.threshold:.1f})"
            elif issue.metric == "overexposure":
                metric_context = f"({issue.value:.0%} of image is overexposed, limit: {issue.threshold:.0%})"
            elif issue.metric == "underexposure":
                metric_context = f"({issue.value:.0%} of image is too dark, limit: {issue.threshold:.0%})"
            elif issue.metric == "resolution":
                metric_context = f"(Minimum dimension: {issue.value:.0f}px, required: {issue.threshold:.0f}px)"
            elif issue.metric == "color_validity":
                metric_context = f"(Saturation: {issue.value:.2f}, minimum: {issue.threshold:.2f})"

            if metric_context:
                parts.append(f"  -> {metric_context}")

        # Build improvement summary
        if reject_issues:
            primary_metrics = list({i.metric for i in reject_issues})
            parts.append(
                f"To fix this: Address the {', '.join(primary_metrics)} issue(s) "
                f"listed above and retake the photo."
            )
        elif warn_issues:
            parts.append(
                "Tips: Follow the suggestions below to improve accuracy."
            )

        return "\n".join(parts)

    @staticmethod
    def _build_improvement_plan(issues: list[QualityGateIssue]) -> list[str]:
        """
        Build a prioritized, step-by-step improvement plan.

        Returns ordered list of specific actions the user should take.
        """
        if not issues:
            return ["Image quality is excellent — no changes needed."]

        # Priority order: reject issues first, then warnings
        sorted_issues = sorted(
            issues,
            key=lambda i: (0 if i.severity == "reject" else 1, -i.value if i.severity == "reject" else i.value),
        )

        plan = []
        seen_metrics = set()

        for issue in sorted_issues:
            if issue.metric in seen_metrics:
                continue
            seen_metrics.add(issue.metric)

            # Get metric-specific detailed steps
            steps = issue.improvement_steps if issue.improvement_steps else [issue.suggestion]

            for step in steps:
                plan.append(step)

        # Add general best practices if multiple issues
        if len(issues) >= 3:
            plan.append(
                "General tip: Use a well-lit room, hold the phone steady, "
                "and ensure the eye fills most of the frame."
            )

        return plan

    @staticmethod
    def _estimate_quality_if_fixed(
        current_score: float,
        issues: list[QualityGateIssue],
    ) -> float:
        """
        Estimate what the quality score would be if all issues were fixed.

        Provides motivation for the user by showing potential improvement.
        """
        if not issues:
            return current_score

        # Estimate improvement per issue type
        improvement_per_issue = {
            "blur": 0.15,
            "brightness": 0.10,
            "contrast": 0.08,
            "noise": 0.10,
            "overexposure": 0.12,
            "underexposure": 0.12,
            "resolution": 0.05,
            "color_validity": 0.08,
        }

        estimated_gain = 0.0
        for issue in issues:
            gain = improvement_per_issue.get(issue.metric, 0.05)
            if issue.severity == "reject":
                estimated_gain += gain
            else:
                estimated_gain += gain * 0.5  # Warnings contribute less

        return min(1.0, current_score + estimated_gain)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience function
# ─────────────────────────────────────────────────────────────────────────────

_default_gate: ImageQualityGate | None = None


def get_quality_gate() -> ImageQualityGate:
    """Get or create the singleton quality gate."""
    global _default_gate
    if _default_gate is None:
        _default_gate = ImageQualityGate()
    return _default_gate


def evaluate_image_quality(image: Image.Image) -> QualityGateResult:
    """Convenience function to evaluate image quality."""
    return get_quality_gate().evaluate(image)
