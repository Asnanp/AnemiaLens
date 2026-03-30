from __future__ import annotations

from io import BytesIO
from pathlib import Path
from statistics import mean

from PIL import Image, ImageFilter, ImageOps, ImageStat
from app.ml.lighting_norm import compute_illumination_bias, normalize_illumination
from app.schemas import QualityAssessment


FEATURE_NAMES = [
    "mean_r",
    "mean_g",
    "mean_b",
    "std_r",
    "std_g",
    "std_b",
    "center_mean_r",
    "center_mean_g",
    "center_mean_b",
    "center_std_r",
    "center_std_g",
    "center_std_b",
    "brightness",
    "contrast",
    "center_brightness",
    "center_contrast",
    "blur_score",
    "center_blur_score",
    "saturation",
    "center_saturation",
    "hist_dark",
    "hist_shadow",
    "hist_mid",
    "hist_bright",
    "hist_highlight",
    "aspect_ratio",
    "red_green_gap",
    "center_red_green_gap",
    "size_score",
    # Pallor-specific features
    "cpi",
    "center_cpi",
    "redness_uniformity",
    "green_blue_ratio",
    # New v4 features
    "redness_ratio",          # R / (R+G+B) full image (alias of cpi, kept separate for clarity)
    "center_redness_ratio",   # R / (R+G+B) center crop
    "pallor_gradient",        # center_cpi - edge_cpi (positive = center paler than edge)
    "color_temp_proxy",       # (R-B) / (R+B) — warm/cool shift
    "center_color_temp",      # same for center crop
    "hue_mean",               # mean hue from HSV (0-1 normalised)
    "hue_std",                # std of hue — high std = mixed tones
    "center_hue_mean",        # center crop hue mean
    # v5 illumination-diagnostic features
    "illumination_mean",      # mean luminance before CLAHE correction [0,1]
    "illumination_std",       # luminance std before correction [0,1]
    "spectral_tilt_rb",       # (R-B)/(R+B) before grey-world — warm/cool cast
    "highlight_fraction",     # fraction of pixels blown out
    "shadow_fraction",        # fraction of shadow-clipped pixels
    "clahe_gain",             # how much CLAHE shifted the L* mean (lighting deficit proxy)
    # v6 advanced spectral/texture features
    "ycbcr_cb_mean",          # YCbCr Cb channel (blue-difference) — elevated in anemia
    "rgb_entropy",            # Shannon entropy of luminance histogram — lower in pale conjunctiva
    "inter_quadrant_gradient",# max CPI difference across 4 quadrants — asymmetric pallor signal
    "lbp_uniformity_proxy",   # center/periphery edge variance ratio — texture regularity
    "pallor_score",           # composite pallor index: low CPI + high Cb + low red_green_gap
]

COLOR_FEATURES = [
    "mean_r",
    "mean_g",
    "mean_b",
    "std_r",
    "std_g",
    "std_b",
    "center_mean_r",
    "center_mean_g",
    "center_mean_b",
    "center_std_r",
    "center_std_g",
    "center_std_b",
    "saturation",
    "center_saturation",
    "red_green_gap",
    "center_red_green_gap",
    # v4 additions
    "redness_ratio",
    "center_redness_ratio",
    "pallor_gradient",
    "color_temp_proxy",
    "center_color_temp",
    "hue_mean",
    "hue_std",
    "center_hue_mean",
    # v6 spectral additions
    "ycbcr_cb_mean",
    "rgb_entropy",
    "pallor_score",
]

TEXTURE_FEATURES = [
    "brightness",
    "contrast",
    "center_brightness",
    "center_contrast",
    "blur_score",
    "center_blur_score",
    "hist_dark",
    "hist_shadow",
    "hist_mid",
    "hist_bright",
    "hist_highlight",
    "aspect_ratio",
    "size_score",
]

FULL_FEATURES = FEATURE_NAMES[:]

ULTIMATE_CLINICAL_FEATURE_NAMES = [
    "pallor_intensity",
    "pallor_gradient",
    "red_channel_mean",
    "red_channel_std",
    "green_channel_mean",
    "green_channel_std",
    "blue_channel_mean",
    "blue_channel_std",
    "red_green_ratio",
    "red_blue_ratio",
    "green_blue_ratio",
    "color_variance",
    "pallor_color_index",
    "texture_smoothness",
    "texture_contrast",
    "texture_entropy",
    "vessel_visibility",
    "vessel_density",
    "vessel_color_intensity",
    "anemia_severity_score",
    "clinical_pallor_score",
    "image_sharpness",
    "lighting_uniformity",
    "noise_level",
    "age_pallor_interaction",
    "gender_color_interaction",
]

