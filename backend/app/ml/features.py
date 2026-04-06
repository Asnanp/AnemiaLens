from __future__ import annotations

import logging
import math
from io import BytesIO
from pathlib import Path
from statistics import mean

from PIL import Image, ImageFilter, ImageOps, ImageStat

from app.ml.lighting_norm import compute_illumination_bias, normalize_illumination
from app.schemas import QualityAssessment

log = logging.getLogger("anemialens.features")

# ---------------------------------------------------------------------------
# Feature name lists (extended with v7 additions)
# ---------------------------------------------------------------------------

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
    # v4 features
    "redness_ratio",
    "center_redness_ratio",
    "pallor_gradient",
    "color_temp_proxy",
    "center_color_temp",
    "hue_mean",
    "hue_std",
    "center_hue_mean",
    # v5 illumination-diagnostic features
    "illumination_mean",
    "illumination_std",
    "spectral_tilt_rb",
    "highlight_fraction",
    "shadow_fraction",
    "clahe_gain",
    # v6 advanced spectral/texture features
    "ycbcr_cb_mean",
    "rgb_entropy",
    "inter_quadrant_gradient",
    "lbp_uniformity_proxy",
    "pallor_score",
    # v7 HSV color features
    "hsv_h_mean",
    "hsv_s_mean",
    "hsv_v_mean",
    "hsv_h_std",
    "hsv_s_std",
    "hsv_v_std",
    "hsv_red_region_sat",       # saturation in red hue region
    "hsv_red_region_val",       # value in red hue region
    "hsv_pallor_region_ratio",  # fraction of pixels in pale hue range
    # v7 LAB color features
    "lab_l_mean",
    "lab_a_mean",
    "lab_b_mean",
    "lab_l_std",
    "lab_a_std",
    "lab_b_std",
    "lab_a_b_ratio",            # a*/b* chromatic ratio
    "lab_chroma_mean",          # sqrt(a*^2 + b*^2)
    "lab_lightness_contrast",   # L* center vs edge difference
    # v7 LAB center features
    "center_lab_l_mean",
    "center_lab_a_mean",
    "center_lab_b_mean",
    # v7 advanced color features
    "color_homogeneity",        # HSV color variance (lower = more uniform)
    "warm_cool_ratio",          # ratio of warm to cool pixels
    "red_saturation_deficit",   # how much red channel lacks saturation
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
    # v7 texture features
    "lbp_variance_r1",
    "lbp_variance_r2",
    "lbp_uniform_ratio_r1",
    "lbp_uniform_ratio_r2",
    "lbp_entropy_r1",
    "lbp_entropy_r2",
    "lbp_dominant_pattern_r1",
    "edge_density",
    "edge_density_center",
    "edge_orientation_entropy",
    "gradient_magnitude_mean",
    "gradient_magnitude_std",
    "canny_edge_density",
    "sobel_energy",
    # v7 symmetry features
    "horizontal_symmetry_rgb",
    "horizontal_symmetry_l",
    "vertical_symmetry_rgb",
    "radial_symmetry",
    # v7 vascular features
    "vascular_density",
    "vascular_branching",
    "vascular_tortuosity",
    "vessel_contrast_ratio",
    "vessel_color_ratio",
    "microvessel_density",
    "large_vessel_density",
    # v7 advanced texture
    "gabor_energy_mean",
    "gabor_energy_std",
    "coarseness",
    "local_binary_pattern_energy",
]

FULL_FEATURES = FEATURE_NAMES[:]

# Full feature names including v7 additions
ALL_FEATURE_NAMES_V7 = FEATURE_NAMES + [
    "lbp_variance_r1",
    "lbp_variance_r2",
    "lbp_uniform_ratio_r1",
    "lbp_uniform_ratio_r2",
    "lbp_entropy_r1",
    "lbp_entropy_r2",
    "lbp_dominant_pattern_r1",
    "edge_density",
    "edge_density_center",
    "edge_orientation_entropy",
    "gradient_magnitude_mean",
    "gradient_magnitude_std",
    "canny_edge_density",
    "sobel_energy",
    "horizontal_symmetry_rgb",
    "horizontal_symmetry_l",
    "vertical_symmetry_rgb",
    "radial_symmetry",
    "vascular_density",
    "vascular_branching",
    "vascular_tortuosity",
    "vessel_contrast_ratio",
    "vessel_color_ratio",
    "microvessel_density",
    "large_vessel_density",
    "gabor_energy_mean",
    "gabor_energy_std",
    "coarseness",
    "local_binary_pattern_energy",
]

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

# ---------------------------------------------------------------------------
# Kernels
# ---------------------------------------------------------------------------

_EDGE_KERNEL = ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1, offset=0)

# LBP-like kernel for texture (3x3 variance computation)
_LBP_KERNEL = ImageFilter.Kernel((3, 3), [1, 1, 1, 1, -8, 1, 1, 1, 1], scale=1, offset=0)

# Sobel kernels
_SOBEL_X = ImageFilter.Kernel((3, 3), [-1, 0, 1, -2, 0, 2, -1, 0, 1], scale=1, offset=0)
_SOBEL_Y = ImageFilter.Kernel((3, 3), [-1, -2, -1, 0, 0, 0, 1, 2, 1], scale=1, offset=0)


# ---------------------------------------------------------------------------
# Image loading
# ---------------------------------------------------------------------------

def load_image_bytes(image_bytes: bytes) -> Image.Image:
    with Image.open(BytesIO(image_bytes)) as image:
        return ImageOps.exif_transpose(image).convert("RGB")


def load_image_path(path: str | Path) -> Image.Image:
    with Image.open(path) as image:
        return ImageOps.exif_transpose(image).convert("RGB")


# ---------------------------------------------------------------------------
# Main feature extraction (v7 — includes HSV, LAB, LBP, edge, symmetry, vascular)
# ---------------------------------------------------------------------------

