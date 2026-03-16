from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image


@dataclass
class RoiExtractionResult:
    image: Image.Image
    extracted: bool


class ConjunctivaRoiExtractor:
    def extract(self, image: Image.Image) -> RoiExtractionResult:
        rgb = image.convert("RGB")
        array = np.asarray(rgb)
        iris = self._detect_iris(array)
        crop: np.ndarray | None = None

        if iris is not None and iris[2] / max(min(array.shape[:2]), 1) < 0.13:
            candidate = self._crop_lower_eyelid(array, iris)
            crop = self._finalize_crop(candidate)

        if crop is None:
            crop = self._fallback_conjunctiva_crop(array)

        if crop is None:
            return RoiExtractionResult(image=rgb, extracted=False)

        return RoiExtractionResult(image=Image.fromarray(crop.astype(np.uint8), mode="RGB"), extracted=True)

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
    ) -> np.ndarray:
        height, width = image.shape[:2]
        center_x, center_y, radius = iris

        left = int(max(0, center_x - (1.95 * radius)))
        right = int(min(width, center_x + (1.95 * radius)))
        top = int(max(0, center_y + (0.16 * radius)))
        bottom = int(min(height, center_y + (1.95 * radius)))
        if right - left < 110 or bottom - top < 40:
            return np.empty((0, 0, 3), dtype=np.uint8)

        return image[top:bottom, left:right].copy()

    def _fallback_conjunctiva_crop(self, image: np.ndarray) -> np.ndarray | None:
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
            if aspect_ratio < 1.1:
                continue

            component_mask = labels == index
            mean_red = float(red_prominence[component_mask].mean()) if np.any(component_mask) else 0.0
            mean_sat = float(hsv[:, :, 1][component_mask].mean()) if np.any(component_mask) else 0.0
            center_x = (x + (box_width / 2.0)) / max(search.shape[1], 1)
            center_y = (y + (box_height / 2.0)) / max(search.shape[0], 1)
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
                return crop

        heuristic = image[
            int(height * 0.42): int(height * 0.78),
            int(width * 0.16): int(width * 0.84),
        ].copy()
        return self._finalize_crop(heuristic)

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
        if refined is not None and refined.size > 0:
            crop = refined

        if crop.shape[0] < 40 or crop.shape[1] < 110:
            return None
        return crop