V8_CLINICAL_FEATURE_NAMES = ULTIMATE_CLINICAL_FEATURE_NAMES + [
    "brightness",
    "contrast",
    "center_brightness",
    "center_contrast",
    "blur_score",
    "center_blur_score",
    "center_cpi",
    "center_red_green_gap",
    "redness_ratio",
    "center_redness_ratio",
    "pallor_score",
    "illumination_mean",
    "illumination_std",
    "highlight_fraction",
    "shadow_fraction",
    "spectral_tilt_rb",
    "lighting_score",
    "glare_risk",
    "shadow_risk",
    "framing_score",
    "quality_passed_flag",
    "quality_warning_count",
    "quality_blocking_flag",
    "source_roi_original",
    "source_palpebral",
    "source_forniceal_palpebral",
]

_EDGE_KERNEL = ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1, offset=0)


def load_image_bytes(image_bytes: bytes) -> Image.Image:
    with Image.open(BytesIO(image_bytes)) as image:
        return ImageOps.exif_transpose(image).convert("RGB")


def load_image_path(path: str | Path) -> Image.Image:
    with Image.open(path) as image:
        return ImageOps.exif_transpose(image).convert("RGB")


def extract_eye_features(
    image: Image.Image,
    *,
    apply_lighting_norm: bool = True,
    lighting_norm_strength: float = 1.0,
) -> dict[str, float]:
    width, height = image.size

    # ── Illumination-bias diagnostics (computed BEFORE correction) ──────────
    illum_bias = compute_illumination_bias(image)

    # ── Lighting normalization (CLAHE + partial grey-world) ─────────────────
    # Applied before resizing so CLAHE works on full-resolution texture.
    if apply_lighting_norm:
        image, _lighting_score = normalize_illumination(
            image,
            clahe_strength=lighting_norm_strength,
        )

    normalized = image.resize((160, 160))
    center = _center_crop(normalized)
    grayscale = normalized.convert("L")
    center_gray = center.convert("L")

    mean_r, mean_g, mean_b = [value / 255.0 for value in ImageStat.Stat(normalized).mean]
    std_r, std_g, std_b = [value / 255.0 for value in ImageStat.Stat(normalized).stddev]
    center_mean_r, center_mean_g, center_mean_b = [
        value / 255.0 for value in ImageStat.Stat(center).mean
    ]
    center_std_r, center_std_g, center_std_b = [
        value / 255.0 for value in ImageStat.Stat(center).stddev
    ]

    brightness = ImageStat.Stat(grayscale).mean[0] / 255.0
    contrast = ImageStat.Stat(grayscale).stddev[0] / 255.0
    center_brightness = ImageStat.Stat(center_gray).mean[0] / 255.0
    center_contrast = ImageStat.Stat(center_gray).stddev[0] / 255.0

    blur_score = ImageStat.Stat(grayscale.filter(_EDGE_KERNEL)).var[0]
    center_blur_score = ImageStat.Stat(center_gray.filter(_EDGE_KERNEL)).var[0]

    saturation = _mean_saturation(normalized)
    center_saturation = _mean_saturation(center)

    hist = grayscale.histogram()
    total = float(sum(hist) or 1)
    hist_dark = sum(hist[0:32]) / total
    hist_shadow = sum(hist[32:96]) / total
    hist_mid = sum(hist[96:160]) / total
    hist_bright = sum(hist[160:224]) / total
    hist_highlight = sum(hist[224:256]) / total

    # Spectral features: Conjunctival Pallor Index (CPI)
    # CPI = R / (R + G + B) - a standard clinical screening metric
    denom = (mean_r + mean_g + mean_b) or 1e-6
    cpi = mean_r / denom

    center_denom = (center_mean_r + center_mean_g + center_mean_b) or 1e-6
    center_cpi = center_mean_r / center_denom

    # Redness uniformity: std of red channel across 4 quadrants
    # Low uniformity (high std) can indicate patchy pallor
    redness_uniformity = _quadrant_red_std(normalized)

    # Green-blue ratio: complementary to R/G for pallor detection
    green_blue_ratio = mean_g / max(mean_b, 1e-6)

    # --- v4 new features ---

    # Redness ratio: same formula as CPI but kept as an explicit separate feature
    # so the model can learn different weights for the two representations
    redness_ratio = cpi
    center_redness_ratio = center_cpi

    # Pallor gradient: how much paler the center is vs the periphery
    # Positive → center is redder than edge (healthy); negative → center paler (anemic)
    edge_cpi = _edge_cpi(normalized)
    pallor_gradient = center_cpi - edge_cpi

    # Color temperature proxy: (R-B)/(R+B) — warm shift correlates with healthy perfusion
    rb_sum = (mean_r + mean_b) or 1e-6
    color_temp_proxy = (mean_r - mean_b) / rb_sum
    center_rb_sum = (center_mean_r + center_mean_b) or 1e-6
    center_color_temp = (center_mean_r - center_mean_b) / center_rb_sum

    # Hue channel statistics from HSV
    hue_mean, hue_std = _hsv_hue_stats(normalized)
    center_hue_mean, _ = _hsv_hue_stats(center)

    # --- v6 advanced features ---

    # YCbCr Cb channel: blue-difference component elevated in anemic (pale) tissue
    ycbcr_cb_mean = _ycbcr_cb_mean(normalized)

    # Shannon entropy of luminance histogram — anemic conjunctiva tends to be
    # more uniform (lower entropy) due to reduced haemoglobin signal variation
    rgb_entropy = _luminance_entropy(normalized)

    # Max CPI difference across 4 quadrants — asymmetric pallor suggests
    # partial conjunctival involvement or ROI misalignment
    inter_quadrant_gradient = _inter_quadrant_cpi_gradient(normalized)

    # Center/periphery Laplacian variance ratio — measures whether texture detail
    # concentrates in the center (well-framed ROI) vs. scattered (poor crop)
    lbp_uniformity_proxy = _lbp_uniformity_proxy(normalized, center)

    # Composite pallor score: clinically calibrated combination of CPI, Cb, and
    # red-green gap. Designed so that score > 0.5 strongly suggests pallor.
    # Formula: 1 - cpi + 0.3*(ycbcr_cb_mean - 0.5) - 0.5*(mean_r - mean_g)
    pallor_score = float(
        (1.0 - cpi) * 0.55
        + (ycbcr_cb_mean - 0.5) * 0.3
        - (mean_r - mean_g) * 0.5
        + (1.0 - green_blue_ratio) * 0.15
    )
    # Clip to [0, 1] so the feature stays interpretable
    pallor_score = max(0.0, min(1.0, pallor_score))

    return {
        "mean_r": mean_r,
        "mean_g": mean_g,
        "mean_b": mean_b,
        "std_r": std_r,
        "std_g": std_g,
        "std_b": std_b,
        "center_mean_r": center_mean_r,
        "center_mean_g": center_mean_g,
        "center_mean_b": center_mean_b,
        "center_std_r": center_std_r,
        "center_std_g": center_std_g,
        "center_std_b": center_std_b,
        "brightness": brightness,
        "contrast": contrast,
        "center_brightness": center_brightness,
        "center_contrast": center_contrast,
        "blur_score": blur_score,
        "center_blur_score": center_blur_score,
        "saturation": saturation,
        "center_saturation": center_saturation,
        "hist_dark": hist_dark,
        "hist_shadow": hist_shadow,
        "hist_mid": hist_mid,
        "hist_bright": hist_bright,
        "hist_highlight": hist_highlight,
        "aspect_ratio": width / max(height, 1),
        "red_green_gap": mean_r - mean_g,
        "center_red_green_gap": center_mean_r - center_mean_g,
        "size_score": min(width, height) / 320.0,
        "cpi": cpi,
        "center_cpi": center_cpi,
        "redness_uniformity": redness_uniformity,
        "green_blue_ratio": green_blue_ratio,
        # v4 new features
        "redness_ratio": redness_ratio,
        "center_redness_ratio": center_redness_ratio,
        "pallor_gradient": pallor_gradient,
        "color_temp_proxy": color_temp_proxy,
        "center_color_temp": center_color_temp,
        "hue_mean": hue_mean,
        "hue_std": hue_std,
        "center_hue_mean": center_hue_mean,
        # v5 illumination-diagnostic features
        "illumination_mean": illum_bias["illumination_mean"],
        "illumination_std": illum_bias["illumination_std"],
        "spectral_tilt_rb": illum_bias["spectral_tilt_rb"],
        "highlight_fraction": illum_bias["highlight_fraction"],
        "shadow_fraction": illum_bias["shadow_fraction"],
        "clahe_gain": illum_bias["clahe_gain"],
        # v6 advanced spectral/texture features
        "ycbcr_cb_mean": ycbcr_cb_mean,
        "rgb_entropy": rgb_entropy,
        "inter_quadrant_gradient": inter_quadrant_gradient,
        "lbp_uniformity_proxy": lbp_uniformity_proxy,
        "pallor_score": pallor_score,
    }