def extract_eye_features(
    image: Image.Image,
    *,
    apply_lighting_norm: bool = True,
    lighting_norm_strength: float = 1.0,
) -> dict[str, float]:
    """
    Extract all engineered features from a conjunctiva image.

    v7 additions:
    - HSV color space features (hue/saturation/value statistics)
    - LAB color space features (lightness, a*, b* chromatic)
    - LBP texture features with multiple radii
    - Edge density features (Sobel, Canny proxy)
    - Symmetry features (horizontal, vertical, radial)
    - Vascular pattern detection
    - Better feature normalization
    """
    width, height = image.size

    # ── Illumination-bias diagnostics (computed BEFORE correction) ──────────
    illum_bias = compute_illumination_bias(image)

    # ── Lighting normalization (CLAHE + partial grey-world) ─────────────────
    if apply_lighting_norm:
        image, _lighting_score = normalize_illumination(
            image,
            clahe_strength=lighting_norm_strength,
        )

    normalized = image.resize((160, 160))
    center = _center_crop(normalized)
    grayscale = normalized.convert("L")
    center_gray = center.convert("L")

    # ── RGB statistics ──────────────────────────────────────────────────────
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

    # ── Spectral features: Conjunctival Pallor Index (CPI) ──────────────────
    denom = (mean_r + mean_g + mean_b) or 1e-6
    cpi = mean_r / denom

    center_denom = (center_mean_r + center_mean_g + center_mean_b) or 1e-6
    center_cpi = center_mean_r / center_denom

    redness_uniformity = _quadrant_red_std(normalized)
    green_blue_ratio = mean_g / max(mean_b, 1e-6)

    # ── v4 features ─────────────────────────────────────────────────────────
    redness_ratio = cpi
    center_redness_ratio = center_cpi

    edge_cpi = _edge_cpi(normalized)
    pallor_gradient_val = center_cpi - edge_cpi

    rb_sum = (mean_r + mean_b) or 1e-6
    color_temp_proxy = (mean_r - mean_b) / rb_sum
    center_rb_sum = (center_mean_r + center_mean_b) or 1e-6
    center_color_temp = (center_mean_r - center_mean_b) / center_rb_sum

    hue_mean, hue_std = _hsv_hue_stats(normalized)
    center_hue_mean, _ = _hsv_hue_stats(center)

    # ── v6 advanced features ────────────────────────────────────────────────
    ycbcr_cb_mean = _ycbcr_cb_mean(normalized)
    rgb_entropy = _luminance_entropy(normalized)
    inter_quadrant_gradient = _inter_quadrant_cpi_gradient(normalized)
    lbp_uniformity_proxy = _lbp_uniformity_proxy(normalized, center)

    pallor_score = float(
        (1.0 - cpi) * 0.55
        + (ycbcr_cb_mean - 0.5) * 0.3
        - (mean_r - mean_g) * 0.5
        + (1.0 - green_blue_ratio) * 0.15
    )
    pallor_score = max(0.0, min(1.0, pallor_score))

    # ── v7 HSV color space features ─────────────────────────────────────────
    hsv_features = _extract_hsv_features(normalized, center)

    # ── v7 LAB color space features ─────────────────────────────────────────
    lab_features = _extract_lab_features(normalized, center)

    # ── v7 Advanced color features ──────────────────────────────────────────
    advanced_color_features = _extract_advanced_color_features(normalized, mean_r, mean_g, mean_b)

    # ── v7 LBP Texture features (multiple radii) ────────────────────────────
    lbp_features = _extract_lbp_features(normalized, center)

    # ── v7 Edge density features ────────────────────────────────────────────
    edge_features = _extract_edge_features(normalized, center, grayscale)

    # ── v7 Symmetry features ────────────────────────────────────────────────
    symmetry_features = _extract_symmetry_features(normalized, grayscale)

    # ── v7 Vascular pattern features ────────────────────────────────────────
    vascular_features = _extract_vascular_features(normalized, center, grayscale)

    return {
        # RGB
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
        # Brightness / contrast
        "brightness": brightness,
        "contrast": contrast,
        "center_brightness": center_brightness,
        "center_contrast": center_contrast,
        "blur_score": blur_score,
        "center_blur_score": center_blur_score,
        "saturation": saturation,
        "center_saturation": center_saturation,
        # Histogram
        "hist_dark": hist_dark,
        "hist_shadow": hist_shadow,
        "hist_mid": hist_mid,
        "hist_bright": hist_bright,
        "hist_highlight": hist_highlight,
        # Geometry
        "aspect_ratio": width / max(height, 1),
        "red_green_gap": mean_r - mean_g,
        "center_red_green_gap": center_mean_r - center_mean_g,
        "size_score": min(width, height) / 320.0,
        # Pallor
        "cpi": cpi,
        "center_cpi": center_cpi,
        "redness_uniformity": redness_uniformity,
        "green_blue_ratio": green_blue_ratio,
        # v4
        "redness_ratio": redness_ratio,
        "center_redness_ratio": center_redness_ratio,
        "pallor_gradient": pallor_gradient_val,
        "color_temp_proxy": color_temp_proxy,
        "center_color_temp": center_color_temp,
        "hue_mean": hue_mean,
        "hue_std": hue_std,
        "center_hue_mean": center_hue_mean,
        # v5
        "illumination_mean": illum_bias["illumination_mean"],
        "illumination_std": illum_bias["illumination_std"],
        "spectral_tilt_rb": illum_bias["spectral_tilt_rb"],
        "highlight_fraction": illum_bias["highlight_fraction"],
        "shadow_fraction": illum_bias["shadow_fraction"],
        "clahe_gain": illum_bias["clahe_gain"],
        # v6
        "ycbcr_cb_mean": ycbcr_cb_mean,
        "rgb_entropy": rgb_entropy,
        "inter_quadrant_gradient": inter_quadrant_gradient,
        "lbp_uniformity_proxy": lbp_uniformity_proxy,
        "pallor_score": pallor_score,
        # v7 HSV
        **hsv_features,
        # v7 LAB
        **lab_features,
        # v7 advanced color
        **advanced_color_features,
        # v7 texture (LBP, edge, symmetry, vascular)
        **lbp_features,
        **edge_features,
        **symmetry_features,
        **vascular_features,
    }


# ---------------------------------------------------------------------------
# v7 HSV Feature Extraction
# ---------------------------------------------------------------------------

