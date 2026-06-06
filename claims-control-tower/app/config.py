import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "Claims Control Tower"
    payment_approval_threshold: float = 5000.0
    agent_hitl_interrupt_enabled: bool = os.getenv("AGENT_HITL_INTERRUPT_ENABLED", "false").lower() == "true"
    suspicious_keywords: tuple[str, ...] = (
        "cash",
        "urgent",
        "backdated",
        "lost receipt",
        "wire transfer",
    )


settings = Settings()
