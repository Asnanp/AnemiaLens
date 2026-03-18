from __future__ import annotations

from io import BytesIO
from pathlib import Path
from statistics import mean

from PIL import Image, ImageFilter, ImageOps, ImageStat


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

_EDGE_KERNEL = ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1, offset=0)


def load_image_bytes(image_bytes: bytes) -> Image.Image:
    with Image.open(BytesIO(image_bytes)) as image:
        return ImageOps.exif_transpose(image).convert("RGB")


def load_image_path(path: str | Path) -> Image.Image:
    with Image.open(path) as image:
        return ImageOps.exif_transpose(image).convert("RGB")


def extract_eye_features(image: Image.Image) -> dict[str, float]:
    width, height = image.size
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
    }


def vectorize_features(feature_map: dict[str, float], names: list[str]) -> list[float]:
    return [float(feature_map[name]) for name in names]


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