def _extract_hsv_features(image: Image.Image, center: Image.Image) -> dict[str, float]:
    """
    Extract HSV color space features.

    HSV provides perceptually meaningful color descriptors:
    - Hue: dominant color type (red, green, etc.)
    - Saturation: color purity/vividness
    - Value: brightness independent of color
    """
    try:
        hsv = image.resize((64, 64)).convert("HSV")
        h, s, v = hsv.split()

        h_stat = ImageStat.Stat(h)
        s_stat = ImageStat.Stat(s)
        v_stat = ImageStat.Stat(v)

        hsv_h_mean = h_stat.mean[0] / 255.0
        hsv_s_mean = s_stat.mean[0] / 255.0
        hsv_v_mean = v_stat.mean[0] / 255.0
        hsv_h_std = h_stat.stddev[0] / 255.0
        hsv_s_std = s_stat.stddev[0] / 255.0
        hsv_v_std = v_stat.stddev[0] / 255.0

        # Red region analysis: hue near 0 or 255 (red wraps around)
        # In PIL HSV, H=0 is red, H~85 is green, H~170 is blue
        h_pixels = list(h.getdata())
        s_pixels = list(s.getdata())
        v_pixels = list(v.getdata())

        # Red hue region: H < 15 or H > 240 (normalized: < 0.06 or > 0.94)
        red_region_sat = 0.5
        red_region_val = 0.5
        red_count = 0
        for hv, sv, vv in zip(h_pixels, s_pixels, v_pixels):
            h_norm = hv / 255.0
            if h_norm < 0.06 or h_norm > 0.94:
                red_region_sat = (red_region_sat * red_count + sv / 255.0) / (red_count + 1)
                red_region_val = (red_region_val * red_count + vv / 255.0) / (red_count + 1)
                red_count += 1

        # Pallor region: low saturation, high value (pale/white pixels)
        # Hue in pink/pale range: H ~ 0-25 (norm 0-0.1), S < 0.3, V > 0.5
        pallor_count = 0
        for hv, sv, vv in zip(h_pixels, s_pixels, v_pixels):
            h_norm = hv / 255.0
            s_norm = sv / 255.0
            v_norm = vv / 255.0
            if h_norm < 0.1 and s_norm < 0.35 and v_norm > 0.45:
                pallor_count += 1
        hsv_pallor_region_ratio = pallor_count / max(len(h_pixels), 1)

        return {
            "hsv_h_mean": _clamp01(hsv_h_mean),
            "hsv_s_mean": _clamp01(hsv_s_mean),
            "hsv_v_mean": _clamp01(hsv_v_mean),
            "hsv_h_std": _clamp01(hsv_h_std),
            "hsv_s_std": _clamp01(hsv_s_std),
            "hsv_v_std": _clamp01(hsv_v_std),
            "hsv_red_region_sat": _clamp01(red_region_sat),
            "hsv_red_region_val": _clamp01(red_region_val),
            "hsv_pallor_region_ratio": _clamp01(hsv_pallor_region_ratio),
        }
    except Exception as e:
        log.warning("HSV feature extraction failed: %s", e)
        return {
            "hsv_h_mean": 0.0, "hsv_s_mean": 0.5, "hsv_v_mean": 0.5,
            "hsv_h_std": 0.0, "hsv_s_std": 0.0, "hsv_v_std": 0.0,
            "hsv_red_region_sat": 0.5, "hsv_red_region_val": 0.5,
            "hsv_pallor_region_ratio": 0.0,
        }


# ---------------------------------------------------------------------------
# v7 LAB Feature Extraction
# ---------------------------------------------------------------------------

def _extract_lab_features(image: Image.Image, center: Image.Image) -> dict[str, float]:
    """
    Extract LAB (CIE L*a*b*) color space features.

    LAB is perceptually uniform:
    - L*: lightness (0=black, 100=white)
    - a*: green-red axis (negative=green, positive=red)
    - b*: blue-yellow axis (negative=blue, positive=yellow)

    The a* channel is particularly informative for conjunctival pallor
    as it captures the red-green balance of blood perfusion.
    """
    try:
        lab = image.resize((64, 64)).convert("LAB")
        l_ch, a_ch, b_ch = lab.split()

        l_stat = ImageStat.Stat(l_ch)
        a_stat = ImageStat.Stat(a_ch)
        b_stat = ImageStat.Stat(b_ch)

        lab_l_mean = l_stat.mean[0] / 255.0
        lab_a_mean = a_stat.mean[0] / 255.0
        lab_b_mean = b_stat.mean[0] / 255.0
        lab_l_std = l_stat.stddev[0] / 255.0
        lab_a_std = a_stat.stddev[0] / 255.0
        lab_b_std = b_stat.stddev[0] / 255.0

        # a*/b* chromatic ratio: indicates red vs yellow dominance
        lab_a_b_ratio = lab_a_mean / max(abs(lab_b_mean), 1e-6)

        # Chroma: colorfulness relative to brightness
        lab_chroma_mean = math.sqrt(lab_a_mean ** 2 + lab_b_mean ** 2)

        # Lightness contrast: center L* vs edge L*
        center_lab = center.resize((32, 32)).convert("LAB")
        center_l = ImageStat.Stat(center_lab.split()[0]).mean[0] / 255.0
        lab_lightness_contrast = abs(lab_l_mean - center_l)

        # Center LAB features
        center_a = ImageStat.Stat(center_lab.split()[1]).mean[0] / 255.0
        center_b = ImageStat.Stat(center_lab.split()[2]).mean[0] / 255.0

        return {
            "lab_l_mean": _clamp01(lab_l_mean),
            "lab_a_mean": _clamp01(lab_a_mean),
            "lab_b_mean": _clamp01(lab_b_mean),
            "lab_l_std": _clamp01(lab_l_std),
            "lab_a_std": _clamp01(lab_a_std),
            "lab_b_std": _clamp01(lab_b_std),
            "lab_a_b_ratio": float(np.clip(lab_a_b_ratio / 2.0, 0.0, 1.0)),
            "lab_chroma_mean": _clamp01(lab_chroma_mean / 128.0),
            "lab_lightness_contrast": _clamp01(lab_lightness_contrast),
            "center_lab_l_mean": _clamp01(center_l),
            "center_lab_a_mean": _clamp01(center_a),
            "center_lab_b_mean": _clamp01(center_b),
        }
    except Exception as e:
        log.warning("LAB feature extraction failed: %s", e)
        return {
            "lab_l_mean": 0.5, "lab_a_mean": 0.5, "lab_b_mean": 0.5,
            "lab_l_std": 0.0, "lab_a_std": 0.0, "lab_b_std": 0.0,
            "lab_a_b_ratio": 0.5, "lab_chroma_mean": 0.0,
            "lab_lightness_contrast": 0.0,
            "center_lab_l_mean": 0.5, "center_lab_a_mean": 0.5,
            "center_lab_b_mean": 0.5,
        }


# ---------------------------------------------------------------------------
# v7 Advanced Color Features
# ---------------------------------------------------------------------------

