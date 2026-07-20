from __future__ import annotations

from datetime import date

from app.common.const import CLAIM_TYPE_DOCUMENT_REQUIREMENTS
from app.common.utils import normalize_claim_type
from app.graph.state import ClaimGraphState


def _document_type(document) -> str:
    return str(
        document.normalized_document_type
        or (document.normalized_payload or {}).get("document_type")
        or document.document_type
    ).lower()


def _extract_invoice_fields(document) -> dict:
    normalized_payload = document.normalized_payload or {}
    if isinstance(normalized_payload, dict):
        extracted_fields = normalized_payload.get("extracted_fields")
        if isinstance(extracted_fields, dict):
            return extracted_fields
    extracted_fields = document.extracted_fields or {}
    return extracted_fields if isinstance(extracted_fields, dict) else {}


async def analyse_risk(state: ClaimGraphState) -> dict:
    notes = list(state.notes)
    errors = list(state.errors)
    required_documents = CLAIM_TYPE_DOCUMENT_REQUIREMENTS.get(normalize_claim_type(state.claim_type), [])
    observed_documents: list[str] = []
    seen_document_types: set[str] = set()
    risk_factors: list[str] = []
    risk_score = 0

    def add_risk(points: int, factor: str, error: str | None = None) -> None:
        nonlocal risk_score
        risk_score += points
        risk_factors.append(factor)
        if error:
            errors.append(error)

    for document in state.claim_documents:
        normalized_document_type = _document_type(document)
        observed_documents.append(normalized_document_type)
        seen_document_types.add(normalized_document_type)

        if str(document.ocr_status).lower() == "failed":
            add_risk(35, f"OCR failed for document {document.document_id}", f"document_ocr_failed:{document.document_id}")

        if str(document.status).lower() == "ocr_completed" and not document.document_text:
            add_risk(
                25,
                f"Missing extracted text for document {document.document_id}",
                f"missing_document_text:{document.document_id}",
            )

        if str(document.status).lower() == "ocr_completed" and not document.normalized_payload:
            add_risk(
                20,
                f"Missing normalized payload for document {document.document_id}",
                f"missing_normalized_payload:{document.document_id}",
            )

        quality_assessment = document.quality_assessment or {}
        if isinstance(quality_assessment, dict) and quality_assessment.get("review_recommended"):
            add_risk(
                15,
                f"Document quality review recommended for {document.document_id}",
                f"low_quality_document:{document.document_id}",
            )

        normalized_confidence = document.normalized_confidence
        if normalized_confidence is not None and normalized_confidence < 0.7:
            add_risk(
                15,
                f"Low normalized confidence for document {document.document_id}",
                f"low_confidence_document:{document.document_id}",
            )

        if normalized_document_type == "invoice":
            extracted_fields = _extract_invoice_fields(document)
            invoice_amount = extracted_fields.get("invoice_amount")
            vendor_name = extracted_fields.get("vendor_name") or extracted_fields.get("repairer_name")
            currency = extracted_fields.get("currency")
            invoice_date = extracted_fields.get("invoice_date")

            if invoice_amount in (None, "", 0):
                add_risk(
                    20,
                    f"Missing invoice amount for document {document.document_id}",
                    f"missing_invoice_amount:{document.document_id}",
                )
            if not vendor_name:
                add_risk(
                    15,
                    f"Missing invoice vendor for document {document.document_id}",
                    f"missing_invoice_vendor:{document.document_id}",
                )
            if not currency:
                notes.append(f"invoice_currency_missing:{document.document_id}")
            if state.incident_date and invoice_date:
                try:
                    incident = date.fromisoformat(state.incident_date)
                    invoice = date.fromisoformat(str(invoice_date))
                    if invoice > incident:
                        add_risk(
                            35,
                            f"Invoice date {invoice_date} is after incident date {state.incident_date}",
                            f"invoice_after_incident:{document.document_id}",
                        )
                except ValueError:
                    add_risk(
                        30,
                        f"Invalid invoice or incident date on document {document.document_id}",
                        f"invalid_invoice_or_incident_date:{document.document_id}",
                    )

    for required_document in required_documents:
        if required_document not in seen_document_types:
            add_risk(
                20,
                f"Missing required document: {required_document}",
                f"missing_required_document:{required_document}",
            )

    if not state.claim_documents:
        add_risk(30, "No claim documents were loaded for risk analysis", "missing_claim_documents")

    if not state.claim_description:
        add_risk(10, "Claim description is missing", "missing_claim_description")

    if state.claim_amount is None:
        add_risk(10, "Claim amount is missing", "missing_claim_amount")

    risk_level = "LOW"
    if risk_score >= 70:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "MEDIUM"

    requires_human_review = bool(state.hitl_required or risk_level == "HIGH" or errors)
    if requires_human_review:
        notes.append("Risk analysis recommends human review before payment routing.")
    else:
        notes.append("Risk analysis completed without review blockers.")

    return {
        "current_step": "risk_analysis",
        "risk_score": min(risk_score, 100),
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "requires_human_review": requires_human_review,
        "hitl_required": requires_human_review,
        "errors": errors,
        "notes": notes,
        "required_documents": required_documents,
        "observed_documents": observed_documents,
        "completed_steps": [
            *state.completed_steps,
            "process_claim",
            "validate_claim_context",
            "analyse_risk",
        ],
    }
