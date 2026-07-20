from __future__ import annotations

import re
from datetime import datetime, timezone
from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.llm_client import LLMClient
from app.observability import traceable
from app.prompt_loader import load_prompt_artifact, render_prompt_template
from app.schemas.document import (
    DocumentClassificationResult,
    DocumentExtractedFields,
    DocumentQualityAssessment,
    NormalizedDocumentRecord,
)


@dataclass(frozen=True)
class TextractLine:
    text: str
    confidence: float


@dataclass(frozen=True)
class TextractResult:
    raw_text: str
    lines: list[TextractLine]
    blocks: list[dict]


@dataclass(frozen=True)
class DocumentIntelligenceResult:
    raw_text: str
    normalized_text: str
    textract_blocks: list[dict]
    validation_results: dict
    document_classification: dict
    extracted_fields: dict
    quality_assessment: dict


class LLMClassification(BaseModel):
    document_type: str
    confidence: float = Field(ge=0, le=1)
    reason: str


class LLMExtractedFields(BaseModel):
    invoice_number: str | None = None
    invoice_amount: float | None = None
    invoice_date: str | None = None
    vendor_name: str | None = None
    policy_number: str | None = None
    claim_reference: str | None = None


class LLMQualityAssessment(BaseModel):
    quality_level: str
    overall_confidence: float = Field(ge=0, le=1)
    review_recommended: bool
    notes: list[str] = Field(default_factory=list)


class LLMDocumentIntelligencePayload(BaseModel):
    document_classification: LLMClassification
    extracted_fields: LLMExtractedFields
    quality_assessment: LLMQualityAssessment


class FallbackDocumentIntelligenceService:
    @traceable(name="normalize_document_text", run_type="tool")
    def normalize_text(self, raw_text: str) -> tuple[str, dict]:
        normalized = re.sub(r"\s+", " ", raw_text).strip()
        validation_results = {
            "has_text": bool(normalized),
            "character_count": len(normalized),
            "contains_numeric_content": bool(re.search(r"\d", normalized)),
            "contains_currency": bool(re.search(r"\$|\b(?:aud|usd)\b", normalized, flags=re.IGNORECASE)),
        }
        return normalized, validation_results

    @traceable(name="fallback_classify_document", run_type="tool")
    def classify_document(self, *, file_name: str, normalized_text: str) -> dict:
        lowered = f"{file_name} {normalized_text}".lower()
        if any(keyword in lowered for keyword in ("invoice", "repair estimate", "amount due")):
            document_type = "invoice"
            confidence = 0.94
        elif any(keyword in lowered for keyword in ("photo", "damage image", "jpeg", "png")):
            document_type = "photo"
            confidence = 0.83
        elif any(keyword in lowered for keyword in ("police", "report")):
            document_type = "police_report"
            confidence = 0.88
        else:
            document_type = "unclassified"
            confidence = 0.55

        return {
            "document_type": document_type,
            "confidence": confidence,
            "reason": f"Classified using filename and normalized text markers for {document_type}.",
        }

    @traceable(name="fallback_extract_claim_fields", run_type="tool")
    def extract_claim_fields(self, *, normalized_text: str, document_type: str) -> dict:
        fields: dict[str, str | float | None] = {
            "invoice_number": None,
            "invoice_amount": None,
            "invoice_date": None,
            "vendor_name": None,
            "policy_number": None,
            "claim_reference": None,
        }

        invoice_number_match = re.search(r"(?:invoice(?: number| no\.?)?[:#]?\s*)([A-Z0-9-]+)", normalized_text, re.IGNORECASE)
        amount_match = re.search(r"(?:amount due|total|invoice amount)[:\s$]*([0-9]+(?:\.[0-9]{2})?)", normalized_text, re.IGNORECASE)
        date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", normalized_text)
        vendor_match = re.search(r"(?:vendor|repairer|supplier)[:\s]+([A-Za-z0-9 &.-]+)", normalized_text, re.IGNORECASE)
        policy_match = re.search(r"(?:policy(?: number)?[:#]?\s*)([A-Z0-9-]+)", normalized_text, re.IGNORECASE)
        claim_match = re.search(r"(?:claim(?: reference| number)?[:#]?\s*)([A-Z0-9-]+)", normalized_text, re.IGNORECASE)

        if invoice_number_match:
            fields["invoice_number"] = invoice_number_match.group(1)
        if amount_match:
            fields["invoice_amount"] = float(amount_match.group(1))
        if date_match:
            fields["invoice_date"] = date_match.group(1)
        if vendor_match:
            fields["vendor_name"] = vendor_match.group(1).strip()
        if policy_match:
            fields["policy_number"] = policy_match.group(1)
        if claim_match:
            fields["claim_reference"] = claim_match.group(1)

        return {
            "document_type": document_type,
            "fields": fields,
            "field_count": len([value for value in fields.values() if value not in (None, "")]),
        }

    @traceable(name="fallback_assess_document_quality", run_type="tool")
    def assess_quality(self, *, textract_result: TextractResult, validation_results: dict, extracted_fields: dict) -> dict:
        confidences = [line.confidence for line in textract_result.lines] or [0.0]
        average_confidence = round(sum(confidences) / len(confidences), 2)
        field_count = extracted_fields.get("field_count", 0)

        if not validation_results["has_text"]:
            quality_level = "poor"
        elif average_confidence >= 95 and field_count >= 2:
            quality_level = "high"
        elif average_confidence >= 80:
            quality_level = "medium"
        else:
            quality_level = "low"

        return {
            "average_confidence": average_confidence,
            "quality_level": quality_level,
            "field_extraction_completeness": field_count,
            "review_recommended": quality_level in {"poor", "low"},
        }

    @traceable(name="run_fallback_document_intelligence", run_type="chain")
    def process(
        self,
        *,
        file_name: str,
        textract_result: TextractResult,
        normalized_text: str | None = None,
        validation_results: dict | None = None,
        fallback_reason: str | None = None,
    ) -> DocumentIntelligenceResult:
        normalized_text = normalized_text or self.normalize_text(textract_result.raw_text)[0]
        validation_results = validation_results or self.normalize_text(textract_result.raw_text)[1]
        classification = self.classify_document(file_name=file_name, normalized_text=normalized_text)
        extracted_fields = self.extract_claim_fields(
            normalized_text=normalized_text,
            document_type=classification["document_type"],
        )
        quality_assessment = self.assess_quality(
            textract_result=textract_result,
            validation_results=validation_results,
            extracted_fields=extracted_fields,
        )
        quality_assessment["processing_mode"] = "fallback"
        quality_assessment["fallback_used"] = True
        quality_assessment["fallback_reason"] = fallback_reason or "llm_not_attempted"
        return DocumentIntelligenceResult(
            raw_text=textract_result.raw_text,
            normalized_text=normalized_text,
            textract_blocks=textract_result.blocks,
            validation_results=validation_results,
            document_classification=classification,
            extracted_fields=extracted_fields,
            quality_assessment=quality_assessment,
        )


