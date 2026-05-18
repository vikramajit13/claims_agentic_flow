from app.schemas.case_packet_schema import CasePacketSchema
from app.schemas.claim_schema import ClaimSummarySchema
from app.schemas.policy_schema import PolicySummarySchema


class CasePacketBuilder:
    def build(
        self,
        claim,
        policy,
        documents,
        coverage_result,
        evidence_result,
        risk_result,
        guardrail_results,
        recommendation,
        claim_history_summary=None,
    ) -> CasePacketSchema:
        return CasePacketSchema(
            claim_summary=ClaimSummarySchema(
                claim_id=claim.id,
                customer_id=claim.customer_id,
                claim_type=claim.claim_type,
                claim_amount=claim.claim_amount,
                incident_date=claim.incident_date,
                description=claim.description,
            ),
            policy_summary=PolicySummarySchema(
                policy_id=policy.id,
                policy_number=policy.policy_number,
                status=policy.status,
                active_from=policy.active_from,
                active_to=policy.active_to,
                coverage_limit=policy.coverage_limit,
            ),
            documents=[
                {
                    "document_type": document.document_type.value,
                    "file_name": document.file_name,
                    "document_metadata": document.document_metadata,
                    "verification_status": document.verification_status.value,
                }
                for document in documents
            ],
            coverage_result=coverage_result,
            evidence_result=evidence_result,
            risk_result=risk_result,
            guardrail_results=guardrail_results if guardrail_results else None,
            adjudication_recommendation=recommendation,
            claim_history_summary=claim_history_summary,
        )
