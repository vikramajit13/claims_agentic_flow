from __future__ import annotations

CLAIM_TYPE_DOCUMENT_REQUIREMENTS = {
    "auto": ["photo", "repair_estimate"],
    "motor": ["photo", "repair_estimate"],
    "home": ["invoice", "damage_report"],
    "property": ["invoice", "damage_report"],
    "health": ["invoice", "medical_report"],
    "medical": ["invoice", "medical_report"],
    "travel": ["invoice"],
    "theft": ["police_report"],
}
