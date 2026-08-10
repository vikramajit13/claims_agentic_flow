from enum import StrEnum
from enum import Enum


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
    GRAPH_EXECUTION = "graph_execution"
    RECOMMEND_NEXT_ACTION = "recommend_next_action"
    HUMAN_REVIEW = "human_review"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class NextWorkflowAction(StrEnum):
    PROCEED_TO_PAYMENT_GUARDRAILS = "PROCEED_TO_PAYMENT_GUARDRAILS"
    CREATE_HUMAN_REVIEW_TASK = "CREATE_HUMAN_REVIEW_TASK"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"
    BLOCK_RECOMMENDED = "BLOCK_RECOMMENDED"
