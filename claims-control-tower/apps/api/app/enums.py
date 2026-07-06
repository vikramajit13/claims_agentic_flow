from enum import StrEnum


class ClaimStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    READY_FOR_GRAPH = "ready_for_graph"
    WAITING_FOR_DOCUMENTS = "waiting_for_documents"
    WAITING_FOR_HUMAN = "waiting_for_human"


class DocumentStatus(StrEnum):
    PENDING_UPLOAD = "pending_upload"
    UPLOADED = "uploaded"
    OCR_QUEUED = "ocr_queued"
    OCR_COMPLETED = "ocr_completed"


class OcrStatus(StrEnum):
    NOT_REQUESTED = "not_requested"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStatus(StrEnum):
    CREATED = "created"
    READY_FOR_GRAPH = "ready_for_graph"
    WAITING_FOR_HUMAN = "waiting_for_human"
    WAITING_FOR_DOCUMENTS = "waiting_for_documents"


class WorkflowStep(StrEnum):
    CREATED = "created"
    DOCUMENT_COLLECTION = "document_collection"
    OCR_ENRICHMENT = "ocr_enrichment"
    GRAPH_BOOTSTRAP = "graph_bootstrap"
    HUMAN_REVIEW = "human_review"
