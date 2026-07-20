from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.graph.state import ClaimGraphState


@dataclass(frozen=True)
class RiskResult:
    score_increment: int
    factor: str
    error: str | None = None


@dataclass
class RiskRegistry:
    risk_score: int = 0
    risk_factors: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def register(self, result: RiskResult) -> None:
        self.risk_score += result.score_increment
        self.risk_factors.append(result.factor)
        if result.error:
            self.errors.append(result.error)


class RiskRule(Protocol):
    def evaluate(self, state: ClaimGraphState, registry: RiskRegistry) -> None:
        ...


__all__ = ["RiskResult", "RiskRegistry", "RiskRule"]
