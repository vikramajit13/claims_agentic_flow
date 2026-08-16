from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.tools import read_only_claim_tools


@dataclass
class _FakeClaim:
    id: int
    claim_number: str
    claim_type: str
    status: str
    claim_amount: float
    incident_date: str
    created_at: datetime


@dataclass
class _FakeDocument:
    id: int
    file_name: str
    normalized_document_type: str | None
    normalized_text: str | None
    ocr_text: str | None
    normalized_confidence: float | None
    quality_assessment: dict | None
    extracted_fields: dict | None
    upload_status: str
    ocr_status: str
    created_at: datetime
    normalized_at: datetime | None


@dataclass
class _FakeWorkflowRun:
    claim_id: int
    status: str
    current_step: str
    created_at: datetime


class _FakeExecuteResult:
    def __init__(self, claims):
        self._claims = claims

    def scalars(self):
        return self

    def all(self):
        return self._claims


class _FakeSession:
    def __init__(self, claims=None, documents=None, workflow_runs=None, claim=None):
        self._claims = claims or []
        self._documents = documents or []
        self._workflow_runs = workflow_runs or []
        self._claim = claim

    async def execute(self, _query):
        query_text = str(_query)
        if "FROM claim_documents" in query_text:
            return _FakeExecuteResult(self._documents)
        if "FROM workflow_runs" in query_text:
            return _FakeExecuteResult(self._workflow_runs)
        return _FakeExecuteResult(self._claims)

    async def get(self, _model, _claim_id):
        return self._claim


def test_get_claim_history_handles_naive_and_aware_created_at(monkeypatch):
    now = datetime.now(UTC)
    claims = [
        _FakeClaim(
            id=1,
            claim_number="CLM-001",
            claim_type="motor",
            status="submitted",
            claim_amount=1200.0,
            incident_date="2026-08-01",
            created_at=(now - timedelta(days=10)).replace(tzinfo=None),
        ),
        _FakeClaim(
            id=2,
            claim_number="CLM-002",
            claim_type="motor",
            status="submitted",
            claim_amount=1300.0,
            incident_date="2026-08-02",
            created_at=now - timedelta(days=400),
        ),
    ]

    @asynccontextmanager
    async def _fake_get_session():
        yield _FakeSession(claims)

    monkeypatch.setattr(read_only_claim_tools, "get_session", _fake_get_session)

    payload = asyncio.run(
        read_only_claim_tools.get_claim_history.ainvoke(
            {
                "customer_id": 1001,
                "lookback_months": 12,
                "exclude_claim_id": None,
            }
        )
    )

    parsed = json.loads(payload)
    assert parsed["claim_count"] == 1
    assert parsed["claims"][0]["claim_number"] == "CLM-001"


def test_get_customer_risk_overview_summarizes_claims(monkeypatch):
    now = datetime.now(UTC)
    claims = [
        _FakeClaim(1, "CLM-001", "motor", "submitted", 1200.0, "2026-08-01", now),
        _FakeClaim(2, "CLM-002", "motor", "rejected", 900.0, "2026-07-02", now - timedelta(days=5)),
        _FakeClaim(3, "CLM-003", "travel", "draft", 300.0, "2026-06-02", now - timedelta(days=10)),
    ]

    @asynccontextmanager
    async def _fake_get_session():
        yield _FakeSession(claims=claims)

    monkeypatch.setattr(read_only_claim_tools, "get_session", _fake_get_session)

    payload = asyncio.run(
        read_only_claim_tools.get_customer_risk_overview.ainvoke(
            {
                "customer_id": 1001,
                "exclude_claim_id": None,
            }
        )
    )

    parsed = json.loads(payload)
    assert parsed["claim_count"] == 3
    assert parsed["rejected_claim_count"] == 1
    assert parsed["open_claim_count"] == 2
    assert parsed["status_counts"]["rejected"] == 1


def test_get_claim_timeline_includes_documents_and_workflows(monkeypatch):
    now = datetime.now(UTC)
    claim = _FakeClaim(10, "CLM-010", "motor", "submitted", 1800.0, "2026-08-01", now - timedelta(days=2))
    document = _FakeDocument(
        id=7,
        file_name="invoice.pdf",
        normalized_document_type="invoice",
        normalized_text="Repair invoice body",
        ocr_text="Repair invoice body",
        normalized_confidence=0.98,
        quality_assessment={"review_recommended": False},
        extracted_fields={"invoice_date": "2026-08-02"},
        upload_status="ocr_completed",
        ocr_status="completed",
        created_at=now - timedelta(days=1),
        normalized_at=now,
    )
    workflow_run = _FakeWorkflowRun(
        claim_id=10,
        status="waiting_for_human",
        current_step="human_review",
        created_at=now + timedelta(hours=1),
    )

    @asynccontextmanager
    async def _fake_get_session():
        yield _FakeSession(
            claim=claim,
            documents=[document],
            workflow_runs=[workflow_run],
        )

    monkeypatch.setattr(read_only_claim_tools, "get_session", _fake_get_session)

    payload = asyncio.run(read_only_claim_tools.get_claim_timeline.ainvoke({"claim_id": 10}))

    parsed = json.loads(payload)
    assert parsed["claim_found"] is True
    assert [event["type"] for event in parsed["events"]] == [
        "claim_created",
        "document_recorded",
        "document_normalized",
        "workflow_run",
    ]