class LLMDocumentIntelligenceService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def is_enabled(self) -> bool:
        return self.llm_client.enabled

    def _load_system_prompt(self) -> tuple[str, dict]:
        artifact = load_prompt_artifact(
            domain="document_intelligence",
            role="system",
            version=settings.document_intelligence_prompt_version,
        )
        return artifact.body, artifact.metadata

    def _build_user_prompt(self, *, file_name: str, normalized_text: str, textract_result: TextractResult) -> str:
        lines = [{"text": line.text, "confidence": line.confidence} for line in textract_result.lines[:40]]
        artifact = load_prompt_artifact(
            domain="document_intelligence",
            role="user",
            version=settings.document_intelligence_prompt_version,
        )
        return render_prompt_template(
            artifact.body,
            {
                "file_name": file_name,
                "normalized_text": normalized_text,
                "textract_lines": lines,
            },
        )

    @traceable(name="run_llm_document_intelligence", run_type="chain")
    def process(self, *, file_name: str, normalized_text: str, textract_result: TextractResult) -> dict:
        system_prompt, system_metadata = self._load_system_prompt()
        payload = self.llm_client.create_document_intelligence(
            system_prompt=system_prompt,
            user_prompt=self._build_user_prompt(
                file_name=file_name,
                normalized_text=normalized_text,
                textract_result=textract_result,
            ),
        )
        model = LLMDocumentIntelligencePayload.model_validate(payload)
        extracted_fields = model.extracted_fields.model_dump()
        field_count = len([value for value in extracted_fields.values() if value not in (None, "")])
        return {
            "document_classification": model.document_classification.model_dump(),
            "extracted_fields": {
                "document_type": model.document_classification.document_type,
                "fields": extracted_fields,
                "field_count": field_count,
            },
            "quality_assessment": {
                **model.quality_assessment.model_dump(),
                "processing_mode": "llm",
                "fallback_used": False,
                "prompt_name": system_metadata["prompt_name"],
                "prompt_version": system_metadata["prompt_version"],
            },
        }


