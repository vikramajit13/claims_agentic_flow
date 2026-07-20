from __future__ import annotations


def normalize_claim_type(claim_type: str | None) -> str | None:
    if not claim_type:
        return None
    return claim_type.strip().lower()
