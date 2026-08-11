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


class _FakeExecuteResult:
    def __init__(self, claims):
        self._claims = claims

    def scalars(self):
        return self

    def all(self):
        return self._claims


class _FakeSession:
    def __init__(self, claims):
        self._claims = claims

    async def execute(self, _query):
        return _FakeExecuteResult(self._claims)


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