class DocumentIntelligenceOrchestrator:
    def __init__(
        self,
        *,
        llm_service: LLMDocumentIntelligenceService | None = None,
        fallback_service: FallbackDocumentIntelligenceService | None = None,
    ) -> None:
        self.llm_service = llm_service or LLMDocumentIntelligenceService()
        self.fallback_service = fallback_service or FallbackDocumentIntelligenceService()

    @traceable(name="run_document_intelligence", run_type="chain")
    def process(self, *, file_name: str, textract_result: TextractResult) -> DocumentIntelligenceResult:
        normalized_text, validation_results = self.fallback_service.normalize_text(textract_result.raw_text)

        if not self.llm_service.is_enabled():
            return self.fallback_service.process(
                file_name=file_name,
                textract_result=textract_result,
                normalized_text=normalized_text,
                validation_results=validation_results,
                fallback_reason="llm_not_configured",
            )

        try:
            llm_result = self.llm_service.process(
                file_name=file_name,
                normalized_text=normalized_text,
                textract_result=textract_result,
            )
            overall_confidence = float(llm_result["quality_assessment"]["overall_confidence"])
            if overall_confidence < settings.document_intelligence_min_confidence:
                raise ValueError(f"llm_confidence_below_threshold:{overall_confidence}")

            return DocumentIntelligenceResult(
                raw_text=textract_result.raw_text,
                normalized_text=normalized_text,
                textract_blocks=textract_result.blocks,
                validation_results=validation_results,
                document_classification=llm_result["document_classification"],
                extracted_fields=llm_result["extracted_fields"],
                quality_assessment=llm_result["quality_assessment"],
            )
        except (ValidationError, ValueError, RuntimeError, KeyError) as exc:
            return self.fallback_service.process(
                file_name=file_name,
                textract_result=textract_result,
                normalized_text=normalized_text,
                validation_results=validation_results,
                fallback_reason=str(exc),
            )

    def build_normalized_record(
        self,
        *,
        document_id: int,
        claim_id: int,
        file_name: str,
        content_type: str | None,
        s3_uri: str,
        s3_bucket: str,
        s3_key: str,
        upload_status: str,
        ocr_status: str,
        intelligence_result: DocumentIntelligenceResult,
    ) -> NormalizedDocumentRecord:
        classification = DocumentClassificationResult.model_validate(intelligence_result.document_classification)
        extracted_fields_payload = intelligence_result.extracted_fields.get("fields") or intelligence_result.extracted_fields
        extracted_fields = DocumentExtractedFields.model_validate(extracted_fields_payload)
        raw_quality = dict(intelligence_result.quality_assessment)
        raw_confidence = float(raw_quality.get("overall_confidence", raw_quality.get("average_confidence", 0.0)))
        if raw_confidence > 1:
            raw_confidence = round(raw_confidence / 100, 4)
        quality_payload = {
            "quality_level": raw_quality.get("quality_level", "unknown"),
            "overall_confidence": raw_confidence,
            "review_recommended": bool(raw_quality.get("review_recommended", False)),
            "notes": raw_quality.get("notes", []),
            "processing_mode": raw_quality.get("processing_mode"),
            "fallback_used": bool(raw_quality.get("fallback_used", False)),
            "fallback_reason": raw_quality.get("fallback_reason"),
        }
        quality_assessment = DocumentQualityAssessment.model_validate(quality_payload)
        confidence = quality_assessment.overall_confidence

        return NormalizedDocumentRecord(
            document_id=document_id,
            claim_id=claim_id,
            file_name=file_name,
            content_type=content_type,
            s3_uri=s3_uri,
            document_type=classification.document_type,
            upload_status=upload_status,
            ocr_status=ocr_status,
            raw_text=intelligence_result.raw_text,
            normalized_text=intelligence_result.normalized_text,
            validation_results=intelligence_result.validation_results,
            document_classification=classification,
            extracted_fields=extracted_fields,
            quality_assessment=quality_assessment,
            textract_blocks=intelligence_result.textract_blocks,
            confidence_score=confidence,
            normalized_at=datetime.now(timezone.utc),
            metadata={
                "s3_bucket": s3_bucket,
                "s3_key": s3_key,
                "source": "document_intelligence_orchestrator",
            },
        )
