from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from langgraph.types import Command
from sqlalchemy import select

from app.config import settings
from app.db import ClaimDocumentRecord, ClaimRecord, HumanReviewRecord, WorkflowRunRecord, get_session
from app.enums import ClaimStatus, DocumentStatus, OcrStatus, WorkflowStatus, WorkflowStep
from app.graph.state import ClaimGraphState
from app.graph.manager import GraphStateManagerFactory
from app.observability import traceable
from app.schemas import (
    HumanReviewDecisionRequest,
    HumanReviewResponse,
    WorkflowTraceEvent,
    WorkflowTraceResponse,
    WorkflowRunResponse,
    WorkflowStartRequest,
)


def _now():
    return datetime.now(timezone.utc)


class WorkflowService:
    def __init__(self) -> None:
        self.graph_manager = GraphStateManagerFactory().create()

    @staticmethod
    def _build_workflow_response(
        workflow: WorkflowRunRecord,
        *,
        human_review_id: int | None = None,
        graph_thread_id: str | None = None,
    ) -> WorkflowRunResponse:
        return WorkflowRunResponse(
            id=workflow.id,
            claim_id=workflow.claim_id,
            status=WorkflowStatus(workflow.status),
            current_step=WorkflowStep(workflow.current_step),
            hitl_required=workflow.hitl_required,
            next_action=workflow.next_action,
            human_review_id=human_review_id,
            graph_thread_id=graph_thread_id or workflow.graph_thread_id,
            notes=workflow.notes,
            created_at=workflow.created_at.isoformat(),
            updated_at=workflow.updated_at.isoformat(),
        )

    @staticmethod
    def _build_human_review_response(review: HumanReviewRecord) -> HumanReviewResponse:
        return HumanReviewResponse(
            id=review.id,
            workflow_run_id=review.workflow_run_id,
            claim_id=review.claim_id,
            review_mode=review.review_mode,
            status=review.status,
            thread_id=review.thread_id,
            request_payload=review.request_payload,
            decision_payload=review.decision_payload,
            resolved_at=review.resolved_at.isoformat() if review.resolved_at is not None else None,
            created_at=review.created_at.isoformat(),
            updated_at=review.updated_at.isoformat(),
        )

    @staticmethod
    def _create_human_review_record(
        *,
        workflow_run_id: int,
        claim_id: int,
        review_mode: str,
        request_payload: dict,
        thread_id: str | None,
    ) -> HumanReviewRecord:
        timestamp = _now()
        return HumanReviewRecord(
            workflow_run_id=workflow_run_id,
            claim_id=claim_id,
            review_mode=review_mode,
            status="pending",
            thread_id=thread_id,
            request_payload=request_payload,
            decision_payload=None,
            created_at=timestamp,
            updated_at=timestamp,
            resolved_at=None,
        )

    async def _extract_graph_state_snapshot(self, thread_id: str | None) -> dict | None:
        if not thread_id:
            return None
        compiled = self.graph_manager.runtime.compiled()
        if not hasattr(compiled, "aget_state"):
            return None
        try:
            snapshot = await compiled.aget_state({"configurable": {"thread_id": thread_id}})
        except Exception:
            return None
        values = getattr(snapshot, "values", None)
        return values if isinstance(values, dict) else None

    @staticmethod
    def _summarize_tool_result(tool_name: str, payload: dict) -> dict:
        summary = {"tool": tool_name}
        if tool_name == "get_guardrail_results":
            summary["overall_decision"] = payload.get("overall_decision")
            summary["result_count"] = len(payload.get("results", []) or [])
            return summary
        if tool_name == "get_customer_risk_overview":
            summary["claim_count"] = payload.get("claim_count")
            summary["rejected_claim_count"] = payload.get("rejected_claim_count")
            summary["open_claim_count"] = payload.get("open_claim_count")
            return summary
        if tool_name == "get_prior_rejection_details":
            summary["prior_rejection_count"] = payload.get("prior_rejection_count")
            return summary
        if tool_name == "get_policy_coverage_summary":
            summary["status"] = payload.get("status")
            summary["coverage_limit"] = payload.get("coverage_limit")
            summary["deductible"] = payload.get("deductible")
            return summary
        if tool_name == "get_document_metadata":
            summary["document_count"] = len(payload.get("documents", []) or [])
            return summary
        if tool_name == "get_document_text_evidence":
            summary["document_count"] = len(payload.get("documents", []) or [])
            return summary
        if tool_name == "get_claim_history":
            summary["claim_count"] = payload.get("claim_count")
            summary["lookback_months"] = payload.get("lookback_months")
            return summary
        if tool_name == "get_claim_timeline":
            summary["event_count"] = len(payload.get("events", []) or [])
            summary["claim_found"] = payload.get("claim_found")
            return summary
        return summary

    @staticmethod
    def _trace_event(
        *,
        event_id: str,
        stage: str,
        title: str,
        detail: str,
        status: str = "info",
        timestamp: str | None = None,
        metadata: dict | None = None,
    ) -> WorkflowTraceEvent:
        return WorkflowTraceEvent(
            id=event_id,
            stage=stage,
            title=title,
            detail=detail,
            status=status,
            timestamp=timestamp,
            metadata=metadata or {},
        )

    def _build_trace_response(
        self,
        *,
        claim_id: int,
        workflow: WorkflowRunRecord | None,
        reviews: list[HumanReviewRecord],
    ) -> WorkflowTraceResponse:
        snapshot = workflow.graph_state_snapshot if workflow is not None else None
        events: list[WorkflowTraceEvent] = []

        if snapshot:
            investigation_plan = snapshot.get("investigation_plan", [])
            graph_catalog = snapshot.get("graph_catalog", [])
            tool_catalog = snapshot.get("tool_catalog", [])
            selected_graph = (
                snapshot.get("selected_investigation_graph")
                or (
                    investigation_plan[0].get("graph_name")
                    if isinstance(investigation_plan, list)
                    and investigation_plan
                    and isinstance(investigation_plan[0], dict)
                    else None
                )
                or snapshot.get("graph_name")
            )
            if selected_graph:
                events.append(
                    self._trace_event(
                        event_id="selected-graph",
                        stage="graph_selection",
                        title="Investigation graph selected",
                        detail=str(snapshot.get("selected_investigation_reason") or selected_graph),
                        metadata={
                            "graph_name": selected_graph,
                            "candidate_graphs": [item.get("graph_name") for item in graph_catalog if isinstance(item, dict)],
                            "plan": investigation_plan,
                        },
                    )
                )

            tool_judgment = snapshot.get("tool_selection_judgment") or {}
            if tool_judgment:
                events.append(
                    self._trace_event(
                        event_id="tool-judge",
                        stage="tool_judge",
                        title="Tool judge verdict",
                        detail=str(tool_judgment.get("rationale") or "Tool selection reviewed."),
                        status="warning" if not tool_judgment.get("approved", True) else "info",
                        metadata={
                            **tool_judgment,
                            "selected_graph": selected_graph,
                        },
                    )
                )

            tool_results = snapshot.get("tool_results") or {}
            tool_result_summaries = [
                self._summarize_tool_result(tool_name, payload)
                for tool_name, payload in sorted(tool_results.items())
                if isinstance(payload, dict)
            ]
            if tool_results:
                events.append(
                    self._trace_event(
                        event_id="tools-executed",
                        stage="tools",
                        title="Investigation tools executed",
                        detail=", ".join(sorted(tool_results.keys())),
                        metadata={
                            "tools": sorted(tool_results.keys()),
                            "available_tools": [item.get("name") for item in tool_catalog if isinstance(item, dict)],
                            "findings": snapshot.get("investigation_findings", []),
                            "tool_result_summaries": tool_result_summaries,
                        },
                    )
                )

            action_judgment = snapshot.get("action_selection_judgment") or {}
            if action_judgment:
                events.append(
                    self._trace_event(
                        event_id="action-judge",
                        stage="action_judge",
                        title="Action judge verdict",
                        detail=str(action_judgment.get("rationale") or "Next action reviewed."),
                        status="warning" if not action_judgment.get("approved", True) else "info",
                        metadata={
                            **action_judgment,
                            "selected_action": snapshot.get("recommended_next_action"),
                        },
                    )
                )

            if snapshot.get("recommended_next_action"):
                events.append(
                    self._trace_event(
                        event_id="action-selected",
                        stage="action",
                        title="Workflow next action selected",
                        detail=str(snapshot.get("recommended_next_action_reason") or snapshot["recommended_next_action"]),
                        metadata={
                            "action": snapshot["recommended_next_action"],
                            "reason": snapshot.get("recommended_next_action_reason"),
                            "requires_human_review": snapshot.get("requires_human_review"),
                            "hitl_required": snapshot.get("hitl_required"),
                        },
                    )
                )

        for review in reviews:
            events.append(
                self._trace_event(
                    event_id=f"human-review-{review.id}",
                    stage="human_review",
                    title=f"Human review {review.status}",
                    detail=str(
                        (review.decision_payload or {}).get("notes")
                        or review.request_payload.get("message")
                        or "Human review checkpoint created."
                    ),
                    status="warning" if review.status == "pending" else "success",
                    timestamp=(review.resolved_at or review.updated_at).isoformat(),
                    metadata={
                        "review_id": review.id,
                        "status": review.status,
                        "review_mode": review.review_mode,
                        "request_payload": review.request_payload,
                        "decision": (review.decision_payload or {}).get("decision"),
                        "decision_payload": review.decision_payload,
                    },
                )
            )

        return WorkflowTraceResponse(
            claim_id=claim_id,
            workflow_run_id=workflow.id if workflow is not None else None,
            graph_thread_id=workflow.graph_thread_id if workflow is not None else None,
            workflow_status=workflow.status if workflow is not None else None,
            current_step=workflow.current_step if workflow is not None else None,
            events=events,
        )

    @staticmethod
    def _json_safe(value):
        if isinstance(value, dict):
            return {str(key): WorkflowService._json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [WorkflowService._json_safe(item) for item in value]
        if isinstance(value, tuple):
            return [WorkflowService._json_safe(item) for item in value]
        if isinstance(value, set):
            return [WorkflowService._json_safe(item) for item in sorted(value, key=str)]
        if hasattr(value, "model_dump"):
            return WorkflowService._json_safe(value.model_dump(mode="json"))
        if hasattr(value, "dict"):
            try:
                return WorkflowService._json_safe(value.dict())
            except TypeError:
                return WorkflowService._json_safe(value.dict)
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                return str(value)
        return str(value)

    @traceable(name="start_mock_claim_workflow", run_type="chain")
    async def start_claim_workflow(self, claim_id: int, request: WorkflowStartRequest) -> WorkflowRunResponse:
        async with get_session() as session:
            claim = await session.get(ClaimRecord, claim_id)
            if claim is None:
                raise KeyError(claim_id)

            documents = (
                await session.execute(
                select(ClaimDocumentRecord).where(ClaimDocumentRecord.claim_id == claim_id)
                )
            ).scalars().all()

            hitl_required = settings.default_hitl_required if request.hitl_required is None else request.hitl_required
            if not documents:
                status = WorkflowStatus.WAITING_FOR_DOCUMENTS
                step = WorkflowStep.DOCUMENT_COLLECTION
                next_action = "Upload claim documents through the pre-signed S3 flow before starting the graph."
                claim.status = ClaimStatus.WAITING_FOR_DOCUMENTS.value
            elif any(document.upload_status == DocumentStatus.PENDING_UPLOAD.value for document in documents):
                status = WorkflowStatus.WAITING_FOR_DOCUMENTS
                step = WorkflowStep.DOCUMENT_COLLECTION
                next_action = "One or more documents have not been confirmed as uploaded yet."
                claim.status = ClaimStatus.WAITING_FOR_DOCUMENTS.value
            elif any(document.ocr_status == OcrStatus.PENDING.value for document in documents):
                status = WorkflowStatus.CREATED
                step = WorkflowStep.OCR_ENRICHMENT
                next_action = "OCR is pending for one or more documents. Finish enrichment before graph execution."
                claim.status = ClaimStatus.SUBMITTED.value
                interrupt_payload = None
                graph_thread_id = None
                graph_state_snapshot = None
            elif hitl_required:
                status = WorkflowStatus.WAITING_FOR_HUMAN
                step = WorkflowStep.HUMAN_REVIEW
                next_action = "Human checkpoint reached before graph execution."
                claim.status = ClaimStatus.WAITING_FOR_HUMAN.value
                interrupt_payload = {
                    "step": "human_review",
                    "claim_id": claim_id,
                    "message": next_action,
                    "mode": "pre_graph_manual_gate",
                }
                graph_thread_id = None
                graph_state_snapshot = None
            else:
                graph_thread_id = f"claim-{claim_id}-{uuid4()}"
                graph_result = await self.graph_manager.ainvoke(
                    ClaimGraphState(
                        claim_id=claim_id,
                        hitl_required=False,
                        correlation_id=graph_thread_id,
                    ),
                    thread_id=graph_thread_id,
                )

                if graph_result.get("__interrupt__"):
                    interrupt_payload = getattr(graph_result["__interrupt__"][0], "value", graph_result["__interrupt__"][0])
                    status = WorkflowStatus.WAITING_FOR_HUMAN
                    step = WorkflowStep.HUMAN_REVIEW
                    next_action = interrupt_payload.get(
                        "message",
                        "Human checkpoint reached during graph execution.",
                    )
                    claim.status = ClaimStatus.WAITING_FOR_HUMAN.value
                else:
                    status = WorkflowStatus.READY_FOR_GRAPH
                    step = WorkflowStep.RECOMMEND_NEXT_ACTION
                    next_action = graph_result.get(
                        "recommended_next_action_reason",
                        "Claim graph executed successfully.",
                    )
                    claim.status = ClaimStatus.READY_FOR_GRAPH.value
                graph_state_snapshot = await self._extract_graph_state_snapshot(graph_thread_id)

            if "graph_thread_id" not in locals():
                graph_thread_id = None
            if "graph_state_snapshot" not in locals():
                graph_state_snapshot = None
            if "interrupt_payload" not in locals():
                interrupt_payload = None

            workflow = WorkflowRunRecord(
                claim_id=claim_id,
                status=status.value,
                current_step=step.value,
                hitl_required=status == WorkflowStatus.WAITING_FOR_HUMAN,
                next_action=next_action,
                notes=request.notes,
                graph_thread_id=graph_thread_id,
                graph_state_snapshot=self._json_safe(graph_state_snapshot),
                created_at=_now(),
                updated_at=_now(),
            )
            session.add(workflow)
            await session.flush()

            human_review_id = None
            response_thread_id = None
            if status == WorkflowStatus.WAITING_FOR_HUMAN:
                review = self._create_human_review_record(
                    workflow_run_id=workflow.id,
                    claim_id=claim_id,
                    review_mode="graph_interrupt" if not hitl_required else "pre_graph_manual_gate",
                    request_payload=interrupt_payload,
                    thread_id=graph_thread_id,
                )
                session.add(review)
                await session.flush()
                human_review_id = review.id
                response_thread_id = graph_thread_id

            claim.updated_at = _now()
            await session.commit()
            await session.refresh(workflow)
            return self._build_workflow_response(
                workflow,
                human_review_id=human_review_id,
                graph_thread_id=response_thread_id,
            )

    async def get_human_review(self, review_id: int) -> HumanReviewResponse:
        async with get_session() as session:
            review = await session.get(HumanReviewRecord, review_id)
            if review is None:
                raise KeyError(review_id)
            return self._build_human_review_response(review)

    async def list_human_reviews(self, *, status: str | None = "pending") -> list[HumanReviewResponse]:
        async with get_session() as session:
            query = select(HumanReviewRecord).order_by(HumanReviewRecord.updated_at.desc())
            if status:
                query = query.where(HumanReviewRecord.status == status)
            reviews = (await session.execute(query)).scalars().all()
            return [self._build_human_review_response(review) for review in reviews]

    async def get_claim_trace(self, claim_id: int) -> WorkflowTraceResponse:
        async with get_session() as session:
            workflow = (
                await session.execute(
                    select(WorkflowRunRecord)
                    .where(WorkflowRunRecord.claim_id == claim_id)
                    .order_by(WorkflowRunRecord.id.desc())
                )
            ).scalars().first()
            reviews = (
                await session.execute(
                    select(HumanReviewRecord)
                    .where(HumanReviewRecord.claim_id == claim_id)
                    .order_by(HumanReviewRecord.id.asc())
                )
            ).scalars().all()
        return self._build_trace_response(claim_id=claim_id, workflow=workflow, reviews=list(reviews))

    async def resume_human_review(
        self,
        review_id: int,
        request: HumanReviewDecisionRequest,
    ) -> HumanReviewResponse:
        async with get_session() as session:
            review = await session.get(HumanReviewRecord, review_id)
            if review is None:
                raise KeyError(review_id)
            if review.status != "pending":
                raise ValueError(f"Human review {review_id} is already {review.status}.")

            workflow = await session.get(WorkflowRunRecord, review.workflow_run_id)
            claim = await session.get(ClaimRecord, review.claim_id)
            if workflow is None or claim is None:
                raise KeyError(review_id)

            decision_payload = {
                "decision": request.decision,
                "notes": request.notes,
            }

            graph_result = None
            if review.thread_id:
                graph_result = await self.graph_manager.runtime.compiled().ainvoke(
                    Command(resume=decision_payload),
                    config={"configurable": {"thread_id": review.thread_id}},
                )

            review.status = "resolved"
            review.decision_payload = decision_payload
            review.resolved_at = _now()
            review.updated_at = _now()

            if graph_result and graph_result.get("__interrupt__"):
                interrupt_payload = getattr(graph_result["__interrupt__"][0], "value", graph_result["__interrupt__"][0])
                workflow.status = WorkflowStatus.WAITING_FOR_HUMAN.value
                workflow.current_step = WorkflowStep.HUMAN_REVIEW.value
                workflow.hitl_required = True
                workflow.next_action = interrupt_payload.get(
                    "message",
                    "Human checkpoint reached during graph execution.",
                )
                claim.status = ClaimStatus.WAITING_FOR_HUMAN.value
            elif request.decision.lower() in {"reject", "deny", "block"}:
                workflow.status = WorkflowStatus.READY_FOR_GRAPH.value
                workflow.current_step = WorkflowStep.HUMAN_REVIEW.value
                workflow.hitl_required = False
                workflow.next_action = request.notes or "Human reviewer rejected the claim."
                claim.status = ClaimStatus.READY_FOR_GRAPH.value
            else:
                workflow.status = WorkflowStatus.READY_FOR_GRAPH.value
                workflow.current_step = (
                    graph_result.get("current_step", WorkflowStep.POST_HUMAN_REVIEW.value)
                    if isinstance(graph_result, dict)
                    else WorkflowStep.POST_HUMAN_REVIEW.value
                )
                workflow.hitl_required = False
                workflow.next_action = (
                    graph_result.get("recommended_next_action_reason")
                    if isinstance(graph_result, dict) and graph_result.get("recommended_next_action_reason")
                    else request.notes or "Human review completed and graph resumed."
                )
                claim.status = ClaimStatus.READY_FOR_GRAPH.value

            workflow.graph_thread_id = review.thread_id
            workflow.graph_state_snapshot = self._json_safe(await self._extract_graph_state_snapshot(review.thread_id))
            workflow.updated_at = _now()
            claim.updated_at = _now()
            await session.commit()
            await session.refresh(review)
            return self._build_human_review_response(review)