def extract_ultimate_clinical_features(
    image: Image.Image,
    quality: QualityAssessment | None = None,
    *,
    age: int | None = None,
    sex: str = "not_specified",
) -> dict[str, float]:
    base = extract_eye_features(image)

    red_mean = float(base.get("center_mean_r", base.get("mean_r", 0.0)))
    green_mean = float(base.get("center_mean_g", base.get("mean_g", 0.0)))
    blue_mean = float(base.get("center_mean_b", base.get("mean_b", 0.0)))
    red_std = float(base.get("center_std_r", base.get("std_r", 0.0)))
    green_std = float(base.get("center_std_g", base.get("std_g", 0.0)))
    blue_std = float(base.get("center_std_b", base.get("std_b", 0.0)))

    pallor_intensity = _clamp01(
        (1.0 - float(base.get("center_cpi", 0.35))) * 1.45
    )
    pallor_gradient = _clamp01(
        0.5 - (float(base.get("pallor_gradient", 0.0)) * 2.4)
    )

    red_green_ratio = red_mean / max(green_mean, 1e-6)
    red_blue_ratio = red_mean / max(blue_mean, 1e-6)
    green_blue_ratio = green_mean / max(blue_mean, 1e-6)
    color_variance = _clamp01((red_std + green_std + blue_std) / 0.6)

    pallor_color_index = _clamp01(
        (float(base.get("pallor_score", 0.0)) * 0.55)
        + (pallor_intensity * 0.25)
        + (pallor_gradient * 0.20)
    )

    quality_blur_score = _quality_attr(
        quality,
        "blur_score",
        float(base.get("blur_score", 0.0)),
    )
    quality_lighting_score = _quality_attr(
        quality,
        "lighting_score",
        _clamp01(
            1.0
            - (
                float(base.get("illumination_std", 0.12)) * 2.1
                + float(base.get("highlight_fraction", 0.0)) * 0.55
                + float(base.get("shadow_fraction", 0.0)) * 0.55
            )
        ),
    )
    glare_risk = _quality_attr(
        quality,
        "glare_risk",
        _clamp01(float(base.get("highlight_fraction", 0.0)) * 2.4),
    )
    shadow_risk = _quality_attr(
        quality,
        "shadow_risk",
        _clamp01(float(base.get("shadow_fraction", 0.0)) * 2.2),
    )

    image_sharpness = _clamp01(quality_blur_score / 180.0)
    texture_contrast = _clamp01(float(base.get("center_contrast", base.get("contrast", 0.0))) * 2.8)
    texture_smoothness = _clamp01(
        1.0 - ((texture_contrast * 0.55) + (image_sharpness * 0.25))
    )
    texture_entropy = _clamp01(float(base.get("rgb_entropy", 0.0)) / 8.0)

    vessel_visibility = _clamp01(
        (float(base.get("center_red_green_gap", 0.0)) + 0.05) * 4.8
        + (image_sharpness * 0.30)
        - (glare_risk * 0.18)
        - (shadow_risk * 0.12)
    )
    vessel_density = _clamp01(
        (vessel_visibility * 0.72)
        + (texture_entropy * 0.18)
        + ((1.0 - texture_smoothness) * 0.10)
    )
    vessel_color_intensity = _clamp01(
        (float(base.get("redness_ratio", 0.0)) - 0.25) * 4.2
    )

    anemia_severity_score = _clamp01(
        (pallor_intensity * 0.40)
        + (pallor_color_index * 0.35)
        + ((1.0 - vessel_visibility) * 0.25)
    )
    clinical_pallor_score = _clamp01(
        (anemia_severity_score * 0.50)
        + (pallor_gradient * 0.20)
        + ((1.0 - vessel_density) * 0.15)
        + ((1.0 - vessel_color_intensity) * 0.15)
    )

    lighting_uniformity = _clamp01(
        (quality_lighting_score * 0.65)
        + ((1.0 - glare_risk) * 0.15)
        + ((1.0 - shadow_risk) * 0.20)
    )
    noise_level = _clamp01(
        (color_variance * 0.35)
        + ((1.0 - image_sharpness) * 0.25)
        + ((1.0 - lighting_uniformity) * 0.25)
        + (abs(float(base.get("spectral_tilt_rb", 0.0))) * 0.15)
    )

    age_scale = 0.0 if age is None else _clamp01((float(age) - 12.0) / 58.0)
    age_pallor_interaction = _clamp01(age_scale * clinical_pallor_score)

    sex_weight = {
        "female": 1.0,
        "male": 0.9,
        "other": 0.95,
        "not_specified": 0.0,
    }.get(str(sex).strip().lower(), 0.0)
    gender_color_interaction = _clamp01(sex_weight * vessel_color_intensity)

    return {
        "pallor_intensity": pallor_intensity,
        "pallor_gradient": pallor_gradient,
        "red_channel_mean": red_mean,
        "red_channel_std": red_std,
        "green_channel_mean": green_mean,
        "green_channel_std": green_std,
        "blue_channel_mean": blue_mean,
        "blue_channel_std": blue_std,
        "red_green_ratio": red_green_ratio,
        "red_blue_ratio": red_blue_ratio,
        "green_blue_ratio": green_blue_ratio,
        "color_variance": color_variance,
        "pallor_color_index": pallor_color_index,
        "texture_smoothness": texture_smoothness,
        "texture_contrast": texture_contrast,
        "texture_entropy": texture_entropy,
        "vessel_visibility": vessel_visibility,
        "vessel_density": vessel_density,
        "vessel_color_intensity": vessel_color_intensity,
        "anemia_severity_score": anemia_severity_score,
        "clinical_pallor_score": clinical_pallor_score,
        "image_sharpness": image_sharpness,
        "lighting_uniformity": lighting_uniformity,
        "noise_level": noise_level,
        "age_pallor_interaction": age_pallor_interaction,
        "gender_color_interaction": gender_color_interaction,
    }


