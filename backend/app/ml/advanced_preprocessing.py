"""
advanced_preprocessing.py — Enhanced image preprocessing pipeline for AnemiaLens.

Provides a comprehensive preprocessing chain that runs before feature extraction
to maximize conjunctiva visibility and prediction accuracy.

Pipeline Stages
---------------
1. Noise reduction for low-light / high-ISO images (enhanced with wavelet denoising)
2. Automatic rotation correction based on eye orientation (improved Hough-based detection)
3. Advanced histogram equalization (CLAHE) for conjunctiva visibility (adaptive multi-scale)
4. Adaptive gamma correction for exposure normalization
5. Color cast correction for spectral bias
6. Vignette correction for flash fall-off
7. Low-light enhancement for underexposed images

All stages are individually toggleable and parameterized for tuning.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Literal

import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageOps, ImageStat

log = logging.getLogger("anemialens.preprocessing")

RotationAngle = Literal[0, 90, 180, 270]


@dataclass
class PreprocessingConfig:
    """Configuration for the advanced preprocessing pipeline."""
    # Noise reduction
    denoise_enabled: bool = True
    denoise_strength: float = 0.5        # 0.0 (none) to 1.0 (maximum)
    denoise_luma: int = 10               # Luminance denoise strength
    denoise_chroma: int = 10             # Chrominance denoise strength
    wavelet_denoise_enabled: bool = True  # Enhanced wavelet-like denoising
    wavelet_denoise_strength: float = 0.3

    # Rotation correction
    rotation_correction_enabled: bool = True
    rotation_auto_detect: bool = True     # Auto-detect eye orientation
    rotation_use_hough: bool = True       # Use Hough line detection for improved accuracy

    # CLAHE / histogram equalization
    clahe_enabled: bool = True
    clahe_clip_limit: float = 3.0        # 1.0 (subtle) to 8.0 (strong)
    clahe_tile_size: int = 8             # Tile grid size (N x N)
    clahe_multi_scale: bool = True       # Apply CLAHE at multiple scales and blend

    # Gamma correction
    gamma_correction_enabled: bool = True
    gamma_auto: bool = True               # Auto-compute gamma from image stats
    gamma_value: float = 1.0             # Manual gamma (used when gamma_auto=False)

    # Color cast correction
    color_cast_correction: bool = True
    grey_world_alpha: float = 0.55       # Blend toward grey world (0=off, 1=full)

    # Vignette correction
    vignette_correction: bool = False    # Flash fall-off correction
    vignette_strength: float = 0.3

    # Low-light enhancement
    lowlight_enhancement: bool = True
    lowlight_threshold: float = 0.30     # Mean luminance below which enhancement triggers
    lowlight_gain: float = 1.5           # Maximum brightness boost factor

    # Output
    output_size: tuple[int, int] | None = None  # Resize after preprocessing


@dataclass
class PreprocessingReport:
    """Diagnostic report from the preprocessing pipeline."""
    stages_applied: list[str] = field(default_factory=list)
    rotation_detected: RotationAngle = 0
    rotation_applied: int = 0
    gamma_computed: float = 1.0
    noise_level_before: float = 0.0
    noise_level_after: float = 0.0
    clahe_gain: float = 0.0
    brightness_before: float = 0.0
    brightness_after: float = 0.0
    contrast_before: float = 0.0
    contrast_after: float = 0.0
    processing_time_ms: float = 0.0
    # New diagnostic fields
    lowlight_boost_applied: bool = False
    lowlight_boost_factor: float = 0.0
    wavelet_denoise_gain: float = 0.0
    clahe_scales_applied: int = 1
    hough_lines_detected: int = 0


class AdvancedPreprocessor:
    """
    Advanced image preprocessor optimized for conjunctival photography.

    Usage
    -----
    preprocessor = AdvancedPreprocessor()
    result_image, report = preprocessor.process(pil_image)
    """

    def __init__(self, config: PreprocessingConfig | None = None) -> None:
        self.config = config or PreprocessingConfig()
        self._last_hough_count: int = 0

    def process(
        self,
        image: Image.Image,
        config: PreprocessingConfig | None = None,
    ) -> tuple[Image.Image, PreprocessingReport]:
        """
        Run the full preprocessing pipeline.

        Parameters
        ----------
        image : PIL.Image — RGB input
        config : Optional override configuration

        Returns
        -------
        (processed_image, report)
        """
        import time
        start = time.perf_counter()

        cfg = config or self.config
        report = PreprocessingReport()

        # Ensure RGB
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Record baseline metrics
        gray = image.convert("L")
        gray_arr = np.asarray(gray, dtype=np.float64)
        report.brightness_before = float(gray_arr.mean()) / 255.0
        report.contrast_before = float(gray_arr.std()) / 255.0
        report.noise_level_before = self._estimate_noise(image)

        working = image

        # ── Stage 1: Noise reduction ────────────────────────────────────────
        if cfg.denoise_enabled:
            working, applied = self._denoise(working, cfg.denoise_strength)
            if applied:
                report.stages_applied.append("denoise")

        # ── Stage 1b: Wavelet-like denoising for low-light ──────────────────
        if cfg.wavelet_denoise_enabled and cfg.wavelet_denoise_strength > 0:
            working, wavelet_gain = self._wavelet_denoise(working, cfg.wavelet_denoise_strength)
            report.wavelet_denoise_gain = wavelet_gain
            if wavelet_gain > 0.01:
                report.stages_applied.append("wavelet_denoise")

        # ── Stage 2: Rotation correction ────────────────────────────────────
        if cfg.rotation_correction_enabled and cfg.rotation_auto_detect:
            working, angle = self._correct_rotation(working, use_hough=cfg.rotation_use_hough)
            report.rotation_detected = angle
            report.hough_lines_detected = self._last_hough_count
            if angle != 0:
                report.rotation_applied = angle
                report.stages_applied.append(f"rotation_{angle}")

        # ── Stage 3: CLAHE histogram equalization ───────────────────────────
        if cfg.clahe_enabled:
            if cfg.clahe_multi_scale:
                working, clahe_gain, scales = self._apply_clahe_multi_scale(
                    working,
                    clip_limit=cfg.clahe_clip_limit,
                    tile_size=cfg.clahe_tile_size,
                )
                report.clahe_gain = clahe_gain
                report.clahe_scales_applied = scales
            else:
                working, clahe_gain = self._apply_clahe(
                    working,
                    clip_limit=cfg.clahe_clip_limit,
                    tile_size=cfg.clahe_tile_size,
                )
                report.clahe_gain = clahe_gain
            report.stages_applied.append("clahe")

        # ── Stage 3b: Low-light enhancement ─────────────────────────────────
        if cfg.lowlight_enhancement:
            working, boost_factor = self._enhance_lowlight(
                working,
                threshold=cfg.lowlight_threshold,
                max_gain=cfg.lowlight_gain,
            )
            if boost_factor > 1.05:
                report.lowlight_boost_applied = True
                report.lowlight_boost_factor = round(boost_factor, 3)
                report.stages_applied.append(f"lowlight_boost_{boost_factor:.2f}x")

        # ── Stage 4: Gamma correction ───────────────────────────────────────
        if cfg.gamma_correction_enabled:
            if cfg.gamma_auto:
                gamma = self._compute_auto_gamma(working)
            else:
                gamma = cfg.gamma_value
            report.gamma_computed = gamma
            if abs(gamma - 1.0) > 0.01:
                working = self._apply_gamma(working, gamma)
                report.stages_applied.append(f"gamma_{gamma:.2f}")

        # ── Stage 5: Color cast correction ──────────────────────────────────
        if cfg.color_cast_correction:
            working = self._correct_color_cast(working, alpha=cfg.grey_world_alpha)
            report.stages_applied.append("color_cast_correction")

        # ── Stage 6: Vignette correction ────────────────────────────────────
        if cfg.vignette_correction and cfg.vignette_strength > 0:
            working = self._correct_vignette(working, cfg.vignette_strength)
            report.stages_applied.append("vignette_correction")

        # ── Optional resize ─────────────────────────────────────────────────
        if cfg.output_size is not None:
            working = working.resize(cfg.output_size, Image.LANCZOS)

        # Record post-processing metrics
        gray_after = np.asarray(working.convert("L"), dtype=np.float64)
        report.brightness_after = float(gray_after.mean()) / 255.0
        report.contrast_after = float(gray_after.std()) / 255.0
        report.noise_level_after = self._estimate_noise(working)

        elapsed_ms = (time.perf_counter() - start) * 1000
        report.processing_time_ms = round(elapsed_ms, 2)

        return working, report

    # ──────────────────────────────────────────────────────────────────────
    # Stage 1: Noise Reduction
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _denoise(
        image: Image.Image,
        strength: float,
    ) -> tuple[Image.Image, bool]:
        """
        Apply noise reduction using non-local means denoising.

        Uses OpenCV's fastNlMeansDenoisingColored for color images.
        Strength controls the filter parameters.
        """
        rgb = np.asarray(image, dtype=np.uint8)

        # Scale parameters by strength
        h_luma = int(5 + strength * 15)    # 5 to 20
        h_chroma = int(3 + strength * 12)  # 3 to 15
        template_window = 5
        search_window = 15

        try:
            denoised = cv2.fastNlMeansDenoisingColored(
                rgb,
                None,
                h_luma,
                h_chroma,
                template_window,
                search_window,
            )
            return Image.fromarray(denoised, mode="RGB"), True
        except Exception as e:
            log.warning("Denoising failed: %s", e)
            return image, False

    @staticmethod
    def _wavelet_denoise(
        image: Image.Image,
        strength: float,
    ) -> tuple[Image.Image, float]:
        """
        Apply wavelet-like denoising using multi-scale Gaussian pyramid.

        This approximates wavelet denoising by:
        1. Building a Gaussian pyramid (multiple scales)
        2. Computing detail layers at each scale
        3. Thresholding detail layers (soft thresholding)
        4. Reconstructing from thresholded details

        Particularly effective for low-light images with high ISO noise.
        """
        try:
            rgb = np.asarray(image, dtype=np.float32)
            threshold = strength * 15.0  # Soft threshold strength

            # Build Gaussian pyramid (3 levels)
            levels = []
            current = rgb.copy()
            for _ in range(3):
                levels.append(current)
                current = cv2.pyrDown(current)

            # Compute detail layers and threshold
            detail = levels[0] - cv2.pyrUp(levels[1])
            detail = cv2.softShrink(detail, threshold)

            # Add second-level detail
            detail2 = levels[1] - cv2.pyrUp(levels[2])
            detail2 = cv2.softShrink(detail2, threshold * 0.7)
            detail2_up = cv2.pyrUp(detail2)

            # Reconstruct: base + thresholded details
            base = levels[2]
            for _ in range(2):
                base = cv2.pyrUp(base)

            # Resize base to match original
            base = cv2.resize(base, (rgb.shape[1], rgb.shape[0]))

            reconstructed = np.clip(base + detail + detail2_up, 0, 255).astype(np.uint8)
            noise_before = float(np.std(rgb - cv2.GaussianBlur(rgb, (5, 5), 0)))
            noise_after = float(np.std(reconstructed.astype(np.float32) - cv2.GaussianBlur(reconstructed.astype(np.float32), (5, 5), 0)))
            gain = max(0.0, (noise_before - noise_after) / max(noise_before, 1.0))

            return Image.fromarray(reconstructed, mode="RGB"), round(gain, 3)
        except Exception as e:
            log.warning("Wavelet denoising failed: %s", e)
            return image, 0.0

    # ──────────────────────────────────────────────────────────────────────
    # Stage 2: Rotation Correction (Enhanced with Hough lines)
    # ──────────────────────────────────────────────────────────────────────

    def _correct_rotation(
        self,
        image: Image.Image,
        use_hough: bool = True,
    ) -> tuple[Image.Image, RotationAngle]:
        """
        Detect and correct image rotation based on eye orientation.

        Uses a combination of:
        1. Gradient structure analysis (original method)
        2. Hough line detection for palpebral fissure orientation (enhanced)

        The palpebral fissure should be approximately horizontal.
        """
        gray = np.asarray(image.convert("L"), dtype=np.float64)
        h, w = gray.shape
        aspect = w / max(h, 1)

        angle: RotationAngle = 0
        self._last_hough_count = 0

        if use_hough:
            angle = self._detect_rotation_hough(gray, w, h, aspect)

        # Fallback to gradient method if Hough found no lines
        if angle == 0 and not use_hough:
            angle = self._detect_rotation_gradient(gray, w, h, aspect)

        if angle != 0:
            image = image.rotate(-angle, expand=True, fillcolor=(0, 0, 0))

        return image, angle

    @staticmethod
    def _detect_rotation_hough(
        gray: np.ndarray,
        width: int,
        height: int,
        aspect: float,
    ) -> RotationAngle:
        """Detect rotation using Hough line detection."""
        # Apply Canny edge detection
        gray_uint8 = np.clip(gray, 0, 255).astype(np.uint8)
        edges = cv2.Canny(gray_uint8, 50, 150, apertureSize=3)

        # Detect lines using probabilistic Hough transform
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=30,
            minLineLength=min(width, height) * 0.2,
            maxLineGap=10,
        )

        if lines is None or len(lines) < 3:
            return 0

        # Compute dominant orientation from detected lines
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            dx = x2 - x1
            dy = y2 - y1
            if abs(dx) > 2:  # Avoid near-vertical lines
                line_angle = np.arctan2(dy, dx) * 180.0 / np.pi
                # Normalize to [-90, 90]
                if line_angle > 90:
                    line_angle -= 180
                elif line_angle < -90:
                    line_angle += 180
                angles.append(line_angle)

        if not angles:
            return 0

        # Use median angle for robustness
        median_angle = float(np.median(angles))

        # Determine if rotation is needed
        # Horizontal lines should have angle ~0
        # If dominant lines are near vertical (~90 or -90), rotate 90 degrees
        abs_angle = abs(median_angle)

        if abs_angle > 60:
            # Dominant lines are near-vertical, need 90-degree rotation
            return 90 if median_angle > 0 else 270
        elif abs_angle > 30 and aspect < 1.0:
            # Moderately angled lines with portrait aspect
            return 90 if median_angle > 0 else 270
        elif aspect < 0.7:
            # Very portrait - likely needs rotation regardless
            return 90

        return 0

    @staticmethod
    def _detect_rotation_gradient(
        gray: np.ndarray,
        width: int,
        height: int,
        aspect: float,
    ) -> RotationAngle:
        """Fallback gradient-based rotation detection."""
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

        grad_x_mag = float(np.sum(np.abs(sobel_x)))
        grad_y_mag = float(np.sum(np.abs(sobel_y)))

        angle: RotationAngle = 0

        if aspect < 0.7:
            if grad_x_mag > grad_y_mag:
                angle = 90
            else:
                angle = 270
        elif aspect < 1.0 and grad_x_mag > grad_y_mag * 1.5:
            angle = 90

        return angle

    # ──────────────────────────────────────────────────────────────────────
    # Stage 3: CLAHE
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _apply_clahe(
        image: Image.Image,
        clip_limit: float = 3.0,
        tile_size: int = 8,
    ) -> tuple[Image.Image, float]:
        """
        Apply Contrast Limited Adaptive Histogram Equalization.

        Works in LAB color space, applying CLAHE only to the L channel
        to preserve color relationships while enhancing local contrast.
        """
        rgb = np.asarray(image, dtype=np.uint8)
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        l_channel = lab[:, :, 0]

        # Record pre-CLAHE mean for gain computation
        l_before = float(l_channel.mean())

        clahe = cv2.createCLAHE(
            clipLimit=clip_limit,
            tileGridSize=(tile_size, tile_size),
        )
        l_corrected = clahe.apply(l_channel)

        # Alpha-blend to avoid over-correction
        blend_factor = 0.65
        lab[:, :, 0] = cv2.addWeighted(
            l_channel, 1.0 - blend_factor,
            l_corrected, blend_factor,
            0,
        )

        result_rgb = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        l_after = float(lab[:, :, 0].mean())
        clahe_gain = abs(l_after - l_before) / 255.0

        return Image.fromarray(result_rgb, mode="RGB"), clahe_gain

    @staticmethod
    def _apply_clahe_multi_scale(
        image: Image.Image,
        clip_limit: float = 3.0,
        tile_size: int = 8,
    ) -> tuple[Image.Image, float, int]:
        """
        Apply CLAHE at multiple scales and blend results.

        Uses fine (small tile), medium, and coarse (large tile) CLAHE
        to capture contrast enhancement at different spatial frequencies.
        This is particularly effective for conjunctival tissue which has
        both fine capillary patterns and larger color gradients.

        Returns (enhanced_image, overall_gain, scales_applied).
        """
        rgb = np.asarray(image, dtype=np.uint8)
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        l_original = lab[:, :, 0].copy()

        # Define scales: fine, medium, coarse
        scales = [
            (max(2, tile_size // 2), clip_limit * 1.5),   # Fine: smaller tiles, stronger
            (tile_size, clip_limit),                         # Medium: original params
            (tile_size * 2, clip_limit * 0.6),              # Coarse: larger tiles, subtler
        ]

        l_enhanced = np.zeros_like(l_original, dtype=np.float64)
        weights = [0.35, 0.40, 0.25]  # Medium scale gets most weight
        scales_applied = 0

        for (ts, cl), weight in zip(scales, weights):
            try:
                clahe = cv2.createCLAHE(
                    clipLimit=cl,
                    tileGridSize=(ts, ts),
                )
                l_corrected = clahe.apply(l_original)
                l_enhanced += l_corrected.astype(np.float64) * weight
                scales_applied += 1
            except Exception as e:
                log.warning("CLAHE scale %d failed: %s", ts, e)

        if scales_applied == 0:
            return image, 0.0, 0

        # Blend with original to avoid over-enhancement
        blend_factor = 0.60
        l_final = np.clip(
            l_original * (1.0 - blend_factor) + l_enhanced * blend_factor,
            0, 255
        ).astype(np.uint8)

        lab[:, :, 0] = l_final
        result_rgb = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

        gain = abs(float(l_final.mean()) - float(l_original.mean())) / 255.0
        return Image.fromarray(result_rgb, mode="RGB"), round(gain, 4), scales_applied

    def _enhance_lowlight(
        self,
        image: Image.Image,
        threshold: float = 0.30,
        max_gain: float = 1.5,
    ) -> tuple[Image.Image, float]:
        """
        Enhance underexposed images using adaptive brightness boost.

        Only applies when mean luminance is below the threshold.
        Uses a combination of:
        1. Gamma-based brightness boost
        2. Shadow-specific detail enhancement
        3. Noise-aware amplification (less boost on noisy images)

        Parameters
        ----------
        image : PIL Image
        threshold : Mean luminance threshold to trigger enhancement
        max_gain : Maximum brightness multiplier

        Returns
        -------
        (enhanced_image, boost_factor)
        """
        gray = np.asarray(image.convert("L"), dtype=np.float64) / 255.0
        mean_luminance = float(gray.mean())

        if mean_luminance >= threshold:
            return image, 1.0

        # Compute adaptive gain based on how dark the image is
        # Darker images get more boost, but capped at max_gain
        deficit = threshold - mean_luminance
        gain = 1.0 + deficit * (max_gain - 1.0) / threshold
        gain = min(gain, max_gain)

        # Estimate noise to avoid amplifying noise in dark regions
        noise_level = self._estimate_noise(image)
        noise_penalty = max(0.5, 1.0 - noise_level / 50.0)  # Reduce gain for noisy images
        gain *= noise_penalty

        if gain <= 1.05:
            return image, 1.0

        # Apply gain using gamma correction (preserves relative contrast)
        # Effective gamma = 1/gain (gain > 1 means gamma < 1, which brightens)
        effective_gamma = 1.0 / gain
        effective_gamma = max(0.3, min(effective_gamma, 1.0))

        # Build LUT for gamma correction
        inv_gamma = 1.0 / effective_gamma
        lut = np.array([
            int(255 * ((i / 255.0) ** (1.0 / inv_gamma)))
            for i in range(256)
        ], dtype=np.uint8)

        rgb = np.asarray(image, dtype=np.uint8)
        brightened = cv2.LUT(rgb, lut)

        # Also boost shadows specifically using histogram manipulation
        hsv = cv2.cvtColor(brightened, cv2.COLOR_RGB2HSV)
        v_channel = hsv[:, :, 2].astype(np.float64)

        # Selective shadow boost: only brighten dark pixels
        shadow_mask = v_channel < 128
        shadow_boost = (128 - v_channel[shadow_mask]) * 0.3 * (gain - 1.0)
        v_channel[shadow_mask] = np.clip(
            v_channel[shadow_mask] + shadow_boost, 0, 255
        )
        hsv[:, :, 2] = np.clip(v_channel, 0, 255).astype(np.uint8)

        result_rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        return Image.fromarray(result_rgb, mode="RGB"), round(gain, 3)

    # ──────────────────────────────────────────────────────────────────────
    # Stage 4: Gamma Correction
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_auto_gamma(image: Image.Image) -> float:
        """
        Compute optimal gamma value from image statistics.

        Target: make the mean luminance approximately 0.45 (standard
        photographic exposure target). Gamma > 1 darkens, < 1 brightens.
        """
        gray = np.asarray(image.convert("L"), dtype=np.float64) / 255.0
        mean_l = float(gray.mean())

        if mean_l < 1e-6:
            return 1.0

        # Solve: mean_l^gamma = 0.45  →  gamma = log(0.45) / log(mean_l)
        target = 0.45
        gamma = math.log(target) / math.log(mean_l)

        # Clamp to reasonable range
        return float(np.clip(gamma, 0.3, 3.0))

    @staticmethod
    def _apply_gamma(image: Image.Image, gamma: float) -> Image.Image:
        """Apply gamma correction using a lookup table for speed."""
        if abs(gamma - 1.0) < 0.01:
            return image

        # Build LUT: out = 255 * (in/255)^(1/gamma)
        inv_gamma = 1.0 / gamma
        lut = np.array([
            int(255 * ((i / 255.0) ** inv_gamma))
            for i in range(256)
        ], dtype=np.uint8)

        rgb = np.asarray(image, dtype=np.uint8)
        corrected = cv2.LUT(rgb, lut)
        return Image.fromarray(corrected, mode="RGB")

    # ──────────────────────────────────────────────────────────────────────
    # Stage 5: Color Cast Correction
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _correct_color_cast(
        image: Image.Image,
        alpha: float = 0.55,
    ) -> Image.Image:
        """
        Partial grey-world white balance to reduce spectral bias.

        The grey-world assumption: average scene color should be grey.
        We apply partial correction to avoid destroying clinical color signals.
        """
        rgb = np.asarray(image, dtype=np.float32)
        mean_r = float(rgb[:, :, 0].mean()) + 1e-6
        mean_g = float(rgb[:, :, 1].mean()) + 1e-6
        mean_b = float(rgb[:, :, 2].mean()) + 1e-6
        mean_all = (mean_r + mean_g + mean_b) / 3.0

        scale_r = 1.0 + alpha * (mean_all / mean_r - 1.0)
        scale_g = 1.0 + alpha * (mean_all / mean_g - 1.0)
        scale_b = 1.0 + alpha * (mean_all / mean_b - 1.0)

        corrected = rgb.copy()
        corrected[:, :, 0] = np.clip(corrected[:, :, 0] * scale_r, 0, 255)
        corrected[:, :, 1] = np.clip(corrected[:, :, 1] * scale_g, 0, 255)
        corrected[:, :, 2] = np.clip(corrected[:, :, 2] * scale_b, 0, 255)

        return Image.fromarray(corrected.astype(np.uint8), mode="RGB")

    # ──────────────────────────────────────────────────────────────────────
    # Stage 6: Vignette Correction
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _correct_vignette(
        image: Image.Image,
        strength: float = 0.3,
    ) -> Image.Image:
        """
        Correct flash fall-off (vignette) brightening the edges.

        Creates a radial gain map and applies it to compensate for
        the typical circular flash falloff pattern.
        """
        rgb = np.asarray(image, dtype=np.float32)
        h, w = rgb.shape[:2]

        # Create radial distance map from center
        center_x, center_y = w / 2, h / 2
        max_dist = math.sqrt(center_x ** 2 + center_y ** 2)
        y_coords, x_coords = np.ogrid[:h, :w]
        dist = np.sqrt((x_coords - center_x) ** 2 + (y_coords - center_y) ** 2) / max_dist

        # Gain map: brighter at edges
        gain = 1.0 + strength * (dist ** 2)
        gain = np.clip(gain, 0.0, 2.0)

        corrected = np.clip(rgb * gain[:, :, np.newaxis], 0, 255).astype(np.uint8)
        return Image.fromarray(corrected, mode="RGB")

    # ──────────────────────────────────────────────────────────────────────
    # Utility helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _estimate_noise(image: Image.Image) -> float:
        """Estimate noise level via local variance."""
        gray = np.asarray(image.convert("L").resize((64, 64)), dtype=np.float64)
        # Local variance using a 3x3 window
        kernel = np.ones((3, 3), np.float64) / 9.0
        local_mean = cv2.filter2D(gray, -1, kernel)
        local_var = cv2.filter2D(gray ** 2, -1, kernel) - local_mean ** 2
        return float(np.sqrt(np.maximum(local_var, 0)).mean())


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience functions
# ─────────────────────────────────────────────────────────────────────────────

_default_preprocessor: AdvancedPreprocessor | None = None


def get_preprocessor(config: PreprocessingConfig | None = None) -> AdvancedPreprocessor:
    """Get or create the singleton preprocessor."""
    global _default_preprocessor
    if _default_preprocessor is None:
        _default_preprocessor = AdvancedPreprocessor(config)
    return _default_preprocessor


def preprocess_image(
    image: Image.Image,
    config: PreprocessingConfig | None = None,
) -> tuple[Image.Image, PreprocessingReport]:
    """Convenience function to preprocess an image."""
    return get_preprocessor(config).process(image)
