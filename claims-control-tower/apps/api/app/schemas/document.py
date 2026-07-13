from pydantic import BaseModel, Field


class ClaimDocumentState(BaseModel):
    document_id: int
    document_type: str
    document_url: str
    uploaded_at: str
    status: str
    document_text: str | None = None
    ocr_status: str | None = None
    ocr_error: str | None = None