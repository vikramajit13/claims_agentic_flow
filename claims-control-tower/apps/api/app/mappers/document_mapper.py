from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.schemas.document import ClaimDocumentState


def _read_value(document: Any, key: str, default: Any = None) -> Any:
    if isinstance(document, Mapping):
        return document.get(key, default)
    return getattr(document, key, default)


def _enum_value(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return getattr(value, "value", value)


def _as_document_type(document: Any) -> str:
    document_type = _read_value(document, "document_type")
    if document_type:
        return str(_enum_value(document_type))

    classification = _read_value(document, "document_classification")
    if isinstance(classification, Mapping):
        candidate = classification.get("document_type") or classification.get("type")
        if candidate:
            return str(candidate)

    file_name = _read_value(document, "file_name")
    if file_name:
        return str(file_name)

    return "unknown"


def _as_document_url(document: Any) -> str:
    s3_uri = _read_value(document, "s3_uri")
    if s3_uri:
        return str(s3_uri)

    bucket = _read_value(document, "s3_bucket")
    key = _read_value(document, "s3_key")
    if bucket and key:
        return f"s3://{bucket}/{key}"

    return ""


def map_claim_document_response(document: Any) -> ClaimDocumentState:
    document_text = _read_value(document, "normalized_text") or _read_value(document, "ocr_text")
    uploaded_at = _read_value(document, "created_at") or _read_value(document, "uploaded_at") or ""

    return ClaimDocumentState(
        document_id=int(_read_value(document, "id") or _read_value(document, "document_id")),
        document_type=_as_document_type(document),
        document_url=_as_document_url(document),
        uploaded_at=str(uploaded_at),
        status=str(_enum_value(_read_value(document, "upload_status"), default="unknown")),
        document_text=document_text,
        ocr_status=str(_enum_value(_read_value(document, "ocr_status"), default="unknown")),
        ocr_error=_read_value(document, "ocr_error"),
    )


def map_claim_documents_response(documents: list[Any] | tuple[Any, ...] | None) -> list[ClaimDocumentState]:
    if not documents:
        return []
    return [map_claim_document_response(document) for document in documents]