def _extract_advanced_color_features(
    image: Image.Image,
    mean_r: float,
    mean_g: float,
    mean_b: float,
) -> dict[str, float]:
    """
    Extract advanced color features for anemia detection.
    """
    try:
        hsv = image.resize((64, 64)).convert("HSV")
        h, s, v = hsv.split()

        # Color homogeneity: inverse of HSV color variance
        s_stat = ImageStat.Stat(s)
        v_stat = ImageStat.Stat(v)
        color_variance = (s_stat.stddev[0] ** 2 + v_stat.stddev[0] ** 2) / (255.0 ** 2)
        color_homogeneity = 1.0 - min(color_variance * 10.0, 1.0)

        # Warm/cool ratio: warm pixels (red/orange) vs cool (blue/green)
        h_pixels = list(h.getdata())
        warm_count = 0
        cool_count = 0
        for hv in h_pixels:
            h_norm = hv / 255.0
            if h_norm < 0.12 or h_norm > 0.88:  # red-orange range
                warm_count += 1
            elif 0.3 < h_norm < 0.7:  # cyan-blue range
                cool_count += 1
        warm_cool_ratio = warm_count / max(cool_count, 1)
        warm_cool_ratio = min(warm_cool_ratio / 3.0, 1.0)  # normalize

        # Red saturation deficit: how much the red channel lacks saturation
        # Anemic tissue: red channel is present but desaturated
        r_pixels = list(image.resize((64, 64)).split()[0].getdata())
        s_pixels = list(s.getdata())
        red_sat_values = [sv for rv, sv in zip(r_pixels, s_pixels) if rv > 128]
        if red_sat_values:
            red_sat_mean = sum(red_sat_values) / len(red_sat_values) / 255.0
        else:
            red_sat_mean = 0.5
        red_saturation_deficit = 1.0 - red_sat_mean

        return {
            "color_homogeneity": _clamp01(color_homogeneity),
            "warm_cool_ratio": _clamp01(warm_cool_ratio),
            "red_saturation_deficit": _clamp01(red_saturation_deficit),
        }
    except Exception as e:
        log.warning("Advanced color feature extraction failed: %s", e)
        return {
            "color_homogeneity": 0.5,
            "warm_cool_ratio": 0.5,
            "red_saturation_deficit": 0.5,
        }


# ---------------------------------------------------------------------------
# v7 LBP Texture Features (Multiple Radii)
# ---------------------------------------------------------------------------

def _extract_lbp_features(image: Image.Image, center: Image.Image) -> dict[str, float]:
    """
    Extract Local Binary Pattern-like texture features at multiple radii.

    Uses Laplacian-of-Gaussian filters at different scales as a proxy for
    LBP (since PIL doesn't have native LBP). Multi-scale texture captures
    both fine capillary patterns and larger vessel structures.
    """
    try:
        gray = image.resize((64, 64)).convert("L")
        gray_center = center.resize((32, 32)).convert("L")

        # Radius 1: fine texture (capillary-level)
        fine_edges = gray.filter(_EDGE_KERNEL)
        fine_stat = ImageStat.Stat(fine_edges)
        lbp_variance_r1 = fine_stat.var[0] / (255.0 ** 2) if fine_stat.var[0] > 0 else 0.0

        # Uniform patterns proxy: ratio of edge pixels with consistent direction
        edge_pixels = list(fine_edges.getdata())
        edge_above = sum(1 for p in edge_pixels if p > 140)
        edge_below = sum(1 for p in edge_pixels if p < 115)
        edge_total = edge_above + edge_below
        lbp_uniform_ratio_r1 = max(edge_above, edge_below) / max(edge_total, 1)

        # LBP entropy r1: measure of texture complexity
        lbp_entropy_r1 = _compute_entropy(fine_edges)

        # Dominant pattern (are edges mostly positive or negative?)
        lbp_dominant_pattern_r1 = 1.0 if edge_above > edge_below else 0.0

        # Radius 2: coarser texture (vessel-level) using Gaussian blur + edge
        coarse = gray.filter(ImageFilter.GaussianBlur(radius=2))
        coarse_edges = coarse.filter(_EDGE_KERNEL)
        coarse_stat = ImageStat.Stat(coarse_edges)
        lbp_variance_r2 = coarse_stat.var[0] / (255.0 ** 2) if coarse_stat.var[0] > 0 else 0.0

        # Coarse uniform ratio
        coarse_edge_pixels = list(coarse_edges.getdata())
        c_above = sum(1 for p in coarse_edge_pixels if p > 140)
        c_below = sum(1 for p in coarse_edge_pixels if p < 115)
        c_total = c_above + c_below
        lbp_uniform_ratio_r2 = max(c_above, c_below) / max(c_total, 1)

        # LBP entropy r2
        lbp_entropy_r2 = _compute_entropy(coarse_edges)

        # LBP energy
        lbp_energy = sum(p ** 2 for p in edge_pixels) / (255.0 ** 2 * len(edge_pixels))

        return {
            "lbp_variance_r1": _clamp01(lbp_variance_r1 * 5.0),
            "lbp_variance_r2": _clamp01(lbp_variance_r2 * 5.0),
            "lbp_uniform_ratio_r1": _clamp01(lbp_uniform_ratio_r1),
            "lbp_uniform_ratio_r2": _clamp01(lbp_uniform_ratio_r2),
            "lbp_entropy_r1": _clamp01(lbp_entropy_r1),
            "lbp_entropy_r2": _clamp01(lbp_entropy_r2),
            "lbp_dominant_pattern_r1": lbp_dominant_pattern_r1,
            "local_binary_pattern_energy": _clamp01(lbp_energy),
        }
    except Exception as e:
        log.warning("LBP feature extraction failed: %s", e)
        return {
            "lbp_variance_r1": 0.5, "lbp_variance_r2": 0.5,
            "lbp_uniform_ratio_r1": 0.5, "lbp_uniform_ratio_r2": 0.5,
            "lbp_entropy_r1": 0.5, "lbp_entropy_r2": 0.5,
            "lbp_dominant_pattern_r1": 0.5,
            "local_binary_pattern_energy": 0.5,
        }


# ---------------------------------------------------------------------------
# v7 Edge Density Features
# ---------------------------------------------------------------------------

