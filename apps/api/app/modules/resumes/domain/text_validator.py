import string
from typing import Any, Dict, Optional

from apps.api.app.core.config import settings


class TextQualityValidator:
    """
    Validates document extraction text quality against configurable threshold settings.
    Distinguishes usable text vs scanned/unreadable documents requiring OCR.
    """

    @classmethod
    def validate_text_quality(
        cls,
        extracted_text: str,
        min_chars: Optional[int] = None,
        max_noise_ratio: Optional[float] = None
    ) -> Dict[str, Any]:
        min_len = min_chars if min_chars is not None else settings.RESUME_MIN_EXTRACTED_TEXT_CHARS
        noise_limit = max_noise_ratio if max_noise_ratio is not None else settings.RESUME_MAX_NON_PRINTABLE_RATIO

        text = (extracted_text or "").strip()

        if len(text) < min_len:
            return {
                "is_usable": False,
                "reason": "INSUFFICIENT_EXTRACTABLE_TEXT",
                "ocr_required": True,
                "details": f"Extracted text length ({len(text)} chars) below minimum threshold ({min_len} chars)"
            }

        # Calculate printable ascii / printable character noise ratio
        printable_count = sum(1 for char in text if char in string.printable)
        total_count = len(text)
        noise_ratio = (total_count - printable_count) / float(total_count)

        if noise_ratio > noise_limit:
            return {
                "is_usable": False,
                "reason": "HIGH_TEXT_NOISE_RATIO",
                "ocr_required": True,
                "details": f"Noise ratio ({noise_ratio:.2%}) exceeds maximum threshold ({noise_limit:.2%})"
            }

        return {
            "is_usable": True,
            "reason": "OK",
            "ocr_required": False,
            "details": "Text quality validation passed"
        }
