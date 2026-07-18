from app.enum.enums import ClaimType

document_required={
    ClaimType.AUTO: ["invoice", "police_report"],
    ClaimType.HOME: ["invoice", "police_report", "damage_report"],
    ClaimType.HEALTH: ["invoice", "medical_report"],
}