def _extract_edge_features(
    image: Image.Image,
    center: Image.Image,
    grayscale: Image.Image,
) -> dict[str, float]:
    """
    Extract edge density and gradient features.

    Edge density correlates with vascular structure visibility.
    Anemic conjunctiva tends to have lower edge density due to
    reduced contrast between vessels and tissue.
    """
    try:
        gray = image.resize((64, 64)).convert("L")
        gray_center = center.resize((32, 32)).convert("L")

        # Sobel gradient magnitude
        sobel_x = gray.filter(_SOBEL_X)
        sobel_y = gray.filter(_SOBEL_Y)
        sx_pixels = list(sobel_x.getdata())
        sy_pixels = list(sobel_y.getdata())

        # Gradient magnitude
        grad_magnitudes = [
            math.sqrt((sx / 255.0) ** 2 + (sy / 255.0) ** 2)
            for sx, sy in zip(sx_pixels, sy_pixels)
        ]
        gradient_magnitude_mean = sum(grad_magnitudes) / len(grad_magnitudes)
        gradient_magnitude_std = (
            sum((g - gradient_magnitude_mean) ** 2 for g in grad_magnitudes)
            / len(grad_magnitudes)
        ) ** 0.5

        # Sobel energy
        sobel_energy = sum(g ** 2 for g in grad_magnitudes) / len(grad_magnitudes)

        # Edge density: fraction of pixels above edge threshold
        edge_threshold = 0.12
        edge_pixels_count = sum(1 for g in grad_magnitudes if g > edge_threshold)
        edge_density = edge_pixels_count / len(grad_magnitudes)

        # Center edge density
        cx_pixels = list(gray_center.filter(_SOBEL_X).getdata())
        cy_pixels = list(gray_center.filter(_SOBEL_Y).getdata())
        center_grads = [
            math.sqrt((cx / 255.0) ** 2 + (cy / 255.0) ** 2)
            for cx, cy in zip(cx_pixels, cy_pixels)
        ]
        edge_density_center = sum(1 for g in center_grads if g > edge_threshold) / len(center_grads)

        # Edge orientation entropy: diversity of edge directions
        orientations = []
        for sx, sy in zip(sx_pixels, sy_pixels):
            if abs(sx) > 20 or abs(sy) > 20:  # significant edge
                angle = math.atan2(sy, sx)
                orientations.append(angle)
        if orientations:
            # Bin orientations into 8 bins
            bins = [0] * 8
            for angle in orientations:
                bin_idx = int((angle + math.pi) / (2 * math.pi) * 8) % 8
                bins[bin_idx] += 1
            total_orient = sum(bins)
            probs = [b / total_orient for b in bins if b > 0]
            edge_orientation_entropy = -sum(p * math.log2(p) for p in probs)
            edge_orientation_entropy = edge_orientation_entropy / 3.0  # normalize (max = log2(8) = 3)
        else:
            edge_orientation_entropy = 0.0

        # Canny-like edge density: use multiple thresholds
        canny_high = sum(1 for g in grad_magnitudes if g > 0.20) / len(grad_magnitudes)
        canny_low = sum(1 for g in grad_magnitudes if g > 0.08) / len(grad_magnitudes)
        canny_edge_density = (canny_high + canny_low) / 2.0

        return {
            "edge_density": _clamp01(edge_density),
            "edge_density_center": _clamp01(edge_density_center),
            "edge_orientation_entropy": _clamp01(edge_orientation_entropy),
            "gradient_magnitude_mean": _clamp01(gradient_magnitude_mean),
            "gradient_magnitude_std": _clamp01(gradient_magnitude_std * 5.0),
            "canny_edge_density": _clamp01(canny_edge_density),
            "sobel_energy": _clamp01(sobel_energy * 5.0),
        }
    except Exception as e:
        log.warning("Edge feature extraction failed: %s", e)
        return {
            "edge_density": 0.5, "edge_density_center": 0.5,
            "edge_orientation_entropy": 0.5,
            "gradient_magnitude_mean": 0.5, "gradient_magnitude_std": 0.5,
            "canny_edge_density": 0.5, "sobel_energy": 0.5,
        }


# ---------------------------------------------------------------------------
# v7 Symmetry Features
# ---------------------------------------------------------------------------

