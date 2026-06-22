from __future__ import annotations

from app.enums import OcrStatus
from app.observability import traceable


class OCRService:
    @traceable(name="mock_ocr_extract", run_type="tool")
    def extract_from_s3(self, *, s3_uri: str, file_name: str) -> tuple[OcrStatus, str]:
        text = (
            f"Mock OCR extracted text from {s3_uri}. "
            f"This placeholder can be swapped for Textract or another OCR provider. "
            f"Document: {file_name}"
        )
        return OcrStatus.COMPLETED, text