def extract_v8_clinical_features(
    image: Image.Image,
    quality: QualityAssessment | None = None,
    *,
    age: int | None = None,
    sex: str = "not_specified",
    source_hint: str = "roi_original",
) -> dict[str, float]:
    base = extract_eye_features(image)
    clinical = extract_ultimate_clinical_features(
        image,
        quality,
        age=age,
        sex=sex,
    )

    lighting_score = _quality_attr(
        quality,
        "lighting_score",
        _clamp01(
            1.0
            - (
                float(base.get("illumination_std", 0.12)) * 2.0
                + float(base.get("highlight_fraction", 0.0)) * 0.55
                + float(base.get("shadow_fraction", 0.0)) * 0.55
            )
        ),
    )
    glare_risk = _quality_attr(
        quality,
        "glare_risk",
        _clamp01(float(base.get("highlight_fraction", 0.0)) * 2.4),
    )
    shadow_risk = _quality_attr(
        quality,
        "shadow_risk",
        _clamp01(float(base.get("shadow_fraction", 0.0)) * 2.2),
    )
    framing = _quality_attr(
        quality,
        "framing_score",
        max(float(framing_score(base)), 0.0),
    )
    warning_count = (
        sum(1 for issue in quality.issues if issue.severity == "warning")
        if quality is not None
        else 0
    )
    blocking_count = (
        sum(1 for issue in quality.issues if issue.severity == "blocking")
        if quality is not None
        else 0
    )
    passed_flag = (
        1.0
        if quality is not None and quality.passed
        else 1.0
        if (
            float(base.get("blur_score", 0.0)) >= 45.0
            and 0.10 <= float(base.get("brightness", 0.24)) <= 0.92
            and float(base.get("contrast", 0.1)) >= 0.05
        )
        else 0.0
    )

    source_value = str(source_hint).strip().lower()

    combined = {
        **clinical,
        "brightness": float(base.get("brightness", 0.0)),
        "contrast": float(base.get("contrast", 0.0)),
        "center_brightness": float(base.get("center_brightness", 0.0)),
        "center_contrast": float(base.get("center_contrast", 0.0)),
        "blur_score": float(base.get("blur_score", 0.0)),
        "center_blur_score": float(base.get("center_blur_score", 0.0)),
        "center_cpi": float(base.get("center_cpi", 0.0)),
        "center_red_green_gap": float(base.get("center_red_green_gap", 0.0)),
        "redness_ratio": float(base.get("redness_ratio", 0.0)),
        "center_redness_ratio": float(base.get("center_redness_ratio", 0.0)),
        "pallor_score": float(base.get("pallor_score", 0.0)),
        "illumination_mean": float(base.get("illumination_mean", 0.5)),
        "illumination_std": float(base.get("illumination_std", 0.12)),
        "highlight_fraction": float(base.get("highlight_fraction", 0.0)),
        "shadow_fraction": float(base.get("shadow_fraction", 0.0)),
        "spectral_tilt_rb": float(base.get("spectral_tilt_rb", 0.0)),
        "lighting_score": float(lighting_score),
        "glare_risk": float(glare_risk),
        "shadow_risk": float(shadow_risk),
        "framing_score": float(framing),
        "quality_passed_flag": passed_flag,
        "quality_warning_count": _clamp01(float(warning_count) / 4.0),
        "quality_blocking_flag": _clamp01(float(blocking_count)),
        "source_roi_original": 1.0 if source_value == "roi_original" else 0.0,
        "source_palpebral": 1.0 if source_value == "palpebral" else 0.0,
        "source_forniceal_palpebral": 1.0 if source_value == "forniceal_palpebral" else 0.0,
    }
    return {name: float(combined.get(name, 0.0)) for name in V8_CLINICAL_FEATURE_NAMES}


