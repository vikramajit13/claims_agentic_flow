from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.db import ClaimDocumentRecord, ClaimRecord, WorkflowRunRecord, get_session


def _json(data: dict) -> str:
    return json.dumps(data, default=str)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def _safe_scalars_all(session, query) -> list:
    try:
        return (await session.execute(query)).scalars().all()
    except OperationalError:
        return []


async def _safe_get(session, model, record_id):
    try:
        return await session.get(model, record_id)
    except OperationalError:
        return None


@tool
async def get_claim_history(customer_id: int, lookback_months: int = 12, exclude_claim_id: int | None = None) -> str:
    """Fetch prior claims for a customer within a configurable lookback window."""
    lookback_cutoff = datetime.now(UTC) - timedelta(days=max(lookback_months, 1) * 30)

    async with get_session() as session:
        query = select(ClaimRecord).where(ClaimRecord.customer_id == customer_id)
        if exclude_claim_id is not None:
            query = query.where(ClaimRecord.id != exclude_claim_id)
        claims = await _safe_scalars_all(session, query.order_by(ClaimRecord.created_at.desc()))

    filtered = [claim for claim in claims if _as_utc(claim.created_at) >= lookback_cutoff]
    return _json(
        {
            "customer_id": customer_id,
            "lookback_months": lookback_months,
            "claim_count": len(filtered),
            "claims": [
                {
                    "claim_id": claim.id,
                    "claim_number": claim.claim_number,
                    "claim_type": claim.claim_type,
                    "status": claim.status,
                    "claim_amount": claim.claim_amount,
                    "incident_date": claim.incident_date,
                    "created_at": claim.created_at.isoformat(),
                }
                for claim in filtered
            ],
        }
    )


@tool
async def get_prior_rejection_details(customer_id: int, exclude_claim_id: int | None = None) -> str:
    """Fetch previously rejected claims for a customer to support reopen or escalation review."""
    async with get_session() as session:
        query = select(ClaimRecord).where(ClaimRecord.customer_id == customer_id)
        if exclude_claim_id is not None:
            query = query.where(ClaimRecord.id != exclude_claim_id)
        claims = await _safe_scalars_all(session, query.order_by(ClaimRecord.created_at.desc()))

    rejected_claims = [claim for claim in claims if str(claim.status).lower() == "rejected"]
    return _json(
        {
            "customer_id": customer_id,
            "prior_rejection_count": len(rejected_claims),
            "rejections": [
                {
                    "claim_id": claim.id,
                    "claim_number": claim.claim_number,
                    "status": claim.status,
                    "claim_amount": claim.claim_amount,
                    "created_at": claim.created_at.isoformat(),
                }
                for claim in rejected_claims
            ],
        }
    )


@tool
async def get_customer_risk_overview(customer_id: int, exclude_claim_id: int | None = None) -> str:
    """Summarize prior customer claim volume, statuses, and exposure to help the LLM choose follow-up tools."""
    async with get_session() as session:
        query = select(ClaimRecord).where(ClaimRecord.customer_id == customer_id)
        if exclude_claim_id is not None:
            query = query.where(ClaimRecord.id != exclude_claim_id)
        claims = await _safe_scalars_all(session, query.order_by(ClaimRecord.created_at.desc()))

    statuses: dict[str, int] = {}
    total_claim_amount = 0.0
    rejected_count = 0
    open_count = 0
    for claim in claims:
        normalized_status = str(claim.status).lower()
        statuses[normalized_status] = statuses.get(normalized_status, 0) + 1
        total_claim_amount += float(claim.claim_amount or 0)
        if normalized_status == "rejected":
            rejected_count += 1
        if normalized_status not in {"rejected", "closed", "paid"}:
            open_count += 1

    return _json(
        {
            "customer_id": customer_id,
            "claim_count": len(claims),
            "status_counts": statuses,
            "rejected_claim_count": rejected_count,
            "open_claim_count": open_count,
            "total_claim_amount": round(total_claim_amount, 2),
        }
    )


@tool
async def get_policy_coverage_summary(policy_id: str) -> str:
    """Return a mocked policy summary including dates, status, limits, deductible, and covered claim types."""
    numeric_portion = "".join(char for char in policy_id if char.isdigit()) or "1"
    variant = int(numeric_portion) % 3
    covered_claim_types = [
        ["motor", "theft"],
        ["travel", "medical"],
        ["property", "motor"],
    ][variant]
    coverage_limit = [10000, 15000, 20000][variant]
    deductible = [500, 250, 1000][variant]

    return _json(
        {
            "policy_id": policy_id,
            "status": "ACTIVE",
            "active_from": "2026-01-01",
            "active_to": "2026-12-31",
            "coverage_limit": coverage_limit,
            "deductible": deductible,
            "covered_claim_types": covered_claim_types,
            "source": "mock_policy_adapter",
        }
    )


@tool
async def get_document_metadata(claim_id: int, document_types: list[str] | None = None) -> str:
    """Fetch normalized document metadata and extracted fields for a claim."""
    normalized_filter = {item.strip().lower() for item in document_types or []}

    async with get_session() as session:
        documents = await _safe_scalars_all(
            session,
            select(ClaimDocumentRecord)
            .where(ClaimDocumentRecord.claim_id == claim_id)
            .order_by(ClaimDocumentRecord.id.asc()),
        )

    payload_documents = []
    for document in documents:
        resolved_type = (document.normalized_document_type or "").lower()
        if normalized_filter and resolved_type not in normalized_filter:
            continue
        fields = document.extracted_fields or {}
        payload_documents.append(
            {
                "document_id": document.id,
                "document_type": document.normalized_document_type or document.file_name,
                "invoice_date": fields.get("invoice_date"),
                "invoice_amount": fields.get("invoice_amount"),
                "vendor_name": fields.get("vendor_name") or fields.get("repairer_name"),
                "verification_status": document.ocr_status,
                "upload_status": document.upload_status,
            }
        )

    return _json({"claim_id": claim_id, "documents": payload_documents})


