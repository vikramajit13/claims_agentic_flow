from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


OUTPUT = Path("/Users/vikramsingh/claims_agentic_flow/output/pdf/claims-agent-deepseek-summary-2026-08-11.pdf")


def build_story():
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#102A43"),
        spaceAfter=8,
    )
    subtitle = ParagraphStyle(
        "SubtitleCustom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#486581"),
        spaceAfter=14,
    )
    section = ParagraphStyle(
        "SectionCustom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        textColor=colors.HexColor("#0B7285"),
        spaceBefore=8,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "BodyCustom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1F2933"),
        spaceAfter=6,
    )

    story = [
        Paragraph("Claims Agent Deployment Summary", title),
        Paragraph("Generated on August 11, 2026 for the dev environment in ap-southeast-2.", subtitle),
        Paragraph("Current Status", section),
        Paragraph(
            "The live stack is working end to end with DeepSeek V4 Pro as the document intelligence model. "
            "The deployed UI, backend, OCR callback path, and graph workflow were exercised successfully.",
            body,
        ),
    ]

    summary_rows = [
        ["Frontend URL", "https://d2mq7u0i5f6mq8.cloudfront.net/"],
        ["Health URL", "https://d2mq7u0i5f6mq8.cloudfront.net/health"],
        ["Live provider", "DeepSeek V4 Pro via https://api.deepseek.com"],
        ["Live ECS task definition", "claims-agent-dev-api:9"],
        ["Validated claim", "CLM-DS-556714"],
        ["Validated document result", "OCR completed, document type detected as invoice"],
        ["Validated workflow result", "Workflow 2 reached waiting_for_human at step human_review"],
    ]

    table = Table(summary_rows, colWidths=[55 * mm, 115 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BCCCDC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEADING", (0, 0), (-1, -1), 12),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F8FBFD")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([table, Spacer(1, 8)])

    story.extend(
        [
            Paragraph("Agent Invocation Notes", section),
            Paragraph(
                "Subagents were not invoked in this task. All investigation, deployment changes, browser testing, "
                "and validation were handled by the main Codex agent only.",
                body,
            ),
            Paragraph("Terraform Reproducibility Notes", section),
            Paragraph(
                "The checked-in Terraform now includes the OpenAI-compatible secret wiring and the DeepSeek "
                "configuration values needed for reproducible deployments.",
                body,
            ),
            Paragraph(
                "Remaining drift still exists in AWS versus Terraform state. A fresh terraform plan shows Terraform "
                "would create an ECS service named claims-agent-dev-api, while the live service currently in use is "
                "claims-agent-dev-api-live. The state also still reflects an older API task definition revision, "
                "which means the repo is logically correct for provider settings but not yet fully reconciled for "
                "service identity.",
                body,
            ),
            Paragraph("Files Updated In Repo", section),
            Paragraph(
                "infra/environments/dev/ecs.tf, infra/environments/dev/locals.tf, "
                "infra/environments/dev/variables.tf, infra/environments/dev/terraform.tfvars, and "
                "infra/environments/dev/terraform.tfvars.example.",
                body,
            ),
            Paragraph("Recommended Next Cleanup", section),
            Paragraph(
                "Either import or rename the live ECS service so Terraform manages the same service object that is "
                "currently serving production traffic in dev. After that, rerun terraform plan and apply so the "
                "DeepSeek deployment is reproducible without manual ECS task registration or service updates.",
                body,
            ),
        ]
    )
    return story


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Claims Agent Deployment Summary",
        author="Codex",
    )
    doc.build(build_story())
    print(OUTPUT)


if __name__ == "__main__":
    main()
