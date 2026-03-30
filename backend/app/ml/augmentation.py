"""
Conjunctiva-specific data augmentation for AnemiaLens training.

Eye/conjunctiva images have unique challenges:
- Lighting varies wildly (phone flash, sunlight, indoor)
- Shaky hands cause motion blur
- Different phone cameras have color casts
- Eyelashes partially occlude the conjunctiva
- JPEG compression artifacts from phone cameras

These augmentations are TRAINING-TIME ONLY — never apply at inference.

v2 (2026-03) — Physically-grounded lighting augmentations
  - simulate_spectral_cast: proper per-channel gain (replaces crude hue rotation)
  - simulate_flash_overexposure: radial gradient center blowout
  - simulate_underexposure: L*-domain darkening (LAB-space gamma)
  - simulate_lighting_norm_residual: trains on partially-corrected images to
    match the inference normalization path from lighting_norm.py
"""
from __future__ import annotations

import random
from io import BytesIO
from typing import Callable

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


class ConjunctivaAugmenter:
    """
    Eye-specific augmentation pipeline.
    Each method returns a new PIL Image (non-destructive).
    """

    # ------------------------------------------------------------------
    # ── Original augmentations (preserved) ────────────────────────────
    # ------------------------------------------------------------------

    def simulate_lighting_variation(
        self,
        image: Image.Image,
        *,
        gamma_range: tuple[float, float] = (0.6, 1.4),
        brightness_range: tuple[float, float] = (0.70, 1.30),
    ) -> Image.Image:
        """
        Gamma correction + brightness shift (RGB domain).
        Mimics different ambient lighting conditions.
        Most impactful augmentation for conjunctiva pallor detection.
        """
        gamma = random.uniform(*gamma_range)
        lut = [int(255 * (i / 255.0) ** gamma) for i in range(256)]
        lut_table = lut * 3  # R, G, B
        image = image.point(lut_table)

        factor = random.uniform(*brightness_range)
        image = ImageEnhance.Brightness(image).enhance(factor)
        return image

    def simulate_blur(
        self,
        image: Image.Image,
        *,
        sigma_range: tuple[float, float] = (0.5, 2.0),
    ) -> Image.Image:
        """
        Gaussian blur to mimic shaky hands or out-of-focus shots.
        Second most impactful — blurry images are very common in field use.
        """
        sigma = random.uniform(*sigma_range)
        return image.filter(ImageFilter.GaussianBlur(radius=sigma))

    def simulate_partial_occlusion(
        self,
        image: Image.Image,
        *,
        erase_fraction_range: tuple[float, float] = (0.05, 0.15),
        n_patches: int = 2,
    ) -> Image.Image:
        """
        Random rectangular erasing to simulate eyelash occlusion.
        Patches are filled with the image mean color (not black) to avoid
        introducing artificial dark signals.
        """
        arr = np.array(image.convert("RGB"), dtype=np.uint8)
        h, w = arr.shape[:2]
        mean_color = arr.mean(axis=(0, 1)).astype(np.uint8)

        for _ in range(n_patches):
            frac = random.uniform(*erase_fraction_range)
            patch_area = int(h * w * frac)
            patch_h = random.randint(max(1, h // 8), max(2, int(h * 0.4)))
            patch_w = patch_area // max(patch_h, 1)
            patch_w = min(patch_w, w)

            top = random.randint(0, max(0, h - patch_h))
            left = random.randint(0, max(0, w - patch_w))
            arr[top: top + patch_h, left: left + patch_w] = mean_color

        return Image.fromarray(arr)

    def simulate_compression_artifacts(
        self,
        image: Image.Image,
        *,
        quality_range: tuple[int, int] = (60, 85),
    ) -> Image.Image:
        """
        JPEG round-trip to simulate phone camera compression.
        Introduces blocking artifacts common in field-captured images.
        """
        quality = random.randint(*quality_range)
        buf = BytesIO()
        image.save(buf, format="JPEG", quality=quality)
        buf.seek(0)
        return Image.open(buf).copy()

    def simulate_contrast_variation(
        self,
        image: Image.Image,
        *,
        contrast_range: tuple[float, float] = (0.75, 1.35),
    ) -> Image.Image:
        """Contrast variation — helps with over/under-exposed images."""
        factor = random.uniform(*contrast_range)
        return ImageEnhance.Contrast(image).enhance(factor)

    # ------------------------------------------------------------------
    # ── v2 physically-grounded lighting augmentations ─────────────────
    # ------------------------------------------------------------------

    def simulate_spectral_cast(
        self,
        image: Image.Image,
        *,
        cast_type: str = "random",
        cast_strength_range: tuple[float, float] = (0.08, 0.30),
    ) -> Image.Image:
        """
        Physically-grounded spectral (colour-temperature) cast augmentation.

        Replaces the old crude hue-rotation hack in simulate_color_cast.
        Instead of rotating channels, we apply per-channel multiplicative gain
        exactly as a real illuminant change would — matching the inverse of
        what lighting_norm.py's grey-world correction undoes.

        cast_type: 'warm'   — incandescent / golden hour (R↑ B↓)
                   'cool'   — shade / cloudy / fluorescent-blue (B↑ R↓)
                   'green'  — fluorescent-green cast (G↑)
                   'random' — pick randomly from warm/cool/green
        """
        if cast_type == "random":
            cast_type = random.choice(["warm", "cool", "green"])

        strength = random.uniform(*cast_strength_range)
        arr = np.asarray(image.convert("RGB"), dtype=np.float32)

        # Multiplicative per-channel scaling — matches the grey-world model
        scale_r, scale_g, scale_b = 1.0, 1.0, 1.0
        if cast_type == "warm":
            scale_r = 1.0 + strength           # R boost
            scale_b = 1.0 - strength * 0.7     # B cut
        elif cast_type == "cool":
            scale_b = 1.0 + strength           # B boost
            scale_r = 1.0 - strength * 0.6     # R cut
        else:  # green / fluorescent
            scale_g = 1.0 + strength * 0.9
            scale_r = 1.0 - strength * 0.3
            scale_b = 1.0 - strength * 0.3

        arr[:, :, 0] = np.clip(arr[:, :, 0] * scale_r, 0, 255)
        arr[:, :, 1] = np.clip(arr[:, :, 1] * scale_g, 0, 255)
        arr[:, :, 2] = np.clip(arr[:, :, 2] * scale_b, 0, 255)
        return Image.fromarray(arr.astype(np.uint8))

    def simulate_flash_overexposure(
        self,
        image: Image.Image,
        *,
        peak_gain_range: tuple[float, float] = (1.4, 2.2),
        hotspot_radius_range: tuple[float, float] = (0.20, 0.45),
    ) -> Image.Image:
        """
        Radial-gradient centre blowout — the most common real-world artefact
        when users hold the phone too close with flash enabled.

        Applies a Gaussian radial gain mask centred slightly off-centre
        (as occurs with diffuse LED flash) that boosts L* locally, then
        clips highlights naturally.  The perimeter is left unchanged.
        """
        arr = np.asarray(image.convert("RGB"), dtype=np.float32)
        h, w = arr.shape[:2]

        # Random hotspot position (biased toward centre ±20%)
        cx = w * random.uniform(0.35, 0.65)
        cy = h * random.uniform(0.35, 0.65)
        radius = min(h, w) * random.uniform(*hotspot_radius_range)
        peak_gain = random.uniform(*peak_gain_range)

        # Gaussian mask [0, 1]
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        dist_sq = (xs - cx) ** 2 + (ys - cy) ** 2
        mask = np.exp(-dist_sq / (2.0 * radius ** 2))

        # Apply gain radially — blend with 1.0 at fringe
        gain = 1.0 + mask * (peak_gain - 1.0)
        for c in range(3):
            arr[:, :, c] = np.clip(arr[:, :, c] * gain, 0, 255)

        return Image.fromarray(arr.astype(np.uint8))

    def simulate_underexposure(
        self,
        image: Image.Image,
        *,
        gamma_range: tuple[float, float] = (1.5, 2.8),
    ) -> Image.Image:
        """
        LAB-space gamma darkening — accurately simulates underexposure
        (shade, indoor ambient) without hue shift.

        Applies gamma > 1 only to the L* channel (darkness without saturation
        artefacts), unlike the RGB gamma in simulate_lighting_variation.
        """
        arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
        lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)

        gamma = random.uniform(*gamma_range)
        l_norm = lab[:, :, 0].astype(np.float32) / 255.0
        l_dark = np.power(l_norm, gamma) * 255.0
        lab[:, :, 0] = np.clip(l_dark, 0, 255).astype(np.uint8)

        rgb_out = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        return Image.fromarray(rgb_out)

    def simulate_lighting_norm_residual(
        self,
        image: Image.Image,
        *,
        correction_fraction_range: tuple[float, float] = (0.20, 0.80),
    ) -> Image.Image:
        """
        Applies lighting normalization at a **random partial strength** to
        train the model on images that look like they've been partially
        corrected by lighting_norm.normalize_illumination().

        This is critical: at inference, normalize_illumination() is always
        applied but with clahe_strength=1.0.  During training we augment with
        a random strength so the model never over-fits to assuming perfect
        normalization.

        Uses the same CLAHE + grey-world pipeline as production.
        """
        from app.ml.lighting_norm import normalize_illumination  # local import keeps circularity safe

        strength = random.uniform(*correction_fraction_range)
        corrected, _ = normalize_illumination(image, clahe_strength=strength, grey_world_alpha=strength * 0.55)
        return corrected


# ---------------------------------------------------------------------------
# Pipeline Builder
# ---------------------------------------------------------------------------

def build_augmentation_pipeline(
    severity: str = "medium",
) -> Callable[[Image.Image], Image.Image]:
    """
    Returns a callable that applies a random subset of augmentations.

    severity:
      'light'  — safe augmentations only (lighting + blur), low distortion
      'medium' — full pipeline, moderate intensity (recommended for training)
      'heavy'  — aggressive augmentations for stress-testing robustness

    v2 change: simulate_color_cast replaced by simulate_spectral_cast;
    simulate_flash_overexposure, simulate_underexposure, and
    simulate_lighting_norm_residual added to medium and heavy pipelines.
    """
    aug = ConjunctivaAugmenter()

    # (function, probability, kwargs)
    if severity == "light":
        pipeline = [
            (aug.simulate_lighting_variation, 0.7, {"gamma_range": (0.80, 1.20), "brightness_range": (0.85, 1.15)}),
            (aug.simulate_blur, 0.4, {"sigma_range": (0.3, 1.2)}),
            (aug.simulate_compression_artifacts, 0.3, {"quality_range": (75, 90)}),
            (aug.simulate_spectral_cast, 0.3, {"cast_strength_range": (0.05, 0.15)}),
        ]
    elif severity == "heavy":
        pipeline = [
            (aug.simulate_lighting_variation, 0.8, {"gamma_range": (0.5, 1.6), "brightness_range": (0.60, 1.45)}),
            (aug.simulate_blur, 0.6, {"sigma_range": (0.5, 3.0)}),
            (aug.simulate_spectral_cast, 0.7, {"cast_strength_range": (0.15, 0.40)}),
            (aug.simulate_flash_overexposure, 0.5, {"peak_gain_range": (1.5, 2.5), "hotspot_radius_range": (0.18, 0.50)}),
            (aug.simulate_underexposure, 0.5, {"gamma_range": (1.6, 3.2)}),
            (aug.simulate_partial_occlusion, 0.5, {"erase_fraction_range": (0.08, 0.20), "n_patches": 3}),
            (aug.simulate_compression_artifacts, 0.5, {"quality_range": (50, 80)}),
            (aug.simulate_contrast_variation, 0.6, {"contrast_range": (0.65, 1.50)}),
            (aug.simulate_lighting_norm_residual, 0.4, {"correction_fraction_range": (0.15, 0.85)}),
        ]
    else:  # medium (default)
        pipeline = [
            (aug.simulate_lighting_variation, 0.75, {"gamma_range": (0.65, 1.40), "brightness_range": (0.75, 1.30)}),
            (aug.simulate_blur, 0.5, {"sigma_range": (0.5, 2.0)}),
            (aug.simulate_spectral_cast, 0.55, {"cast_strength_range": (0.08, 0.28)}),
            (aug.simulate_flash_overexposure, 0.30, {"peak_gain_range": (1.4, 2.0), "hotspot_radius_range": (0.22, 0.44)}),
            (aug.simulate_underexposure, 0.30, {"gamma_range": (1.5, 2.6)}),
            (aug.simulate_partial_occlusion, 0.35, {"erase_fraction_range": (0.05, 0.15), "n_patches": 2}),
            (aug.simulate_compression_artifacts, 0.4, {"quality_range": (60, 85)}),
            (aug.simulate_contrast_variation, 0.4, {"contrast_range": (0.75, 1.35)}),
            (aug.simulate_lighting_norm_residual, 0.25, {"correction_fraction_range": (0.20, 0.80)}),
        ]

    def apply(image: Image.Image) -> Image.Image:
        result = image.convert("RGB")
        for fn, prob, kwargs in pipeline:
            if random.random() < prob:
                result = fn(result, **kwargs)
        return result

    return apply


# ---------------------------------------------------------------------------
# Impact Notes (for documentation)
# ---------------------------------------------------------------------------
AUGMENTATION_IMPACT_NOTES = """
Augmentation impact ranking for conjunctiva pallor detection (v2):

1. simulate_lighting_variation   — HIGH IMPACT
   Lighting is the #1 source of variance in field images.
   Gamma + brightness shifts directly affect R/G/B ratios used for pallor.

2. simulate_blur                 — HIGH IMPACT
   Shaky hands are extremely common. Blur degrades ROI extraction quality.
   Training on blurry images improves robustness to poor captures.

3. simulate_spectral_cast        — HIGH IMPACT (replaces simulate_color_cast v1)
   Proper per-channel multiplicative gain matches the grey-world model used
   at inference. Warm/cool/green cast types cover all real-world illuminants.
   Much more realistic than the old hue-rotation approximation.

4. simulate_flash_overexposure   — HIGH IMPACT (new in v2)
   Radial gradient blowout is the most common field artefact (phone flash).
   Directly exercises the highlight_fraction and clahe_gain feature paths.

5. simulate_underexposure        — MEDIUM-HIGH IMPACT (new in v2)
   LAB-space darkening (L*-only gamma) accurately simulates shade/indoor
   conditions without hue shift. Exercises illumination_mean and clahe_gain.

6. simulate_lighting_norm_residual — MEDIUM IMPACT (new in v2)
   Trains the model on partially-corrected images to avoid over-fitting to
   the assumption of perfect normalize_illumination() output at inference.
   Prevents brittleness when CLAHE over- or under-corrects.

7. simulate_compression_artifacts — MEDIUM IMPACT
   JPEG artifacts are universal in phone photos. Low-quality compression
   can introduce false texture signals.

8. simulate_partial_occlusion    — MEDIUM IMPACT
   Eyelashes frequently occlude the conjunctiva. Random erasing forces
   the model to use the visible region rather than memorising full patterns.

9. simulate_contrast_variation   — LOW-MEDIUM IMPACT
   Helps with over/under-exposed images but partially covered by lighting.
"""
