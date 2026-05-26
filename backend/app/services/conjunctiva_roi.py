from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageStat

from app.ml.lighting_norm import normalize_illumination
from app.ml.roi_confidence import RoiConfidenceScorer

_roi_scorer = RoiConfidenceScorer()


@dataclass
class RoiExtractionResult:
    image: Image.Image
    extracted: bool
    confidence: float = 0.5  # ROI extraction quality score [0, 1]
    source: str = "full_frame"
    bbox: tuple[int, int, int, int] | None = None
    frame_size: tuple[int, int] | None = None
    enhanced_image: Image.Image | None = None
    preview_sharpness: float = 0.0
    preview_contrast: float = 0.0
    preview_tone_balance: float = 0.0
    enhancement_summary: str = ""


class ConjunctivaRoiExtractor:
    def extract(self, image: Image.Image) -> RoiExtractionResult:
        rgb = image.convert("RGB")
        array = np.asarray(rgb)
        frame_size = (rgb.width, rgb.height)
        iris = self._detect_iris(array)
        crop: np.ndarray | None = None
        bbox: tuple[int, int, int, int] | None = None
        source = "full_frame"

        if iris is not None and iris[2] / max(min(array.shape[:2]), 1) < 0.13:
            candidate, candidate_bbox = self._crop_lower_eyelid(array, iris)
            crop = self._finalize_crop(candidate)
            if crop is None and candidate.size > 0 and candidate.shape[0] >= 120 and candidate.shape[1] >= 220:
                crop = candidate
            if crop is not None:
                source = "iris_guided"
                bbox = candidate_bbox

        if crop is None:
            fallback = self._fallback_conjunctiva_crop(array)
            if fallback is not None:
                crop, bbox = fallback
                source = "heuristic_roi"

        if crop is None:
            enhanced_image, preview_sharpness, preview_contrast, preview_tone_balance = (
                self._build_enhanced_preview(rgb)
            )
            return RoiExtractionResult(
                image=rgb,
                extracted=False,
                confidence=0.0,
                source="full_frame",
                bbox=None,
                frame_size=frame_size,
                enhanced_image=enhanced_image,
                preview_sharpness=preview_sharpness,
                preview_contrast=preview_contrast,
                preview_tone_balance=preview_tone_balance,
                enhancement_summary=(
                    "The system could not isolate the inner eyelid ROI cleanly, so the preview falls back to the "
                    "full frame with gentle lighting cleanup only."
                ),
            )

        roi_image = Image.fromarray(crop.astype(np.uint8), mode="RGB")
        confidence = _roi_scorer.score(roi_image, original=rgb)
        minimum_confidence = 0.66 if source == "heuristic_roi" else 0.56
        if confidence < minimum_confidence:
            enhanced_image, preview_sharpness, preview_contrast, preview_tone_balance = (
                self._build_enhanced_preview(rgb)
            )
            return RoiExtractionResult(
                image=rgb,
                extracted=False,
                confidence=confidence,
                source="roi_rejected",
                bbox=None,
                frame_size=frame_size,
                enhanced_image=enhanced_image,
                preview_sharpness=preview_sharpness,
                preview_contrast=preview_contrast,
                preview_tone_balance=preview_tone_balance,
                enhancement_summary=(
                    "The system found a possible crop, but it did not look enough like the exposed lower inner eyelid "
                    "to trust it for screening."
                ),
            )
        enhanced_image, preview_sharpness, preview_contrast, preview_tone_balance = (
            self._build_enhanced_preview(roi_image)
        )
        return RoiExtractionResult(
            image=roi_image,
            extracted=True,
            confidence=confidence,
            source=source,
            bbox=bbox,
            frame_size=frame_size,
            enhanced_image=enhanced_image,
            preview_sharpness=preview_sharpness,
            preview_contrast=preview_contrast,
            preview_tone_balance=preview_tone_balance,
            enhancement_summary=self._build_enhancement_summary(
                source=source,
                sharpness=preview_sharpness,
                contrast=preview_contrast,
                tone_balance=preview_tone_balance,
            ),
        )

    def _detect_iris(self, image: np.ndarray) -> tuple[float, float, float] | None:
        height, width = image.shape[:2]
        scale = 1.0
        if max(height, width) > 960:
            scale = 960.0 / max(height, width)
            work = cv2.resize(image, (int(width * scale), int(height * scale)))
        else:
            work = image

        gray = cv2.cvtColor(work, cv2.COLOR_RGB2GRAY)
        gray = cv2.GaussianBlur(gray, (9, 9), 2)
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=max(40, min(work.shape[:2]) // 5),
            param1=70,
            param2=22,
            minRadius=max(18, min(work.shape[:2]) // 20),
            maxRadius=max(50, min(work.shape[:2]) // 5),
        )
        if circles is None:
            return None

        best: tuple[float, float, float, float] | None = None
        work_height, work_width = work.shape[:2]
        base_gray = cv2.cvtColor(work, cv2.COLOR_RGB2GRAY)
        for circle in circles[0]:
            x, y, radius = [float(value) for value in circle]
            if not (0.12 <= x / work_width <= 0.88 and 0.25 <= y / work_height <= 0.82):
                continue
            if radius <= 0:
                continue

            mask = np.zeros((work_height, work_width), dtype=np.uint8)
            cv2.circle(mask, (int(x), int(y)), int(radius), 255, -1)
            mean_gray = float(cv2.mean(base_gray, mask=mask)[0])
            centrality = 1.0 - abs((x / work_width) - 0.5) * 0.9 - abs((y / work_height) - 0.58) * 0.8
            score = ((255.0 - mean_gray) / 255.0) + centrality
            if best is None or score > best[0]:
                best = (score, x / scale, y / scale, radius / scale)

        if best is None:
            return None
        return best[1], best[2], best[3]

    def _crop_lower_eyelid(
        self,
        image: np.ndarray,
        iris: tuple[float, float, float],
    ) -> tuple[np.ndarray, tuple[int, int, int, int]]:
        height, width = image.shape[:2]
        center_x, center_y, radius = iris

        left = int(max(0, center_x - (1.95 * radius)))
        right = int(min(width, center_x + (1.95 * radius)))
        top = int(max(0, center_y + (0.16 * radius)))
        bottom = int(min(height, center_y + (1.95 * radius)))
        if right - left < 110 or bottom - top < 40:
            return np.empty((0, 0, 3), dtype=np.uint8), (left, top, 0, 0)

        return image[top:bottom, left:right].copy(), (left, top, right - left, bottom - top)

    def _fallback_conjunctiva_crop(self, image: np.ndarray) -> tuple[np.ndarray, tuple[int, int, int, int]] | None:
        height, width = image.shape[:2]
        if height < 80 or width < 160 or min(height, width) < 700:
            return None

        search_left = int(width * 0.08)
        search_right = int(width * 0.92)
        search_top = int(height * 0.22)
        search_bottom = int(height * 0.88)
        search = image[search_top:search_bottom, search_left:search_right].copy()
        if search.size == 0:
            return None

        gray = cv2.cvtColor(search, cv2.COLOR_RGB2GRAY)
        hsv = cv2.cvtColor(search, cv2.COLOR_RGB2HSV)
        red_prominence = search[:, :, 0].astype(np.int16) - search[:, :, 1].astype(np.int16)

        dynamic_threshold = max(10, int(np.percentile(red_prominence, 72)))
        mask = (
            (red_prominence > dynamic_threshold)
            & (search[:, :, 0] > 70)
            & (hsv[:, :, 1] > 18)
            & (gray > 40)
            & (gray < 245)
        ).astype(np.uint8) * 255

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.dilate(mask, kernel, iterations=1)

        component_count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        best_box: tuple[float, int, int, int, int] | None = None
        search_area = max(search.shape[0] * search.shape[1], 1)
        min_area = max(180, int(search_area * 0.0035))
        for index in range(1, component_count):
            x, y, box_width, box_height, area = [int(value) for value in stats[index]]
            if area < min_area:
                continue
            aspect_ratio = box_width / max(box_height, 1)
            if aspect_ratio < 1.45 or aspect_ratio > 6.2:
                continue

            component_mask = labels == index
            mean_red = float(red_prominence[component_mask].mean()) if np.any(component_mask) else 0.0
            mean_sat = float(hsv[:, :, 1][component_mask].mean()) if np.any(component_mask) else 0.0
            center_x = (x + (box_width / 2.0)) / max(search.shape[1], 1)
            center_y = (y + (box_height / 2.0)) / max(search.shape[0], 1)
            if not (0.18 <= center_x <= 0.82 and 0.28 <= center_y <= 0.74):
                continue
            if mean_red < 14.0 or mean_sat < 24.0:
                continue
            horizontal_bonus = 1.0 - abs(center_x - 0.5) * 1.6
            vertical_bonus = 1.0 - abs(center_y - 0.55) * 1.8
            score = (
                (area / search_area) * 10.0
                + (aspect_ratio * 0.9)
                + (mean_red / 32.0)
                + (mean_sat / 96.0)
                + horizontal_bonus
                + vertical_bonus
            )
            if best_box is None or score > best_box[0]:
                best_box = (score, x, y, box_width, box_height)

        if best_box is not None:
            _, x, y, box_width, box_height = best_box
            pad_x = int(box_width * 0.16) + 10
            pad_y = int(box_height * 0.28) + 8
            left = max(0, x - pad_x)
            top = max(0, y - pad_y)
            right = min(search.shape[1], x + box_width + pad_x)
            bottom = min(search.shape[0], y + box_height + pad_y)
            candidate = search[top:bottom, left:right].copy()
            crop = self._finalize_crop(candidate)
            if crop is not None:
                return crop, (
                    search_left + left,
                    search_top + top,
                    right - left,
                    bottom - top,
                )

        return None

    def _refine_conjunctiva_band(self, crop: np.ndarray) -> np.ndarray | None:
        height, width = crop.shape[:2]
        search = crop[: max(1, int(height * 0.82)), :]
        gray = cv2.cvtColor(search, cv2.COLOR_RGB2GRAY)
        red_prominence = search[:, :, 0].astype(np.int16) - search[:, :, 1].astype(np.int16)
        dynamic_threshold = max(14, int(np.percentile(red_prominence, 68)))
        mask = (
            (red_prominence > dynamic_threshold)
            & (search[:, :, 0] > 90)
            & (gray > 45)
            & (gray < 245)
        ).astype(np.uint8) * 255

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        component_count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        best_box: tuple[float, int, int, int, int] | None = None
        min_area = max(120, int(search.shape[0] * search.shape[1] * 0.005))
        for index in range(1, component_count):
            x, y, box_width, box_height, area = [int(value) for value in stats[index]]
            if area < min_area:
                continue
            aspect_ratio = box_width / max(box_height, 1)
            if aspect_ratio < 1.2:
                continue
            center_y = y + (box_height / 2.0)
            vertical_penalty = abs((center_y / max(search.shape[0], 1)) - 0.55) * 3.0
            score = (area / 1000.0) + aspect_ratio - vertical_penalty
            if best_box is None or score > best_box[0]:
                best_box = (score, x, y, box_width, box_height)

        if best_box is None:
            return None

        _, x, y, box_width, box_height = best_box
        pad_x = int(box_width * 0.1) + 8
        pad_y = int(box_height * 0.25) + 6
        left = max(0, x - pad_x)
        top = max(0, y - pad_y)
        right = min(width, x + box_width + pad_x)
        bottom = min(height, y + box_height + pad_y)
        if right - left < 110 or bottom - top < 40:
            return None
        return crop[top:bottom, left:right].copy()

    def _finalize_crop(self, crop: np.ndarray | None) -> np.ndarray | None:
        if crop is None or crop.size == 0:
            return None

        refined = self._refine_conjunctiva_band(crop)
        if refined is None or refined.size == 0:
            return None
        crop = refined

        if crop.shape[0] < 40 or crop.shape[1] < 110:
            return None
        return crop

    def _build_enhanced_preview(self, image: Image.Image) -> tuple[Image.Image, float, float, float]:
        corrected, _ = normalize_illumination(
            image,
            clahe_strength=1.08,
            grey_world_alpha=0.30,
            return_score=True,
        )
        corrected = Image.blend(corrected, image.convert("RGB"), 0.28)
        corrected = self._rebalance_preview_tone(corrected)
        enhanced = ImageEnhance.Contrast(corrected).enhance(1.08)
        enhanced = ImageEnhance.Color(enhanced).enhance(1.06)
        enhanced = enhanced.filter(ImageFilter.UnsharpMask(radius=1.25, percent=148, threshold=2))
        enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.05)

        gray = image.convert("L")
        enhanced_gray = enhanced.convert("L")
        enhanced_contrast_raw = ImageStat.Stat(enhanced_gray).stddev[0] / 255.0
        enhanced_mean = ImageStat.Stat(enhanced_gray).mean[0] / 255.0

        preview_sharpness = _clamp01((self._edge_variance(enhanced_gray) - 38.0) / 210.0)
        preview_contrast = _clamp01((enhanced_contrast_raw - 0.045) / 0.22)
        preview_tone_balance = _clamp01(1.0 - (abs(enhanced_mean - 0.46) / 0.32))

        # Keep the enhancement stable if the original crop is already very crisp and balanced.
        original_sharpness = _clamp01((self._edge_variance(gray) - 38.0) / 210.0)
        if original_sharpness >= 0.82 and preview_tone_balance >= 0.8:
            return corrected, original_sharpness, preview_contrast, preview_tone_balance

        return enhanced, preview_sharpness, preview_contrast, preview_tone_balance

    def _rebalance_preview_tone(self, image: Image.Image) -> Image.Image:
        array = np.asarray(image.convert("RGB"), dtype=np.float32)
        channel_means = array.mean(axis=(0, 1))
        red_mean, green_mean, blue_mean = [float(value) for value in channel_means]

        cool_bias = _clamp01((blue_mean - red_mean) / 42.0)
        green_bias = _clamp01((green_mean - red_mean) / 52.0)
        warm_lift = 1.0 + (cool_bias * 0.08) + (green_bias * 0.04)
        blue_trim = 1.0 - (cool_bias * 0.10)
        green_trim = 1.0 - (green_bias * 0.05)

        array[:, :, 0] = np.clip(array[:, :, 0] * warm_lift, 0, 255)
        array[:, :, 1] = np.clip(array[:, :, 1] * green_trim, 0, 255)
        array[:, :, 2] = np.clip(array[:, :, 2] * blue_trim, 0, 255)

        # Preserve clinically relevant redness without making the crop look artificially neon.
        red_mask = (array[:, :, 0] > array[:, :, 1] * 1.05) & (array[:, :, 0] > array[:, :, 2] * 1.08)
        array[:, :, 0] = np.where(red_mask, np.clip(array[:, :, 0] * 1.02, 0, 255), array[:, :, 0])
        return Image.fromarray(array.astype(np.uint8), mode="RGB")

    def _build_enhancement_summary(
        self,
        *,
        source: str,
        sharpness: float,
        contrast: float,
        tone_balance: float,
    ) -> str:
        source_text = {
            "iris_guided": "The iris-guided crop isolated the exposed lower inner eyelid.",
            "heuristic_roi": "A heuristic ROI crop isolated the strongest conjunctival band from the frame.",
            "full_frame": "The preview falls back to the full frame because no stable ROI was isolated.",
        }.get(source, "The crop focuses on the exposed inner eyelid region.")

        if sharpness >= 0.78 and contrast >= 0.68 and tone_balance >= 0.72:
            return f"{source_text} Lighting was balanced and vessel detail was sharpened for a cleaner conjunctival preview."
        if tone_balance < 0.5:
            return f"{source_text} The preview corrected uneven exposure, but lighting is still limiting how much conjunctival detail can be recovered."
        if sharpness < 0.45:
            return f"{source_text} Tone was corrected, but blur still limits the amount of recoverable vessel detail."
        return f"{source_text} The preview applies lighting cleanup and gentle local sharpening so the conjunctival tissue is easier to inspect."

    def _edge_variance(self, grayscale: Image.Image) -> float:
        return float(ImageStat.Stat(grayscale.filter(ImageFilter.FIND_EDGES)).var[0])


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
