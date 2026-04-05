"""
ROI confidence scoring and blend strategy for AnemiaLens.

Instead of a hard switch between ROI and full-frame predictions,
we score the ROI extraction quality and blend proportionally.

Confidence tiers:
  >= 0.70  → use ROI prediction (high confidence)
  0.40-0.70 → blend ROI + full-frame
  < 0.40   → use full-frame with a small uncertainty penalty
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageStat


class RoiConfidenceScorer:
    """
    Scores the quality of a conjunctiva ROI crop on a 0-1 scale.

    Metrics:
    - Red channel dominance (conjunctiva should be reddish)
    - Saturation balance (tissue should not look greyed out)
    - Aspect ratio validity (wide strip, not square)
    - Size relative to a reference (too small/too large = unreliable)
    - Texture sharpness (blurry ROI = bad extraction)
    - Center-tissue bias (core should look more conjunctival than the edges)
    """

    # Minimum acceptable ROI dimensions
    MIN_WIDTH = 80
    MIN_HEIGHT = 30

    def score(self, roi: Image.Image, original: Image.Image | None = None) -> float:
        """
        Returns a confidence score in [0, 1].
        Higher = better ROI extraction.
        """
        width, height = roi.size
        if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
            return 0.0

        scores: list[float] = []

        # 1. Red channel dominance
        scores.append(self._red_dominance(roi))

        # 2. Tissue saturation
        scores.append(self._saturation_score(roi))

        # 3. Aspect ratio (conjunctiva strip is wide)
        scores.append(self._aspect_ratio_score(width, height))

        # 4. Size relative to original (if available)
        if original is not None:
            scores.append(self._relative_size_score(roi, original))
        else:
            scores.append(0.6)  # neutral if no reference

        # 5. Texture sharpness
        scores.append(self._sharpness_score(roi))

        # 6. Center tissue bias
        scores.append(self._center_bias_score(roi))

        weights = np.array([0.24, 0.16, 0.18, 0.14, 0.14, 0.14], dtype=np.float32)
        return float(np.clip(np.average(scores, weights=weights), 0.0, 1.0))

    def _red_dominance(self, roi: Image.Image) -> float:
        """R channel should be notably higher than G and B in conjunctiva."""
        rgb = roi.convert("RGB")
        stat = ImageStat.Stat(rgb)
        r, g, b = stat.mean
        total = r + g + b + 1e-6
        # Healthy conjunctiva: R/total ~ 0.40-0.55
        r_ratio = r / total
        # Score peaks at 0.42, falls off outside [0.30, 0.65]
        score = 1.0 - abs(r_ratio - 0.42) / 0.25
        return float(np.clip(score, 0.0, 1.0))

    def _aspect_ratio_score(self, width: int, height: int) -> float:
        """Conjunctiva strip should have aspect ratio >= 1.8."""
        ratio = width / max(height, 1)
        if ratio >= 2.5:
            return 1.0
        if ratio >= 1.8:
            return 0.85
        if ratio >= 1.2:
            return 0.55
        return 0.2

    def _relative_size_score(self, roi: Image.Image, original: Image.Image) -> float:
        """ROI should be 3-35% of the original image area."""
        roi_area = roi.size[0] * roi.size[1]
        orig_area = original.size[0] * original.size[1] + 1
        ratio = roi_area / orig_area
        if 0.03 <= ratio <= 0.35:
            return 1.0
        if ratio < 0.03:
            return float(np.clip(ratio / 0.03, 0.0, 1.0))
        # Too large → probably grabbed the whole image
        return float(np.clip(1.0 - (ratio - 0.35) / 0.35, 0.0, 1.0))

    def _saturation_score(self, roi: Image.Image) -> float:
        rgb = np.asarray(roi.convert("RGB"), dtype=np.float32) / 255.0
        channel_max = rgb.max(axis=2)
        channel_min = rgb.min(axis=2)
        denom = np.where(channel_max > 1e-6, channel_max, 1.0)
        saturation = float(np.mean((channel_max - channel_min) / denom))
        if 0.12 <= saturation <= 0.42:
            return 1.0
        if saturation < 0.12:
            return float(np.clip(saturation / 0.12, 0.0, 1.0))
        return float(np.clip(1.0 - ((saturation - 0.42) / 0.4), 0.0, 1.0))

    def _sharpness_score(self, roi: Image.Image) -> float:
        """Laplacian variance as a proxy for sharpness."""
        from PIL import ImageFilter
        gray = roi.convert("L").resize((64, 32))
        kernel = ImageFilter.Kernel(
            (3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1, offset=0
        )
        lap_var = ImageStat.Stat(gray.filter(kernel)).var[0]
        # Typical sharp ROI: var > 50; blurry: var < 10
        return float(np.clip(lap_var / 80.0, 0.0, 1.0))

    def _center_bias_score(self, roi: Image.Image) -> float:
        width, height = roi.size
        if width < 12 or height < 12:
            return 0.0

        rgb = np.asarray(roi.convert("RGB"), dtype=np.float32)
        center = rgb[
            int(height * 0.2): int(height * 0.8),
            int(width * 0.18): int(width * 0.82),
        ]
        outer_mask = np.ones((height, width), dtype=bool)
        outer_mask[
            int(height * 0.2): int(height * 0.8),
            int(width * 0.18): int(width * 0.82),
        ] = False
        outer = rgb[outer_mask]

        if center.size == 0 or outer.size == 0:
            return 0.0

        center_gap = float(np.mean(center[:, :, 0] - center[:, :, 1]))
        outer_gap = float(np.mean(outer[:, 0] - outer[:, 1]))
        delta = center_gap - outer_gap
        if delta >= 16.0:
            return 1.0
        if delta <= 0.0:
            return 0.0
        return float(np.clip(delta / 16.0, 0.0, 1.0))


def blend_roi_fullframe(
    roi_pred: dict[str, float],
    fullframe_pred: dict[str, float],
    roi_confidence: float,
) -> dict[str, float]:
    """
    Blend ROI and full-frame predictions based on ROI confidence.

    Tiers:
      confidence >= 0.70 → 90% ROI, 10% full-frame
      confidence 0.40-0.70 → linear blend
      confidence < 0.40 → 10% ROI, 90% full-frame + uncertainty penalty
    """
    if roi_confidence >= 0.70:
        roi_w = 0.90
    elif roi_confidence >= 0.40:
        # Linear interpolation: 0.40 → 0.30 weight, 0.70 → 0.90 weight
        t = (roi_confidence - 0.40) / 0.30
        roi_w = 0.30 + t * 0.60
    else:
        roi_w = 0.10

    ff_w = 1.0 - roi_w

    blended_risk = roi_w * roi_pred["anemia_risk"] + ff_w * fullframe_pred["anemia_risk"]
    blended_hb = roi_w * roi_pred["predicted_hemoglobin"] + ff_w * fullframe_pred["predicted_hemoglobin"]

    # Uncertainty: weighted blend + penalty for low ROI confidence
    roi_unc = roi_pred.get("uncertainty", 0.4)
    ff_unc = fullframe_pred.get("uncertainty", 0.4)
    base_uncertainty = roi_w * roi_unc + ff_w * ff_unc

    # Low confidence penalty: up to +0.15 extra uncertainty
    confidence_penalty = max(0.0, (0.40 - roi_confidence) / 0.40) * 0.15
    blended_uncertainty = float(np.clip(base_uncertainty + confidence_penalty, 0.04, 0.95))

    return {
        "anemia_risk": float(np.clip(blended_risk, 0.0, 1.0)),
        "predicted_hemoglobin": float(blended_hb),
        "uncertainty": blended_uncertainty,
        "decision_threshold": roi_pred.get("decision_threshold", 0.5),
        "roi_confidence": roi_confidence,
        "roi_weight": roi_w,
    }
