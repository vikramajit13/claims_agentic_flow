from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "Claims Control Tower"
    payment_approval_threshold: float = 5000.0
    suspicious_keywords: tuple[str, ...] = (
        "cash",
        "urgent",
        "backdated",
        "lost receipt",
        "wire transfer",
    )


settings = Settings()
