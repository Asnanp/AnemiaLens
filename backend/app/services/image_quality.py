from __future__ import annotations

from PIL import Image

from app.config import settings
from app.ml.features import edge_blur_baseline, extract_eye_features, load_image_bytes, framing_score
from app.schemas import QualityAssessment, QualityIssue
from app.services.conjunctiva_roi import ConjunctivaRoiExtractor


class ImageQualityService:
    def __init__(self) -> None:
        self.roi_extractor = ConjunctivaRoiExtractor()
        self.blur_block_threshold = max(settings.min_blur_score - 5.0, 0.0)
        self.blur_warning_threshold = max(settings.min_blur_score + 30.0, self.blur_block_threshold)
        self.framing_block_threshold = settings.min_framing + 0.45
        self.framing_warning_threshold = settings.min_framing + 0.75

        self.roi_brightness_block_low = settings.min_brightness * 0.25
        self.roi_brightness_warning_low = settings.min_brightness * 0.40
        self.roi_brightness_block_high = min(0.99, settings.max_brightness - 0.10)
        self.roi_brightness_warning_high = min(0.99, settings.max_brightness - 0.20)
        self.roi_contrast_block = settings.min_contrast * 0.75
        self.roi_contrast_warning = settings.min_contrast + 0.02

        self.full_brightness_block_low = settings.min_brightness * 0.20
        self.full_brightness_warning_low = settings.min_brightness * 0.35
        self.full_brightness_block_high = min(0.99, settings.max_brightness - 0.34)
        self.full_brightness_warning_high = min(0.99, settings.max_brightness - 0.50)
        self.full_contrast_block = settings.min_contrast
        self.full_contrast_warning = settings.min_contrast + 0.04

    def evaluate(self, image_bytes: bytes) -> tuple[QualityAssessment, Image.Image]:
        raw_image = load_image_bytes(image_bytes)
        roi = self.roi_extractor.extract(raw_image)
        image = roi.image
        feature_map = extract_eye_features(image)
        blur_score = float(feature_map["blur_score"])
        brightness_score = float(feature_map["brightness"])
        contrast_score = float(feature_map["contrast"])
        center_brightness = float(feature_map["center_brightness"])
        center_contrast = float(feature_map["center_contrast"])
        bright_region_ratio = float(feature_map["hist_bright"])
        highlight_ratio = float(feature_map["hist_highlight"])
        frame_score = float(framing_score(feature_map))
        edge_blur = edge_blur_baseline(image)

        issues: list[QualityIssue] = []

        if image.size[0] < 110 or image.size[1] < 40:
            issues.append(
                QualityIssue(
                    code="resolution_too_low",
                    severity="blocking",
                    title="Image is too small",
                    message="Move closer to the eye and keep the eyelid area sharp and centered.",
                )
            )
        elif roi.extracted and (raw_image.size[0] >= image.size[0] * 1.6 or raw_image.size[1] >= image.size[1] * 1.6):
            issues.append(
                QualityIssue(
                    code="roi_cropped",
                    severity="warning",
                    title="Lower eyelid region detected",
                    message="The app auto-focused on the exposed inner eyelid to match the screening model.",
                )
            )

        eye_visibility_score = self._eye_visibility_score(feature_map, frame_score, roi_extracted=roi.extracted)
        visibility_threshold = 0.4 if roi.extracted else 0.52
        if eye_visibility_score < visibility_threshold:
            issues.append(
                QualityIssue(
                    code="eye_not_visible",
                    severity="blocking",
                    title="Eye is not clearly visible",
                    message="Retake with one eye filling the frame and the inner lower eyelid clearly visible.",
                )
            )

        issues = self._soften_salvageable_roi_blocks(
            issues,
            roi_extracted=roi.extracted,
            blur_score=blur_score,
            brightness_score=brightness_score,
            contrast_score=contrast_score,
            framing_score=frame_score,
        )

        if any(issue.code == "eye_not_visible" and issue.severity == "blocking" for issue in issues):
            assessment = QualityAssessment(
                passed=False,
                blur_score=round(blur_score, 2),
                brightness_score=round(brightness_score, 3),
                contrast_score=round(contrast_score, 3),
                framing_score=round(frame_score, 3),
                issues=issues,
            )
            return assessment, image

        if blur_score < self.blur_block_threshold:
            issues.append(
                QualityIssue(
                    code="blur_detected",
                    severity="blocking",
                    title="Image looks blurry",
                    message="Hold steady, tap to focus, and retake the photo without motion.",
                )
            )
        elif blur_score < self.blur_warning_threshold:
            issues.append(
                QualityIssue(
                    code="blur_detected",
                    severity="warning",
                    title="Image is slightly soft",
                    message="The model can still try, but a sharper image will improve confidence.",
                )
            )

        if roi.extracted:
            lighting_blocked = (
                (
                    brightness_score < self.roi_brightness_block_low
                    and center_brightness < (self.roi_brightness_block_low + 0.03)
                )
                or (highlight_ratio > 0.12)
                or (
                    brightness_score > self.roi_brightness_block_high
                    and center_brightness > (self.roi_brightness_block_high + 0.04)
                    and highlight_ratio > 0.04
                )
                or (
                    contrast_score < self.roi_contrast_block
                    and center_contrast < (self.roi_contrast_block + 0.02)
                )
            )
            lighting_warn = (
                brightness_score < self.roi_brightness_warning_low
                or brightness_score > self.roi_brightness_warning_high
                or center_brightness > (self.roi_brightness_warning_high + 0.06)
                or contrast_score < self.roi_contrast_warning
                or center_contrast < (self.roi_contrast_block + 0.02)
                or highlight_ratio > 0.03
            )
        else:
            lighting_blocked = (
                (
                    brightness_score < self.full_brightness_block_low
                    and center_brightness < (self.full_brightness_block_low + 0.03)
                )
                or (highlight_ratio > 0.08)
                or (
                    brightness_score > self.full_brightness_block_high
                    and center_brightness > (self.full_brightness_block_high + 0.04)
                    and bright_region_ratio > 0.28
                )
                or (
                    contrast_score < self.full_contrast_block
                    and center_contrast < (self.full_contrast_block + 0.02)
                )
            )
            lighting_warn = (
                brightness_score < self.full_brightness_warning_low
                or brightness_score > self.full_brightness_warning_high
                or center_brightness > (self.full_brightness_warning_high + 0.06)
                or contrast_score < self.full_contrast_warning
                or center_contrast < self.full_contrast_warning
                or bright_region_ratio > 0.24
                or highlight_ratio > 0.02
            )
        if lighting_blocked:
            issues.append(
                QualityIssue(
                    code="poor_lighting",
                    severity="blocking",
                    title="Lighting is not usable",
                    message="Use bright, even light without flash glare or heavy shadows.",
                )
            )
        elif lighting_warn:
            issues.append(
                QualityIssue(
                    code="poor_lighting",
                    severity="warning",
                    title="Lighting could be better",
                    message="The model can try this image, but even light will improve reliability.",
                )
            )

        if (
            frame_score < self.framing_block_threshold
            or feature_map["center_blur_score"] < max(blur_score, edge_blur) * 0.55
        ):
            issues.append(
                QualityIssue(
                    code="bad_framing",
                    severity="blocking",
                    title="Eye is not framed clearly",
                    message="Fill the frame with one eye and keep the inner eyelid area visible.",
                )
            )
        elif (
            frame_score < self.framing_warning_threshold
            or feature_map["center_blur_score"] < max(blur_score, edge_blur) * 0.68
        ):
            issues.append(
                QualityIssue(
                    code="bad_framing",
                    severity="warning",
                    title="Eye framing is a little loose",
                    message="The model can try this image, but centering the inner eyelid will help.",
                )
            )

        issues = self._soften_salvageable_roi_blocks(
            issues,
            roi_extracted=roi.extracted,
            blur_score=blur_score,
            brightness_score=brightness_score,
            contrast_score=contrast_score,
            framing_score=frame_score,
        )

        blocking_issues = [issue for issue in issues if issue.severity == "blocking"]

        assessment = QualityAssessment(
            passed=not blocking_issues,
            blur_score=round(blur_score, 2),
            brightness_score=round(brightness_score, 3),
            contrast_score=round(contrast_score, 3),
            framing_score=round(frame_score, 3),
            issues=issues,
        )
        return assessment, image

    def _soften_salvageable_roi_blocks(
        self,
        issues: list[QualityIssue],
        *,
        roi_extracted: bool,
        blur_score: float,
        brightness_score: float,
        contrast_score: float,
        framing_score: float,
    ) -> list[QualityIssue]:
        if not self._should_salvage_roi_capture(
            issues,
            roi_extracted=roi_extracted,
            blur_score=blur_score,
            brightness_score=brightness_score,
            contrast_score=contrast_score,
            framing_score=framing_score,
        ):
            return issues

        softened: list[QualityIssue] = []
        for issue in issues:
            if issue.severity == "blocking" and issue.code in {"bad_framing", "eye_not_visible"}:
                softened.append(
                    issue.model_copy(
                        update={
                            "severity": "warning",
                            "message": (
                                "The eyelid crop still looks usable, so screening can continue, "
                                "but a tighter retake should improve reliability."
                            ),
                        }
                    )
                )
            else:
                softened.append(issue)
        return softened

    def allows_raw_frame_rescue(self, assessment: QualityAssessment) -> bool:
        blocking_codes = {issue.code for issue in assessment.issues if issue.severity == "blocking"}
        return bool(blocking_codes) and (
            blocking_codes.issubset({"bad_framing", "eye_not_visible"})
            or blocking_codes == {"poor_lighting"}
        )

    def build_raw_frame_rescue_assessment(self, assessment: QualityAssessment) -> QualityAssessment:
        if not self.allows_raw_frame_rescue(assessment):
            return assessment

        rescued_issues: list[QualityIssue] = []
        for issue in assessment.issues:
            if issue.severity == "blocking" and issue.code in {"bad_framing", "eye_not_visible", "poor_lighting"}:
                rescued_issues.append(
                    issue.model_copy(
                        update={
                            "severity": "warning",
                            "message": (
                                "The ROI crop was weak, so the app fell back to the full eye frame. "
                                "Screening can continue, but a cleaner retake is still recommended."
                            ),
                        }
                    )
                )
            else:
                rescued_issues.append(issue)

        return assessment.model_copy(update={"passed": True, "issues": rescued_issues})

    def _should_salvage_roi_capture(
        self,
        issues: list[QualityIssue],
        *,
        roi_extracted: bool,
        blur_score: float,
        brightness_score: float,
        contrast_score: float,
        framing_score: float,
    ) -> bool:
        if not roi_extracted:
            return False

        blocking_codes = {issue.code for issue in issues if issue.severity == "blocking"}
        if not blocking_codes or not blocking_codes.issubset({"bad_framing", "eye_not_visible"}):
            return False

        standard_salvage = (
            blur_score >= 180.0
            and framing_score >= 2.0
            and contrast_score >= 0.12
            and 0.22 <= brightness_score <= 0.58
        )
        if standard_salvage:
            return True

        clarity_exception = (
            blocking_codes == {"bad_framing"}
            and blur_score >= 300.0
            and framing_score >= 1.75
            and contrast_score >= 0.16
            and 0.30 <= brightness_score <= 0.58
        )
        return clarity_exception

    def _eye_visibility_score(
        self,
        feature_map: dict[str, float],
        frame_score: float,
        roi_extracted: bool = False,
    ) -> float:
        if roi_extracted:
            structure_signal = self._scaled(frame_score, 1.0, 2.1)
            focus_signal = self._scaled(feature_map["blur_score"], 85.0, 260.0)
            texture_signal = self._scaled(feature_map["contrast"], 0.08, 0.22)
            tissue_signal = min(
                self._range_score(feature_map["red_green_gap"], 0.02, 0.2),
                self._range_score(feature_map["center_red_green_gap"], 0.02, 0.22),
                self._range_score(feature_map["saturation"], 0.03, 0.28),
            )
            score = (
                structure_signal * 0.25
                + focus_signal * 0.24
                + texture_signal * 0.18
                + tissue_signal * 0.33
            )
            if tissue_signal < 0.22:
                score *= 0.45
            if texture_signal < 0.12:
                score *= 0.8
            return max(0.0, min(1.0, score))

        structure_signal = self._scaled(frame_score, 1.05, 2.1)
        focus_signal = min(
            self._scaled(feature_map["center_blur_score"], 55.0, 220.0),
            self._scaled(
                feature_map["center_blur_score"] / max(feature_map["blur_score"], 1e-6),
                0.58,
                1.55,
            ),
        )
        texture_signal = min(
            self._scaled(feature_map["contrast"], 0.08, 0.22),
            self._scaled(feature_map["center_contrast"], 0.08, 0.2),
        )
        dark_signal = self._range_score(feature_map["hist_dark"], 0.16, 0.92)
        tissue_signal = min(
            self._range_score(feature_map["center_red_green_gap"], -0.01, 0.18),
            self._range_score(feature_map["center_saturation"], 0.035, 0.24),
            self._range_score(feature_map["saturation"], 0.03, 0.24),
        )

        score = (
            structure_signal * 0.28
            + focus_signal * 0.22
            + texture_signal * 0.2
            + dark_signal * 0.12
            + tissue_signal * 0.18
        )
        if dark_signal < 0.2:
            score *= 0.4
        if texture_signal < 0.2:
            score *= 0.6
        return max(0.0, min(1.0, score))

    def _scaled(self, value: float, low: float, high: float) -> float:
        if value <= low:
            return 0.0
        if value >= high:
            return 1.0
        return (value - low) / max(high - low, 1e-6)

    def _range_score(self, value: float, low: float, high: float) -> float:
        if low <= value <= high:
            return 1.0

        slack = max((high - low) * 0.75, 1e-6)
        if value < low:
            return max(0.0, 1.0 - ((low - value) / slack))
        return max(0.0, 1.0 - ((value - high) / slack))
