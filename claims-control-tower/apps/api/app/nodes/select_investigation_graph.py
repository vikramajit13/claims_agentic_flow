from __future__ import annotations

from collections.abc import Mapping

from app.graph.state import ClaimGraphState
from app.tools import list_investigation_graph_options

DEFAULT_GRAPH = "investigate_claim_graph"


def _read_value(document: object, key: str):
    if isinstance(document, Mapping):
        return document.get(key)
    return getattr(document, key, None)


def _has_document_evidence(state: ClaimGraphState) -> bool:
    return any(
        bool(
            _read_value(document, "document_text")
            or _read_value(document, "normalized_document_type")
            or _read_value(document, "normalized_payload")
        )
        for document in state.claim_documents
    )


def select_investigation_graph(state: ClaimGraphState) -> dict:
    selected_graph = DEFAULT_GRAPH
    reason = "Defaulted to the broad investigation graph for a balanced claim review."

    if _has_document_evidence(state):
        selected_graph = "document_evidence_graph"
        reason = "Claim documents already contain OCR or normalized evidence, so document-focused investigation is preferred."
    elif (state.risk_level or "").upper() in {"HIGH", "CRITICAL"} or (state.risk_score or 0) >= 70:
        selected_graph = "customer_history_graph"
        reason = "Elevated risk indicates we should inspect prior customer history and rejection patterns first."

    notes = list(state.investigation_notes)
    notes.append(f"Investigation graph selected: {selected_graph}. {reason}")
    return {
        "selected_investigation_graph": selected_graph,
        "selected_investigation_reason": reason,
        "graph_catalog": list_investigation_graph_options(),
        "investigation_notes": notes,
    }
