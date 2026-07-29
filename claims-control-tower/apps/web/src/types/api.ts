export type ClaimStatus =
  | "draft"
  | "submitted"
  | "ready_for_graph"
  | "waiting_for_documents"
  | "waiting_for_human";

export type DocumentStatus = "pending_upload" | "uploaded" | "ocr_queued" | "ocr_completed";
export type OcrStatus = "not_requested" | "pending" | "completed" | "failed";
export type WorkflowStatus = "created" | "ready_for_graph" | "waiting_for_human" | "waiting_for_documents";
export type WorkflowStep =
  | "created"
  | "document_collection"
  | "ocr_enrichment"
  | "graph_bootstrap"
  | "human_review";

export type ClaimCreateRequest = {
  claim_number: string;
  customer_id: number;
  claim_type: string;
  description?: string | null;
  incident_date?: string | null;
  claim_amount?: number | null;
};

export type DocumentPresignRequest = {
  file_name: string;
  content_type?: string | null;
  run_ocr?: boolean;
};

export type DocumentPresignResponse = {
  document_id: number;
  upload_url: string;
  upload_method: string;
  upload_headers: Record<string, string>;
  s3_uri: string;
  s3_bucket: string;
  s3_key: string;
  expires_in_seconds: number;
};

export type WorkflowStartRequest = {
  hitl_required?: boolean | null;
  notes?: string[];
};

export type ClaimDocumentResponse = {
  id: number;
  file_name: string;
  content_type?: string | null;
  s3_uri: string;
  s3_bucket: string;
  s3_key: string;
  upload_status: DocumentStatus;
  ocr_requested: boolean;
  ocr_status: OcrStatus;
  ocr_job_id?: string | null;
  ocr_error?: string | null;
  ocr_text?: string | null;
  normalized_text?: string | null;
  validation_results?: Record<string, unknown> | null;
  document_classification?: Record<string, unknown> | null;
  extracted_fields?: Record<string, unknown> | null;
  quality_assessment?: Record<string, unknown> | null;
  normalized_payload?: Record<string, unknown> | null;
  normalized_document_type?: string | null;
  normalized_confidence?: number | null;
  normalized_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type ClaimResponse = {
  id: number;
  claim_number: string;
  customer_id: number;
  claim_type: string;
  description?: string | null;
  incident_date?: string | null;
  claim_amount?: number | null;
  status: ClaimStatus;
  documents: ClaimDocumentResponse[];
  created_at: string;
  updated_at: string;
};

export type WorkflowRunResponse = {
  id: number;
  claim_id: number;
  status: WorkflowStatus;
  current_step: WorkflowStep;
  hitl_required: boolean;
  next_action: string;
  notes: string[];
  created_at: string;
  updated_at: string;
};