def vectorize_features(feature_map: dict[str, float], names: list[str]) -> list[float]:
    return [float(feature_map[name]) for name in names]


def _quality_attr(
    quality: QualityAssessment | None,
    name: str,
    fallback: float,
) -> float:
    if quality is None:
        return float(fallback)
    value = getattr(quality, name, fallback)
    if value is None:
        return float(fallback)
    return float(value)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def framing_score(feature_map: dict[str, float]) -> float:
    center_detail_ratio = feature_map["center_blur_score"] / max(feature_map["blur_score"], 1e-6)
    center_focus = feature_map["center_contrast"] / max(feature_map["contrast"], 1e-6)
    redness_signal = max(0.0, feature_map["center_red_green_gap"] + 0.06) * 4.0
    return center_detail_ratio + (center_focus * 0.5) + redness_signal


def edge_blur_baseline(image: Image.Image) -> float:
    normalized = image.resize((160, 160)).convert("L")
    width, height = normalized.size
    margin_x = width // 6
    margin_y = height // 6
    bands = [
        normalized.crop((0, 0, width, margin_y)),
        normalized.crop((0, height - margin_y, width, height)),
        normalized.crop((0, 0, margin_x, height)),
        normalized.crop((width - margin_x, 0, width, height)),
    ]
    return mean(ImageStat.Stat(band.filter(_EDGE_KERNEL)).var[0] for band in bands)


