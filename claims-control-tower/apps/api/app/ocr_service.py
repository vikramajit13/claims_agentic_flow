from __future__ import annotations

from urllib.parse import urlparse

import boto3

from app.enums import OcrStatus
from app.observability import traceable
from app.config import settings
from app.document_intelligence_service import TextractLine, TextractResult


class OCRService:
    def __init__(self) -> None:
        self.client = None if settings.use_mock_ocr else boto3.client("textract", region_name=settings.aws_region)

    @traceable(name="mock_textract_extract", run_type="tool")
    def _mock_extract(self, *, s3_uri: str, file_name: str) -> TextractResult:
        text = (
            f"Mock OCR extracted text from {s3_uri}. "
            f"Document: {file_name}. "
            "Invoice Number: INV-1001. "
            "Invoice Amount: 4200.00. "
            "Amount Due: 4200.00. "
            "Vendor: ABC Repairs. "
            "Policy Number: POL-123. "
            "Claim Reference: CLM-9001. "
            "Invoice Date: 2026-07-01."
        )
        lines = [
            TextractLine(text="Invoice Number: INV-1001", confidence=98.1),
            TextractLine(text="Amount Due: 4200.00", confidence=97.3),
            TextractLine(text="Vendor: ABC Repairs", confidence=96.0),
            TextractLine(text="Invoice Date: 2026-07-01", confidence=95.2),
        ]
        blocks = [
            {"block_type": "LINE", "text": line.text, "confidence": line.confidence}
            for line in lines
        ]
        return TextractResult(raw_text=text, lines=lines, blocks=blocks)

    @traceable(name="textract_extract", run_type="tool")
    def extract_from_s3(self, *, s3_uri: str, file_name: str) -> tuple[OcrStatus, TextractResult]:
        if settings.use_mock_ocr:
            return OcrStatus.COMPLETED, self._mock_extract(s3_uri=s3_uri, file_name=file_name)

        if self.client is None:
            raise RuntimeError("Textract client is not configured.")

        parsed = urlparse(s3_uri)
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        response = self.client.detect_document_text(
            Document={"S3Object": {"Bucket": bucket, "Name": key}}
        )

        lines = []
        blocks = []
        text_parts = []
        for block in response.get("Blocks", []):
            if block.get("BlockType") != "LINE":
                continue
            line_text = block.get("Text", "")
            confidence = float(block.get("Confidence", 0.0))
            lines.append(TextractLine(text=line_text, confidence=confidence))
            blocks.append(
                {
                    "block_type": block.get("BlockType"),
                    "text": line_text,
                    "confidence": confidence,
                }
            )
            text_parts.append(line_text)

        return OcrStatus.COMPLETED, TextractResult(
            raw_text=" ".join(text_parts).strip(),
            lines=lines,
            blocks=blocks,
        )