def _extract_symmetry_features(image: Image.Image, grayscale: Image.Image) -> dict[str, float]:
    """
    Extract symmetry features.

    Healthy conjunctiva tends to be approximately symmetric.
    Asymmetry can indicate poor framing, occlusion, or pathology.
    """
    try:
        w, h = image.size

        # Horizontal symmetry (left-right mirror)
        rgb_pixels = list(image.resize((64, 64)).getdata())
        sym_w, sym_h = 64, 64

        def _compute_symmetry(pixels: list, img_w: int, img_h: int, axis: str) -> float:
            """Compute symmetry score along given axis."""
            total_diff = 0
            count = 0
            for y in range(img_h):
                for x in range(img_w // 2):
                    if axis == "horizontal":
                        left_idx = y * img_w + x
                        right_idx = y * img_w + (img_w - 1 - x)
                    else:  # vertical
                        left_idx = y * img_w + x
                        right_idx = (img_h - 1 - y) * img_w + x
                    if left_idx < len(pixels) and right_idx < len(pixels):
                        total_diff += abs(pixels[left_idx] - pixels[right_idx])
                        count += 1
            if count == 0:
                return 0.5
            avg_diff = total_diff / count / 255.0
            return 1.0 - min(avg_diff * 3.0, 1.0)  # 1.0 = perfect symmetry

        # RGB symmetry
        horizontal_symmetry_rgb = _compute_symmetry(rgb_pixels, sym_w, sym_h, "horizontal")

        # L* channel symmetry (luminance)
        l_pixels = list(grayscale.resize((64, 64)).getdata())
        horizontal_symmetry_l = _compute_symmetry(l_pixels, sym_w, sym_h, "horizontal")

        # Vertical symmetry
        vertical_symmetry_rgb = _compute_symmetry(rgb_pixels, sym_w, sym_h, "vertical")

        # Radial symmetry: compare quadrants
        half_w, half_h = sym_w // 2, sym_h // 2
        quadrants = []
        for qy in range(2):
            for qx in range(2):
                quad_vals = []
                for y in range(qy * half_h, (qy + 1) * half_h):
                    for x in range(qx * half_w, (qx + 1) * half_w):
                        idx = y * sym_w + x
                        if idx < len(l_pixels):
                            quad_vals.append(l_pixels[idx])
                if quad_vals:
                    quadrants.append(sum(quad_vals) / len(quad_vals))

        if len(quadrants) == 4:
            # Radial symmetry: how similar are opposite quadrants?
            diag_diff_1 = abs(quadrants[0] - quadrants[3]) / 255.0
            diag_diff_2 = abs(quadrants[1] - quadrants[2]) / 255.0
            radial_symmetry = 1.0 - min((diag_diff_1 + diag_diff_2) / 2.0 * 4.0, 1.0)
        else:
            radial_symmetry = 0.5

        return {
            "horizontal_symmetry_rgb": _clamp01(horizontal_symmetry_rgb),
            "horizontal_symmetry_l": _clamp01(horizontal_symmetry_l),
            "vertical_symmetry_rgb": _clamp01(vertical_symmetry_rgb),
            "radial_symmetry": _clamp01(radial_symmetry),
        }
    except Exception as e:
        log.warning("Symmetry feature extraction failed: %s", e)
        return {
            "horizontal_symmetry_rgb": 0.5,
            "horizontal_symmetry_l": 0.5,
            "vertical_symmetry_rgb": 0.5,
            "radial_symmetry": 0.5,
        }


# ---------------------------------------------------------------------------
# v7 Vascular Pattern Features
# ---------------------------------------------------------------------------

def _extract_vascular_features(
    image: Image.Image,
    center: Image.Image,
    grayscale: Image.Image,
) -> dict[str, float]:
    """
    Extract vascular pattern features.

    Blood vessels in conjunctiva are key indicators of anemia.
    Anemic tissue shows reduced vessel visibility, altered color,
    and decreased branching complexity.
    """
    try:
        gray = image.resize((64, 64)).convert("L")
        w, h = gray.size

        # Vessel detection: use inverted red channel as vessel proxy
        # Blood vessels appear darker in grayscale and more red in RGB
        rgb = image.resize((64, 64))
        r, g, b = rgb.split()
        r_pixels = list(r.getdata())
        g_pixels = list(g.getdata())
        b_pixels = list(b.getdata())
        gray_pixels = list(gray.getdata())

        # Vessel contrast: red channel intensity relative to surroundings
        red_mean = sum(r_pixels) / max(len(r_pixels), 1)
        vessel_contrast_ratio = 0.5
        if red_mean > 0:
            vessel_contrast_ratio = sum(
                abs(rp - red_mean) for rp in r_pixels
            ) / (red_mean * len(r_pixels))
            vessel_contrast_ratio = min(vessel_contrast_ratio * 3.0, 1.0)

        # Vessel color ratio: proportion of pixels with strong red signal
        vessel_color_pixels = sum(
            1 for rp, gp in zip(r_pixels, g_pixels)
            if rp > gp * 1.15  # red dominant
        )
        vessel_color_ratio = vessel_color_pixels / max(len(r_pixels), 1)

        # Microvessel density: fine-scale edge density (radius=1)
        fine_edges = gray.filter(_EDGE_KERNEL)
        fine_edge_pixels = list(fine_edges.getdata())
        microvessel_threshold = 100
        microvessel_count = sum(1 for p in fine_edge_pixels if p > microvessel_threshold or p < 255 - microvessel_threshold)
        microvessel_density = microvessel_count / (len(fine_edge_pixels) * 2)

        # Large vessel density: coarse-scale structure (Gaussian blur + edge)
        coarse = gray.filter(ImageFilter.GaussianBlur(radius=2.0))
        coarse_edges = coarse.filter(_EDGE_KERNEL)
        coarse_edge_pixels = list(coarse_edges.getdata())
        large_vessel_count = sum(1 for p in coarse_edge_pixels if p > microvessel_threshold or p < 255 - microvessel_threshold)
        large_vessel_density = large_vessel_count / (len(coarse_edge_pixels) * 2)

        # Vascular density: combined measure
        vascular_density = (microvessel_density * 0.6 + large_vessel_density * 0.4)

        # Vessel branching proxy: complexity of edge patterns
        # Higher LBP uniform ratio => more structured (branching) patterns
        branching = _compute_branching_proxy(fine_edges, w, h)

        # Vessel tortuosity: direction change in edges
        tortuosity = _compute_tortuosity_proxy(gray)

        return {
            "vascular_density": _clamp01(vascular_density),
            "vascular_branching": _clamp01(branching),
            "vascular_tortuosity": _clamp01(tortuosity),
            "vessel_contrast_ratio": _clamp01(vessel_contrast_ratio),
            "vessel_color_ratio": _clamp01(vessel_color_ratio),
            "microvessel_density": _clamp01(microvessel_density),
            "large_vessel_density": _clamp01(large_vessel_density),
        }
    except Exception as e:
        log.warning("Vascular feature extraction failed: %s", e)
        return {
            "vascular_density": 0.5,
            "vascular_branching": 0.5,
            "vascular_tortuosity": 0.5,
            "vessel_contrast_ratio": 0.5,
            "vessel_color_ratio": 0.5,
            "microvessel_density": 0.5,
            "large_vessel_density": 0.5,
        }


def _compute_branching_proxy(edges: Image.Image, w: int, h: int) -> float:
    """
    Proxy for vessel branching: count of edge junction-like patterns.
    Uses local variance of edge pixels as a proxy for branching complexity.
    """
    try:
        pixels = list(edges.getdata())
        # Sample local 3x3 variance at edge pixels
        variances = []
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                idx = y * w + x
                if pixels[idx] > 140 or pixels[idx] < 115:  # edge pixel
                    neighborhood = [
                        pixels[(y + dy) * w + (x + dx)]
                        for dy in [-1, 0, 1]
                        for dx in [-1, 0, 1]
                    ]
                    local_mean = sum(neighborhood) / 9
                    local_var = sum((p - local_mean) ** 2 for p in neighborhood) / 9
                    variances.append(local_var)
        if not variances:
            return 0.5
        # High local variance => complex branching
        avg_var = sum(variances) / len(variances)
        return min(avg_var / 2000.0, 1.0)
    except Exception:
        return 0.5


def _compute_tortuosity_proxy(gray: Image.Image) -> float:
    """
    Proxy for vessel tortuosity: how much edge directions change locally.
    Higher tortuosity => more winding vessels.
    """
    try:
        sobel_x = gray.filter(_SOBEL_X)
        sobel_y = gray.filter(_SOBEL_Y)
        sx = list(sobel_x.getdata())
        sy = list(sobel_y.getdata())

        # Compute orientation changes
        angles = []
        for i in range(len(sx)):
            if abs(sx[i]) > 15 or abs(sy[i]) > 15:
                angle = math.atan2(sy[i], sx[i])
                angles.append(angle)

        if len(angles) < 3:
            return 0.5

        # Measure angular changes between adjacent edge pixels
        angle_changes = []
        for i in range(1, min(len(angles), 200)):
            diff = abs(angles[i] - angles[i - 1])
            if diff > math.pi:
                diff = 2 * math.pi - diff
            angle_changes.append(diff)

        if not angle_changes:
            return 0.5

        avg_change = sum(angle_changes) / len(angle_changes)
        # Normalize: max expected change ~ pi/2
        return min(avg_change / (math.pi / 2), 1.0)
    except Exception:
        return 0.5


# ---------------------------------------------------------------------------
# Feature normalization
# ---------------------------------------------------------------------------

class FeatureNormalizer:
    """
    Normalizes features to [0, 1] range using configurable statistics.
    Supports min-max, z-score, and robust (median/IQR) normalization.
    """

    def __init__(
        self,
        method: str = "minmax",
        feature_stats: dict[str, dict[str, float]] | None = None,
    ):
        self.method = method
        self.feature_stats = feature_stats or {}

    def normalize(self, features: dict[str, float]) -> dict[str, float]:
        """Normalize features using configured method and statistics."""
        result = {}
        for name, value in features.items():
            if name in self.feature_stats:
                stats = self.feature_stats[name]
                if self.method == "minmax":
                    min_val = stats.get("min", 0.0)
                    max_val = stats.get("max", 1.0)
                    result[name] = (value - min_val) / max(max_val - min_val, 1e-6)
                elif self.method == "zscore":
                    mean_val = stats.get("mean", 0.0)
                    std_val = stats.get("std", 1.0)
                    result[name] = (value - mean_val) / max(std_val, 1e-6)
                elif self.method == "robust":
                    median = stats.get("median", 0.0)
                    iqr = stats.get("iqr", 1.0)
                    result[name] = (value - median) / max(iqr, 1e-6)
            else:
                result[name] = _clamp01(value)
        return result

    def fit(self, feature_data: list[dict[str, float]]) -> None:
        """Compute normalization statistics from data."""
        if not feature_data:
            return

        all_names = feature_data[0].keys()
        for name in all_names:
            values = [d[name] for d in feature_data if name in d]
            if not values:
                continue

            if self.method == "minmax":
                self.feature_stats[name] = {
                    "min": min(values),
                    "max": max(values),
                }
            elif self.method == "zscore":
                m = sum(values) / len(values)
                s = (sum((v - m) ** 2 for v in values) / len(values)) ** 0.5
                self.feature_stats[name] = {"mean": m, "std": max(s, 1e-6)}
            elif self.method == "robust":
                sorted_vals = sorted(values)
                n = len(sorted_vals)
                median = sorted_vals[n // 2]
                q1 = sorted_vals[n // 4]
                q3 = sorted_vals[3 * n // 4]
                self.feature_stats[name] = {"median": median, "iqr": max(q3 - q1, 1e-6)}


# ---------------------------------------------------------------------------
# Clinical feature extractors
# ---------------------------------------------------------------------------

def extract_ultimate_clinical_features(
    image: Image.Image,
    quality: QualityAssessment | None = None,
    *,
    age: int | None = None,
    sex: str = "not_specified",
) -> dict[str, float]:
    base = extract_eye_features(image)

    red_mean = float(base.get("center_mean_r", base.get("mean_r", 0.0))) * 255.0
    green_mean = float(base.get("center_mean_g", base.get("mean_g", 0.0))) * 255.0
    blue_mean = float(base.get("center_mean_b", base.get("mean_b", 0.0))) * 255.0
    red_std = float(base.get("center_std_r", base.get("std_r", 0.0))) * 255.0
    green_std = float(base.get("center_std_g", base.get("std_g", 0.0))) * 255.0
    blue_std = float(base.get("center_std_b", base.get("std_b", 0.0))) * 255.0

    pallor_intensity = _clamp01(
        0.5 - float(base.get("center_cpi", 0.35))
    )
    pallor_gradient = _clamp01(
        (-float(base.get("pallor_gradient", 0.0))) * 2.4
    )

    red_green_ratio = red_mean / max(green_mean, 1e-6)
    red_blue_ratio = red_mean / max(blue_mean, 1e-6)
    green_blue_ratio = green_mean / max(blue_mean, 1e-6)
    color_variance = float((red_std ** 2 + green_std ** 2 + blue_std ** 2) / 3.0)

    pallor_color_index = (
        (float(base.get("pallor_score", 0.0)) * 0.20)
        + ((pallor_intensity - 0.14) * 0.35)
        + ((pallor_gradient - 0.11) * 0.25)
        + ((1.0 - red_green_ratio) * 0.15)
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

    # Use vascular features if available (v7)
    vessel_visibility = _clamp01(
        (float(base.get("center_red_green_gap", 0.0)) + 0.05) * 4.8
        + (float(base.get("image_sharpness", 0.5)) * 0.30 if "image_sharpness" in base else
           _clamp01(quality_blur_score / 180.0) * 0.30)
        - (glare_risk * 0.18)
        - (shadow_risk * 0.12)
    )

    # Enhanced vessel density using v7 features when available
    v7_vessel_density = base.get("vascular_density")
    if v7_vessel_density is not None:
        vessel_density = _clamp01(
            (v7_vessel_density * 0.5)
            + (vessel_visibility * 0.35)
            + (float(base.get("rgb_entropy", 0.0)) * 0.15)
        )
    else:
        vessel_density = _clamp01(
            (vessel_visibility * 0.72)
            + (float(base.get("rgb_entropy", 0.0)) * 0.18)
            + ((1.0 - float(base.get("texture_smoothness", 0.5))) * 0.10)
        )

    vessel_color_intensity = _clamp01(
        (float(base.get("redness_ratio", 0.0)) - 0.25) * 4.2
    )

    anemia_severity_score = (
        ((pallor_intensity - 0.14) * 0.55)
        + (pallor_color_index * 0.45)
        + (((1.0 - vessel_visibility) - 0.20) * 0.20)
    )
    clinical_pallor_score = _clamp01(
        0.12
        + (anemia_severity_score * 0.55)
        + (pallor_gradient * 0.20)
        + ((1.0 - vessel_density) * 0.10)
        + ((1.0 - vessel_color_intensity) * 0.08)
    )

    lighting_uniformity = _clamp01(
        (quality_lighting_score * 0.65)
        + ((1.0 - glare_risk) * 0.15)
        + ((1.0 - shadow_risk) * 0.20)
    )

    image_sharpness = _clamp01(quality_blur_score / 180.0)
    texture_contrast = _clamp01(float(base.get("center_contrast", base.get("contrast", 0.0))) * 2.8)
    texture_entropy = float(base.get("rgb_entropy", 0.0))
    texture_smoothness = _clamp01(
        1.0 - ((texture_contrast * 0.55) + (image_sharpness * 0.25))
    )
    noise_level = max(
        0.0,
        ((color_variance / 3000.0) * 0.20)
        + ((1.0 - image_sharpness) * 0.22)
        + ((1.0 - lighting_uniformity) * 0.22)
        + (abs(float(base.get("spectral_tilt_rb", 0.0))) * 0.15)
    )

    age_scale = 0.5 if age is None else _clamp01((float(age) - 12.0) / 58.0)
    age_pallor_interaction = age_scale * clinical_pallor_score

    sex_weight = {
        "female": 1.0,
        "male": 0.9,
        "other": 0.95,
        "not_specified": 0.95,
    }.get(str(sex).strip().lower(), 0.95)
    gender_color_interaction = sex_weight * red_green_ratio

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


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

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
    Low std -> uniform redness (healthy); high std -> patchy pallor.
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
    return min(std / 0.15, 1.0)


def _edge_cpi(image: Image.Image) -> float:
    """CPI computed on the peripheral ring (outer 25% border) of the image."""
    w, h = image.size
    mx, my = w // 4, h // 4
    strips = [
        image.crop((0, 0, w, my)),
        image.crop((0, h - my, w, h)),
        image.crop((0, my, mx, h - my)),
        image.crop((w - mx, my, w, h - my)),
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
    hue_channel = hsv.split()[0]
    stat = ImageStat.Stat(hue_channel)
    hue_mean = stat.mean[0] / 255.0
    hue_std = stat.stddev[0] / 255.0
    return hue_mean, hue_std


def _ycbcr_cb_mean(image: Image.Image) -> float:
    """
    v6: YCbCr Cb (blue-difference) channel mean normalised to [0, 1].
    """
    try:
        ycbcr = image.resize((64, 64)).convert("YCbCr")
        cb_channel = ycbcr.split()[1]
        return ImageStat.Stat(cb_channel).mean[0] / 255.0
    except Exception:
        return 0.5


def _luminance_entropy(image: Image.Image) -> float:
    """
    v6: Shannon entropy of the luminance histogram.
    """
    gray = image.resize((64, 64)).convert("L")
    hist = gray.histogram()
    total = float(sum(hist) or 1)
    entropy = 0.0
    for count in hist:
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    return entropy / 8.0


def _inter_quadrant_cpi_gradient(image: Image.Image) -> float:
    """
    v6: Maximum CPI difference between any two of the 4 quadrants.
    """
    w, h = image.size
    hw, hh = w // 2, h // 2
    quadrants = [
        image.crop((0, 0, hw, hh)),
        image.crop((hw, 0, w, hh)),
        image.crop((0, hh, hw, h)),
        image.crop((hw, hh, w, h)),
    ]
    cpis = []
    for q in quadrants:
        stat = ImageStat.Stat(q)
        r, g, b = [v / 255.0 for v in stat.mean]
        denom = (r + g + b) or 1e-6
        cpis.append(r / denom)
    gradient = max(cpis) - min(cpis)
    return min(gradient / 0.20, 1.0)


def _lbp_uniformity_proxy(image: Image.Image, center: Image.Image) -> float:
    """
    v6: Ratio of center Laplacian variance to full-image Laplacian variance.
    """
    edge_var_full = ImageStat.Stat(image.convert("L").filter(_EDGE_KERNEL)).var[0]
    edge_var_center = ImageStat.Stat(center.convert("L").filter(_EDGE_KERNEL)).var[0]
    if edge_var_full < 1e-6:
        return 0.5
    ratio = edge_var_center / edge_var_full
    return min(ratio, 2.0) / 2.0


def _compute_entropy(image: Image.Image) -> float:
    """Compute normalized Shannon entropy of pixel intensity distribution."""
    hist = image.histogram()
    total = float(sum(hist) or 1)
    entropy = 0.0
    for count in hist:
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    return entropy / 8.0


# ---------------------------------------------------------------------------
# numpy import for ensemble_v2 compatibility (used in clinical extractors)
# ---------------------------------------------------------------------------
try:
    import numpy as np
except ImportError:
    np = None  # type: ignore


# ---------------------------------------------------------------------------
# v8+ Preprocessing integration and optimized feature extraction
# ---------------------------------------------------------------------------

def extract_features_with_preprocessing(
    image: Image.Image,
    *,
    apply_advanced_preprocessing: bool = True,
    preprocessing_config: dict | None = None,
    apply_lighting_norm: bool = True,
    lighting_norm_strength: float = 1.0,
) -> tuple[dict[str, float], dict[str, float]]:
    """
    Extract features with optional advanced preprocessing pipeline.

    This is the enhanced entry point that chains:
    1. Advanced preprocessing (CLAHE, denoise, rotation correction, gamma)
    2. Lighting normalization (existing)
    3. Feature extraction (existing)

    Parameters
    ----------
    image : PIL.Image — RGB input
    apply_advanced_preprocessing : Whether to run the advanced pipeline
    preprocessing_config : Optional config dict for the advanced preprocessor
    apply_lighting_norm : Whether to apply existing lighting normalization
    lighting_norm_strength : Strength of lighting normalization

    Returns
    -------
    (feature_map, preprocessing_metrics)
        feature_map: Standard feature dictionary
        preprocessing_metrics: Diagnostic metrics from preprocessing
    """
    preprocessing_metrics: dict[str, float] = {}
    working_image = image

    if apply_advanced_preprocessing:
        from app.ml.advanced_preprocessing import (
            AdvancedPreprocessor,
            PreprocessingConfig,
        )

        # Build config from dict or use defaults
        if preprocessing_config is not None:
            cfg = PreprocessingConfig(
                denoise_enabled=preprocessing_config.get("denoise_enabled", True),
                denoise_strength=preprocessing_config.get("denoise_strength", 0.5),
                clahe_enabled=preprocessing_config.get("clahe_enabled", True),
                clahe_clip_limit=preprocessing_config.get("clahe_clip_limit", 3.0),
                gamma_correction_enabled=preprocessing_config.get("gamma_correction_enabled", True),
                gamma_auto=preprocessing_config.get("gamma_auto", True),
                color_cast_correction=preprocessing_config.get("color_cast_correction", True),
                rotation_correction_enabled=preprocessing_config.get("rotation_correction_enabled", True),
            )
        else:
            cfg = PreprocessingConfig()

        preprocessor = AdvancedPreprocessor(cfg)
        working_image, report = preprocessor.process(image)

        # Capture preprocessing metrics
        preprocessing_metrics = {
            "preprocessing_time_ms": report.processing_time_ms,
            "clahe_gain": report.clahe_gain,
            "gamma_computed": report.gamma_computed,
            "brightness_before": report.brightness_before,
            "brightness_after": report.brightness_after,
            "contrast_before": report.contrast_before,
            "contrast_after": report.contrast_after,
            "noise_level_before": report.noise_level_before,
            "noise_level_after": report.noise_level_after,
            "rotation_applied": float(report.rotation_applied),
        }

    # Run standard feature extraction on preprocessed image
    feature_map = extract_eye_features(
        working_image,
        apply_lighting_norm=apply_lighting_norm,
        lighting_norm_strength=lighting_norm_strength,
    )

    # Merge preprocessing metrics
    feature_map.update({
        f"preproc_{k}": v for k, v in preprocessing_metrics.items()
    })

    return feature_map, preprocessing_metrics


def vectorize_features_fast(
    feature_map: dict[str, float],
    feature_names: list[str],
    default_value: float = 0.0,
) -> list[float]:
    """
    Optimized feature vectorization with O(1) lookups.

    Faster than the original vectorize_features for repeated calls
    by avoiding repeated dict key checks.
    """
    return [feature_map.get(name, default_value) for name in feature_names]


def compute_feature_statistics(
    feature_maps: list[dict[str, float]],
    feature_names: list[str] | None = None,
) -> dict[str, dict[str, float]]:
    """
    Compute mean and std statistics for a list of feature maps.

    Used for feature typicality computation in confidence scoring.

    Parameters
    ----------
    feature_maps : List of feature dictionaries
    feature_names : Optional list of feature names to compute stats for

    Returns
    -------
    Dict of {feature_name: {"mean": float, "std": float}}
    """
    if not feature_maps:
        return {}

    if feature_names is None:
        feature_names = list(feature_maps[0].keys())

    stats: dict[str, dict[str, float]] = {}

    for feat_name in feature_names:
        values = [fm.get(feat_name, 0.0) for fm in feature_maps]
        if values:
            mean_val = sum(values) / len(values)
            variance = sum((v - mean_val) ** 2 for v in values) / len(values)
            std_val = variance ** 0.5
            stats[feat_name] = {"mean": mean_val, "std": max(std_val, 1e-6)}
        else:
            stats[feat_name] = {"mean": 0.0, "std": 1.0}

    return stats
