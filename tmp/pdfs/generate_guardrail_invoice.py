from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


OUTPUT = Path("/Users/vikramsingh/claims_agentic_flow/tmp/guardrail-invoice.pdf")


def draw_label_value(pdf: canvas.Canvas, x: float, y: float, label: str, value: str) -> float:
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(x, y, label)
    offset = stringWidth(label, "Helvetica-Bold", 10) + 4
    pdf.setFont("Helvetica", 10)
    pdf.drawString(x + offset, y, value)
    return y - 7 * mm


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(OUTPUT), pagesize=A4)
    width, height = A4

    pdf.setTitle("Guardrail Invoice Test")
    pdf.setFont("Helvetica-Bold", 22)
    pdf.setFillColor(colors.HexColor("#12344D"))
    pdf.drawString(20 * mm, height - 25 * mm, "ACME Collision Repairs")

    pdf.setFont("Helvetica", 11)
    pdf.setFillColor(colors.black)
    pdf.drawString(20 * mm, height - 33 * mm, "Invoice for claims workflow guardrail test")

    y = height - 48 * mm
    y = draw_label_value(pdf, 20 * mm, y, "Invoice Number:", "INV-DS-GUARD-001")
    y = draw_label_value(pdf, 20 * mm, y, "Invoice Date:", "2026-08-12")
    y = draw_label_value(pdf, 20 * mm, y, "Customer:", "Jordan Example")
    y = draw_label_value(pdf, 20 * mm, y, "Vehicle:", "2021 Toyota Corolla")
    y = draw_label_value(pdf, 20 * mm, y, "Repairer Name:", "ACME Collision Repairs")
    y = draw_label_value(pdf, 20 * mm, y, "Invoice Amount:", "2400.00")

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(20 * mm, y - 4 * mm, "Repair Summary")
    pdf.setFont("Helvetica", 10)
    text = pdf.beginText(20 * mm, y - 12 * mm)
    text.setLeading(14)
    lines = [
        "Front bumper replacement and repaint after low-speed parking collision.",
        "Parts, labour, paint matching, and calibration included.",
        "This invoice is intentionally dated after the incident date to test deterministic guardrails.",
    ]
    for line in lines:
        text.textLine(line)
    pdf.drawText(text)

    pdf.setStrokeColor(colors.HexColor("#BCCCDC"))
    pdf.line(20 * mm, 78 * mm, width - 20 * mm, 78 * mm)
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(colors.HexColor("#486581"))
    pdf.drawString(20 * mm, 70 * mm, "Test fixture generated for Claims Agent investigation graph validation.")

    pdf.showPage()
    pdf.save()
    print(OUTPUT)


if __name__ == "__main__":
    main()
