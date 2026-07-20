from __future__ import annotations

from datetime import date
from typing import Any

from app.common.const import CLAIM_TYPE_DOCUMENT_REQUIREMENTS
from app.common.utils import normalize_claim_type
from app.enums import RiskLevel
from app.risk import RiskRegistry, RiskResult, RiskRule
from app.graph.state import ClaimGraphState


def _document_type(document: Any) -> str:
    return str(
        document.normalized_document_type
        or (document.normalized_payload or {}).get("document_type")
        or document.document_type
    ).lower()


def _extract_invoice_fields(document: Any) -> dict[str, Any]:
    normalized_payload = document.normalized_payload or {}
    if isinstance(normalized_payload, dict):
        extracted_fields = normalized_payload.get("extracted_fields")
        if isinstance(extracted_fields, dict):
            return extracted_fields
    extracted_fields = document.extracted_fields or {}
    return extracted_fields if isinstance(extracted_fields, dict) else {}


class MetadataRiskRule:
    def evaluate(self, state: ClaimGraphState, registry: RiskRegistry) -> None:
        if not state.claim_documents:
            registry.register(
                RiskResult(
                    30,
                    "No claim documents were loaded for risk analysis",
                    "missing_claim_documents",
                )
            )
        if not state.claim_description:
            registry.register(
                RiskResult(10, "Claim description is missing", "missing_claim_description")
            )
        if state.claim_amount is None:
            registry.register(RiskResult(10, "Claim amount is missing", "missing_claim_amount"))


class DocumentCompletenessRule:
    def evaluate(self, state: ClaimGraphState, registry: RiskRegistry) -> None:
        required_docs = CLAIM_TYPE_DOCUMENT_REQUIREMENTS.get(normalize_claim_type(state.claim_type), [])
        seen_docs = {_document_type(doc) for doc in state.claim_documents}

        for required_doc in required_docs:
            if required_doc not in seen_docs:
                registry.register(
                    RiskResult(
                        20,
                        f"Missing required document: {required_doc}",
                        f"missing_required_document:{required_doc}",
                    )
                )


class DocumentProcessingRule:
    def evaluate(self, state: ClaimGraphState, registry: RiskRegistry) -> None:
        for document in state.claim_documents:
            document_id = document.document_id
            status = str(document.status).lower()

            if str(document.ocr_status).lower() == "failed":
                registry.register(
                    RiskResult(
                        35,
                        f"OCR failed for document {document_id}",
                        f"document_ocr_failed:{document_id}",
                    )
                )

            if status == "ocr_completed":
                if not document.document_text:
                    registry.register(
                        RiskResult(
                            25,
                            f"Missing extracted text for document {document_id}",
                            f"missing_document_text:{document_id}",
                        )
                    )
                if not document.normalized_payload:
                    registry.register(
                        RiskResult(
                            20,
                            f"Missing normalized payload for document {document_id}",
                            f"missing_normalized_payload:{document_id}",
                        )
                    )

            quality = document.quality_assessment or {}
            if isinstance(quality, dict) and quality.get("review_recommended"):
                registry.register(
                    RiskResult(
                        15,
                        f"Document quality review recommended for {document_id}",
                        f"low_quality_document:{document_id}",
                    )
                )

            if document.normalized_confidence is not None and document.normalized_confidence < 0.7:
                registry.register(
                    RiskResult(
                        15,
                        f"Low normalized confidence for document {document_id}",
                        f"low_confidence_document:{document_id}",
                    )
                )


class InvoiceDeepAnalysisRule:
    def evaluate(self, state: ClaimGraphState, registry: RiskRegistry) -> None:
        for document in state.claim_documents:
            if _document_type(document) != "invoice":
                continue

            fields = _extract_invoice_fields(document)
            vendor_name = fields.get("vendor_name") or fields.get("repairer_name")
            invoice_date = fields.get("invoice_date")

            if fields.get("invoice_amount") in (None, "", 0):
                registry.register(
                    RiskResult(
                        20,
                        f"Missing invoice amount for document {document.document_id}",
                        f"missing_invoice_amount:{document.document_id}",
                    )
                )
            if not vendor_name:
                registry.register(
                    RiskResult(
                        15,
                        f"Missing invoice vendor for document {document.document_id}",
                        f"missing_invoice_vendor:{document.document_id}",
                    )
                )
            if not fields.get("currency"):
                registry.notes.append(f"invoice_currency_missing:{document.document_id}")

            self._validate_dates(state, document, invoice_date, registry)

    def _validate_dates(
        self,
        state: ClaimGraphState,
        document: Any,
        invoice_date: Any,
        registry: RiskRegistry,
    ) -> None:
        if not (state.incident_date and invoice_date):
            return

        try:
            incident = date.fromisoformat(state.incident_date)
            invoice = date.fromisoformat(str(invoice_date))
        except ValueError:
            registry.register(
                RiskResult(
                    30,
                    f"Invalid invoice or incident date on document {document.document_id}",
                    f"invalid_invoice_or_incident_date:{document.document_id}",
                )
            )
            return

        if invoice > incident:
            registry.register(
                RiskResult(
                    35,
                    f"Invoice date {invoice_date} is after incident date {state.incident_date}",
                    f"invoice_after_incident:{document.document_id}",
                )
            )


class RiskAnalysisEngine:
    def __init__(self, rules: list[RiskRule] | None = None) -> None:
        self._rules = rules or [
            MetadataRiskRule(),
            DocumentCompletenessRule(),
            DocumentProcessingRule(),
            InvoiceDeepAnalysisRule(),
        ]

    @staticmethod
    def _determine_risk_level(score: int) -> RiskLevel:
        if score >= 70:
            return RiskLevel.HIGH
        if score >= 40:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def execute(self, state: ClaimGraphState) -> dict[str, Any]:
        registry = RiskRegistry(
            errors=list(state.errors),
            notes=list(state.notes),
        )

        for rule in self._rules:
            rule.evaluate(state, registry)

        risk_level = self._determine_risk_level(registry.risk_score)
        requires_review = bool(state.hitl_required or risk_level == RiskLevel.HIGH or registry.errors)

        registry.notes.append(
            "Risk analysis recommends human review before payment routing."
            if requires_review
            else "Risk analysis completed without review blockers."
        )

        required_documents = CLAIM_TYPE_DOCUMENT_REQUIREMENTS.get(normalize_claim_type(state.claim_type), [])
        observed_documents = [_document_type(document) for document in state.claim_documents]

        return {
            "current_step": "risk_analysis",
            "risk_score": min(registry.risk_score, 100),
            "risk_level": risk_level.value,
            "risk_factors": registry.risk_factors,
            "requires_human_review": requires_review,
            "hitl_required": requires_review,
            "errors": registry.errors,
            "notes": registry.notes,
            "required_documents": required_documents,
            "observed_documents": observed_documents,
            "completed_steps": [
                *state.completed_steps,
                "process_claim",
                "validate_claim_context",
                "analyse_risk",
            ],
        }


async def analyse_risk(state: ClaimGraphState) -> dict[str, Any]:
    return RiskAnalysisEngine().execute(state)
