from __future__ import annotations

import base64
from io import BytesIO

from PIL import Image

from app.schemas import RoiPreview
from app.services.conjunctiva_roi import RoiExtractionResult


def build_roi_preview_payload(roi_result: RoiExtractionResult) -> RoiPreview | None:
    original = roi_result.image
    enhanced = roi_result.enhanced_image or original
    if original is None or enhanced is None:
        return None

    return RoiPreview(
        source=roi_result.source,
        extracted=roi_result.extracted,
        extraction_confidence=float(roi_result.confidence),
        original_data_url=_image_to_data_url(original),
        enhanced_data_url=_image_to_data_url(enhanced),
        preview_sharpness=float(roi_result.preview_sharpness),
        preview_contrast=float(roi_result.preview_contrast),
        preview_tone_balance=float(roi_result.preview_tone_balance),
        enhancement_summary=roi_result.enhancement_summary,
    )


def _image_to_data_url(image: Image.Image, *, max_width: int = 420, quality: int = 82) -> str:
    preview = image.convert("RGB")
    if preview.width > max_width:
        scale = max_width / max(preview.width, 1)
        preview = preview.resize(
            (max_width, max(1, int(preview.height * scale))),
            Image.Resampling.LANCZOS,
        )

    buffer = BytesIO()
    preview.save(buffer, format="JPEG", quality=quality, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"