def _center_crop(image: Image.Image) -> Image.Image:
    width, height = image.size
    left = width // 4
    top = height // 4
    right = width - left
    bottom = height - top
    return image.crop((left, top, right, bottom))


def _mean_saturation(image: Image.Image) -> float:
    sample = image.resize((64, 64)).convert("HSV")
    return ImageStat.Stat(sample).mean[1] / 255.0


def _quadrant_red_std(image: Image.Image) -> float:
    """
    Compute std of mean red channel across 4 quadrants.
    Low std → uniform redness (healthy); high std → patchy pallor.
    Normalised to [0, 1].
    """
    w, h = image.size
    hw, hh = w // 2, h // 2
    quadrants = [
        image.crop((0, 0, hw, hh)),
        image.crop((hw, 0, w, hh)),
        image.crop((0, hh, hw, h)),
        image.crop((hw, hh, w, h)),
    ]
    means = [ImageStat.Stat(q).mean[0] / 255.0 for q in quadrants]
    std = float(mean([(m - sum(means) / 4) ** 2 for m in means]) ** 0.5)
    # Normalise: typical range 0-0.15 → map to 0-1
    return min(std / 0.15, 1.0)


def _edge_cpi(image: Image.Image) -> float:
    """CPI computed on the peripheral ring (outer 25% border) of the image."""
    w, h = image.size
    mx, my = w // 4, h // 4
    # Collect the four border strips
    strips = [
        image.crop((0, 0, w, my)),           # top
        image.crop((0, h - my, w, h)),        # bottom
        image.crop((0, my, mx, h - my)),      # left
        image.crop((w - mx, my, w, h - my)),  # right
    ]
    r_vals, g_vals, b_vals = [], [], []
    for strip in strips:
        s = ImageStat.Stat(strip)
        r_vals.append(s.mean[0] / 255.0)
        g_vals.append(s.mean[1] / 255.0)
        b_vals.append(s.mean[2] / 255.0)
    er = mean(r_vals)
    eg = mean(g_vals)
    eb = mean(b_vals)
    denom = (er + eg + eb) or 1e-6
    return er / denom