@tool
async def get_document_text_evidence(
    claim_id: int,
    document_types: list[str] | None = None,
    max_documents: int = 3,
) -> str:
    """Return compact document evidence snippets and extraction quality for LLM-led investigation."""
    normalized_filter = {item.strip().lower() for item in document_types or []}

    async with get_session() as session:
        documents = await _safe_scalars_all(
            session,
            select(ClaimDocumentRecord)
            .where(ClaimDocumentRecord.claim_id == claim_id)
            .order_by(ClaimDocumentRecord.id.asc()),
        )

    evidence = []
    for document in documents:
        resolved_type = (document.normalized_document_type or "").lower()
        if normalized_filter and resolved_type not in normalized_filter:
            continue

        snippet_source = document.normalized_text or document.ocr_text or ""
        evidence.append(
            {
                "document_id": document.id,
                "document_type": document.normalized_document_type or document.file_name,
                "snippet": snippet_source[:280],
                "has_more_text": len(snippet_source) > 280,
                "confidence": document.normalized_confidence,
                "review_recommended": bool((document.quality_assessment or {}).get("review_recommended", False)),
                "extracted_fields": document.extracted_fields or {},
            }
        )
        if len(evidence) >= max(max_documents, 1):
            break

    return _json({"claim_id": claim_id, "documents": evidence})


@tool
async def get_claim_timeline(claim_id: int) -> str:
    """Return a normalized timeline of claim, document, and workflow events to support graph branching decisions."""
    async with get_session() as session:
        claim = await _safe_get(session, ClaimRecord, claim_id)
        documents = await _safe_scalars_all(
            session,
            select(ClaimDocumentRecord)
            .where(ClaimDocumentRecord.claim_id == claim_id)
            .order_by(ClaimDocumentRecord.created_at.asc()),
        )
        workflow_runs = await _safe_scalars_all(
            session,
            select(WorkflowRunRecord)
            .where(WorkflowRunRecord.claim_id == claim_id)
            .order_by(WorkflowRunRecord.created_at.asc()),
        )

    if claim is None:
        return _json({"claim_id": claim_id, "events": [], "claim_found": False})

    events = [
        {
            "type": "claim_created",
            "timestamp": claim.created_at.isoformat(),
            "status": claim.status,
            "detail": claim.claim_number,
        }
    ]
    for document in documents:
        events.append(
            {
                "type": "document_recorded",
                "timestamp": document.created_at.isoformat(),
                "status": document.upload_status,
                "detail": document.file_name,
            }
        )
        if document.normalized_at is not None:
            events.append(
                {
                    "type": "document_normalized",
                    "timestamp": document.normalized_at.isoformat(),
                    "status": document.ocr_status,
                    "detail": document.normalized_document_type or document.file_name,
                }
            )
    for workflow_run in workflow_runs:
        events.append(
            {
                "type": "workflow_run",
                "timestamp": workflow_run.created_at.isoformat(),
                "status": workflow_run.status,
                "detail": workflow_run.current_step,
            }
        )

    events.sort(key=lambda item: item["timestamp"])
    return _json({"claim_id": claim_id, "claim_found": True, "events": events})


@tool
async def get_guardrail_results(claim_id: int, workflow_run_id: str | None = None, phase: str | None = None) -> str:
    """Fetch synthesized deterministic guardrail results for a claim investigation step."""
    del workflow_run_id
    del phase

    async with get_session() as session:
        claim = await _safe_get(session, ClaimRecord, claim_id)
        documents = await _safe_scalars_all(
            session,
            select(ClaimDocumentRecord)
            .where(ClaimDocumentRecord.claim_id == claim_id)
            .order_by(ClaimDocumentRecord.id.asc()),
        )

    if claim is None:
        return _json({"claim_id": claim_id, "overall_decision": "BLOCKED", "results": [{"code": "CLAIM_NOT_FOUND"}]})

    results: list[dict] = []
    overall_decision = "PASS"

    if claim.claim_amount and claim.claim_amount > 5000:
        overall_decision = "REVIEW_REQUIRED"
        results.append(
            {
                "code": "CLAIM_AMOUNT_ABOVE_REVIEW_THRESHOLD",
                "decision": "REVIEW_REQUIRED",
                "severity": "MEDIUM",
                "message": "Claim amount exceeds manual review threshold.",
            }
        )

    for document in documents:
        fields = document.extracted_fields or {}
        invoice_date = fields.get("invoice_date")
        if claim.incident_date and invoice_date and str(invoice_date) > str(claim.incident_date):
            overall_decision = "REVIEW_REQUIRED"
            results.append(
                {
                    "code": "INVOICE_DATE_AFTER_INCIDENT",
                    "decision": "REVIEW_REQUIRED",
                    "severity": "HIGH",
                    "message": f"Invoice date {invoice_date} is after incident date {claim.incident_date}.",
                }
            )

    if not results:
        results.append(
            {
                "code": "NO_GUARDRAIL_BREACH",
                "decision": "PASS",
                "severity": "LOW",
                "message": "No deterministic guardrail breach detected.",
            }
        )

    return _json({"claim_id": claim_id, "overall_decision": overall_decision, "results": results})
