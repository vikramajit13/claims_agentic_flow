from enum import StrEnum


class RecommendationDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"
    REFER_TO_HUMAN = "REFER_TO_HUMAN"


class FraudRiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class HumanDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MODIFY_PAYOUT = "MODIFY_PAYOUT"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"
    ESCALATE = "ESCALATE"