def _hsv_hue_stats(image: Image.Image) -> tuple[float, float]:
    """Return (mean_hue, std_hue) normalised to [0, 1] from the HSV hue channel."""
    hsv = image.resize((64, 64)).convert("HSV")
    hue_channel = hsv.split()[0]  # H channel, 0-255
    stat = ImageStat.Stat(hue_channel)
    hue_mean = stat.mean[0] / 255.0
    hue_std = stat.stddev[0] / 255.0
    return hue_mean, hue_std


def _ycbcr_cb_mean(image: Image.Image) -> float:
    """
    v6: YCbCr Cb (blue-difference) channel mean normalised to [0, 1].
    The Cb component is higher for bluish / pale tissue. In anemic conjunctiva
    haemoglobin concentration drops, shifting colour from red toward pale-blue,
    raising Cb.  Typical healthy range: 0.45-0.52; anemic: 0.53-0.62.
    """
    try:
        ycbcr = image.resize((64, 64)).convert("YCbCr")
        cb_channel = ycbcr.split()[1]  # Cb channel
        return ImageStat.Stat(cb_channel).mean[0] / 255.0
    except Exception:
        return 0.5  # safe neutral default


def _luminance_entropy(image: Image.Image) -> float:
    """
    v6: Shannon entropy of the luminance (L* in LAB) histogram.
    Low entropy → the image is concentrated in a narrow brightness band →
    typical of pale, homogeneous conjunctiva in anaemic subjects.
    Returns value normalised approximately to [0, 1] (divide by log2(256)).
    """
    import math as _math
    gray = image.resize((64, 64)).convert("L")
    hist = gray.histogram()          # 256 bins
    total = float(sum(hist) or 1)
    entropy = 0.0
    for count in hist:
        if count > 0:
            p = count / total
            entropy -= p * _math.log2(p)
    return entropy / 8.0             # 8 = log2(256), normalise to ~[0,1]


def _inter_quadrant_cpi_gradient(image: Image.Image) -> float:
    """
    v6: Maximum CPI difference between any two of the 4 quadrants.
    Large gradient → asymmetric pallor (partial ROI, eyelash occlusion, or
    gradient illumination unresolved by CLAHE).
    Normalised to [0, 1]; typical: <0.06 healthy, >0.12 suspect.
    """
    w, h = image.size
    hw, hh = w // 2, h // 2
    quadrants = [
        image.crop((0,  0,  hw, hh)),
        image.crop((hw, 0,  w,  hh)),
        image.crop((0,  hh, hw, h)),
        image.crop((hw, hh, w,  h)),
    ]
    cpis = []
    for q in quadrants:
        stat = ImageStat.Stat(q)
        r, g, b = [v / 255.0 for v in stat.mean]
        denom = (r + g + b) or 1e-6
        cpis.append(r / denom)
    gradient = max(cpis) - min(cpis)
    return min(gradient / 0.20, 1.0)   # 0.20 → normalisation ceiling


def _lbp_uniformity_proxy(image: Image.Image, center: Image.Image) -> float:
    """
    v6: Ratio of center Laplacian variance to full-image Laplacian variance.
    A well-cropped, in-focus conjunctival ROI with a sharp conjunctival vessel
    bed shows higher texture energy in the center. Low ratio < 0.8 suggests
    the image is out-of-focus or poorly centred.
    Clipped to [0, 2] then normalised by dividing by 2.
    """
    edge_var_full   = ImageStat.Stat(image.convert("L").filter(_EDGE_KERNEL)).var[0]
    edge_var_center = ImageStat.Stat(center.convert("L").filter(_EDGE_KERNEL)).var[0]
    if edge_var_full < 1e-6:
        return 0.5
    ratio = edge_var_center / edge_var_full
    return min(ratio, 2.0) / 2.0
