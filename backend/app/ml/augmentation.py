"""
Conjunctiva-specific data augmentation for AnemiaLens training.

Eye/conjunctiva images have unique challenges:
- Lighting varies wildly (phone flash, sunlight, indoor)
- Shaky hands cause motion blur
- Different phone cameras have color casts
- Eyelashes partially occlude the conjunctiva
- JPEG compression artifacts from phone cameras

These augmentations are TRAINING-TIME ONLY — never apply at inference.
"""
from __future__ import annotations

import random
from io import BytesIO
from typing import Callable

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


class ConjunctivaAugmenter:
    """
    Eye-specific augmentation pipeline.
    Each method returns a new PIL Image (non-destructive).
    """

    def simulate_lighting_variation(
        self,
        image: Image.Image,
        *,
        gamma_range: tuple[float, float] = (0.6, 1.4),
        brightness_range: tuple[float, float] = (0.70, 1.30),
    ) -> Image.Image:
        """
        Gamma correction + brightness shift.
        Mimics different ambient lighting conditions.
        Most impactful augmentation for conjunctiva pallor detection.
        """
        # Gamma correction
        gamma = random.uniform(*gamma_range)
        lut = [int(255 * (i / 255.0) ** gamma) for i in range(256)]
        lut_table = lut * 3  # R, G, B
        image = image.point(lut_table)

        # Brightness
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

    def simulate_color_cast(
        self,
        image: Image.Image,
        *,
        hue_shift_range: tuple[int, int] = (-10, 10),
        saturation_range: tuple[float, float] = (0.80, 1.20),
    ) -> Image.Image:
        """
        Slight hue shift + saturation change.
        Mimics different phone camera white balance settings.
        Important for pallor detection since we rely on R/G ratios.
        """
        arr = np.array(image.convert("RGB"), dtype=np.float32)

        # Simple hue shift via channel rotation
        hue_shift = random.uniform(*hue_shift_range) / 360.0
        if abs(hue_shift) > 0.001:
            # Approximate hue shift by rotating R/G/B channels slightly
            r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
            shift = hue_shift * 30  # scale to pixel range
            arr[:, :, 0] = np.clip(r + shift, 0, 255)
            arr[:, :, 1] = np.clip(g - shift * 0.5, 0, 255)
            arr[:, :, 2] = np.clip(b - shift * 0.5, 0, 255)

        result = Image.fromarray(arr.astype(np.uint8))

        # Saturation
        factor = random.uniform(*saturation_range)
        result = ImageEnhance.Color(result).enhance(factor)
        return result

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


# ---------------------------------------------------------------------------
# Pipeline Builder
# ---------------------------------------------------------------------------

def build_augmentation_pipeline(
    severity: str = "medium",
) -> Callable[[Image.Image], Image.Image]:
    """
    Returns a callable that applies a random subset of augmentations.

    severity:
      'light'  — safe augmentations only (lighting + blur)
      'medium' — all augmentations, moderate intensity (recommended)
      'heavy'  — aggressive augmentations for robustness stress-testing
    """
    aug = ConjunctivaAugmenter()

    # (function, probability, kwargs)
    if severity == "light":
        pipeline = [
            (aug.simulate_lighting_variation, 0.7, {"gamma_range": (0.75, 1.25), "brightness_range": (0.80, 1.20)}),
            (aug.simulate_blur, 0.4, {"sigma_range": (0.3, 1.2)}),
            (aug.simulate_compression_artifacts, 0.3, {"quality_range": (75, 90)}),
        ]
    elif severity == "heavy":
        pipeline = [
            (aug.simulate_lighting_variation, 0.9, {"gamma_range": (0.5, 1.6), "brightness_range": (0.60, 1.45)}),
            (aug.simulate_blur, 0.6, {"sigma_range": (0.5, 3.0)}),
            (aug.simulate_color_cast, 0.7, {"hue_shift_range": (-15, 15), "saturation_range": (0.70, 1.35)}),
            (aug.simulate_partial_occlusion, 0.5, {"erase_fraction_range": (0.08, 0.20), "n_patches": 3}),
            (aug.simulate_compression_artifacts, 0.5, {"quality_range": (50, 80)}),
            (aug.simulate_contrast_variation, 0.6, {"contrast_range": (0.65, 1.50)}),
        ]
    else:  # medium (default)
        pipeline = [
            (aug.simulate_lighting_variation, 0.8, {"gamma_range": (0.6, 1.4), "brightness_range": (0.70, 1.30)}),
            (aug.simulate_blur, 0.5, {"sigma_range": (0.5, 2.0)}),
            (aug.simulate_color_cast, 0.5, {"hue_shift_range": (-10, 10), "saturation_range": (0.80, 1.20)}),
            (aug.simulate_partial_occlusion, 0.35, {"erase_fraction_range": (0.05, 0.15), "n_patches": 2}),
            (aug.simulate_compression_artifacts, 0.4, {"quality_range": (60, 85)}),
            (aug.simulate_contrast_variation, 0.4, {"contrast_range": (0.75, 1.35)}),
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
Augmentation impact ranking for conjunctiva pallor detection:

1. simulate_lighting_variation  — HIGH IMPACT
   Lighting is the #1 source of variance in field images.
   Gamma + brightness shifts directly affect R/G/B ratios used for pallor.

2. simulate_blur                — HIGH IMPACT
   Shaky hands are extremely common. Blur degrades ROI extraction quality.
   Training on blurry images improves robustness to poor captures.

3. simulate_color_cast          — MEDIUM IMPACT
   Different phones have different white balance. Hue shifts test whether
   the model relies on absolute color vs. relative channel ratios.

4. simulate_compression_artifacts — MEDIUM IMPACT
   JPEG artifacts are universal in phone photos. Low-quality compression
   can introduce false texture signals.

5. simulate_partial_occlusion   — MEDIUM IMPACT
   Eyelashes frequently occlude the conjunctiva. Random erasing forces
   the model to use the visible region rather than memorising full patterns.

6. simulate_contrast_variation  — LOW-MEDIUM IMPACT
   Helps with over/under-exposed images but partially covered by lighting.
"""
