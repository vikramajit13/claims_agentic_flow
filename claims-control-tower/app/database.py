from __future__ import annotations

from collections import defaultdict
from datetime import date

from app.models.claim import Claim, ClaimStatus
from app.models.policy import Policy, PolicyType


class InMemoryStore:
    def __init__(self) -> None:
        self.counters: defaultdict[str, int] = defaultdict(int)
        self.claims = {}
        self.policies = {}
        self.documents = {}
        self.workflow_runs = {}
        self.workflow_events = {}
        self.human_tasks = {}
        self.payment_instructions = {}
        self.seed()

    def next_id(self, bucket: str) -> int:
        self.counters[bucket] += 1
        return self.counters[bucket]

    def seed(self) -> None:
        if self.policies:
            return

        sample_policies = [
            Policy(
                id=self.next_id("policies"),
                policy_number="POL-1001",
                customer_id=100,
                policy_type=PolicyType.ACTIVE,
                coverage_limit=10000,
                deductible=500,
                active_from=str(date(2026, 1, 1)),
                active_to=str(date(2026, 12, 31)),
                status="active",
                covered_claim_types=["motor", "theft"],
            ),
            Policy(
                id=self.next_id("policies"),
                policy_number="POL-1002",
                customer_id=101,
                policy_type=PolicyType.ACTIVE,
                coverage_limit=25000,
                deductible=1000,
                active_from=str(date(2026, 1, 1)),
                active_to=str(date(2026, 12, 31)),
                status="active",
                covered_claim_types=["medical", "travel"],
            ),
            Policy(
                id=self.next_id("policies"),
                policy_number="POL-1003",
                customer_id=102,
                policy_type=PolicyType.EXPIRED,
                coverage_limit=8000,
                deductible=250,
                active_from=str(date(2025, 1, 1)),
                active_to=str(date(2025, 12, 31)),
                status="expired",
                covered_claim_types=["motor"],
            ),
            Policy(
                id=self.next_id("policies"),
                policy_number="POL-MOTOR-001",
                customer_id=999,
                policy_type=PolicyType.ACTIVE,
                coverage_limit=12000,
                deductible=500,
                active_from=str(date(2026, 1, 1)),
                active_to=str(date(2026, 12, 31)),
                status="active",
                covered_claim_types=["motor"],
            ),
        ]

        for policy in sample_policies:
            self.policies[policy.id] = policy

        seeded_claims = [
            Claim(
                id=self.next_id("claims"),
                claim_number="HIST-999-001",
                customer_id=999,
                policy_id=4,
                claim_type="motor",
                claim_amount=1800,
                incident_date=str(date(2025, 7, 10)),
                description="Historical motor claim 1",
                status=ClaimStatus.COMPLETED,
                created_at=str(date(2025, 7, 11)),
                updated_at=str(date(2025, 7, 11)),
            ),
            Claim(
                id=self.next_id("claims"),
                claim_number="HIST-999-002",
                customer_id=999,
                policy_id=4,
                claim_type="motor",
                claim_amount=2100,
                incident_date=str(date(2025, 10, 5)),
                description="Historical motor claim 2",
                status=ClaimStatus.COMPLETED,
                created_at=str(date(2025, 10, 6)),
                updated_at=str(date(2025, 10, 6)),
            ),
            Claim(
                id=self.next_id("claims"),
                claim_number="HIST-999-003",
                customer_id=999,
                policy_id=4,
                claim_type="motor",
                claim_amount=2600,
                incident_date=str(date(2026, 2, 14)),
                description="Historical motor claim 3",
                status=ClaimStatus.COMPLETED,
                created_at=str(date(2026, 2, 15)),
                updated_at=str(date(2026, 2, 15)),
            ),
        ]
        for claim in seeded_claims:
            self.claims[claim.id] = claim

    def reset(self) -> None:
        self.counters = defaultdict(int)
        self.claims = {}
        self.policies = {}
        self.documents = {}
        self.workflow_runs = {}
        self.workflow_events = {}
        self.human_tasks = {}
        self.payment_instructions = {}
        self.seed()


_store = InMemoryStore()


def get_store() -> InMemoryStore:
    return _store
