"""
PDF report generator — professional tax computation reports using ReportLab.

Generates branded PDFs for:
  - Income tax computation (old vs new regime comparison)
  - Client summary reports
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("operatoros.pdf")

# Output directory for generated PDFs
PDF_OUTPUT_DIR = Path(os.getenv("PDF_OUTPUT_DIR", "/app/reports"))


class PDFGenerator:
    """Generate professional tax computation PDF reports."""

    def __init__(self, firm_name: str = "OperatorOS CA Practice") -> None:
        self.firm_name = firm_name

    def generate_income_tax_report(
        self,
        computation: Any,
        client: Any,
    ) -> str:
        """Generate a PDF for an income tax computation.

        Args:
            computation: TaxComputation ORM instance.
            client: Client ORM instance.

        Returns:
            File path of the generated PDF.
        """
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch, mm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"tax_computation_{computation.id}.pdf"
        filepath = str(PDF_OUTPUT_DIR / filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=25 * mm,
            bottomMargin=20 * mm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            fontSize=18,
            spaceAfter=6,
            textColor=colors.HexColor("#1a365d"),
        )
        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            fontSize=13,
            spaceAfter=4,
            spaceBefore=12,
            textColor=colors.HexColor("#2d3748"),
        )
        normal_style = styles["Normal"]

        elements = []

        # ── Header ───────────────────────────────────────────────────
        elements.append(Paragraph(self.firm_name, title_style))
        elements.append(Paragraph("Income Tax Computation Report", heading_style))
        elements.append(Spacer(1, 6))

        # ── Client Details ───────────────────────────────────────────
        if client:
            client_data = [
                ["Client Name:", client.firm_name or "N/A"],
                ["PAN:", client.pan or "N/A"],
                ["Entity Type:", client.entity_type.value if client.entity_type else "N/A"],
                ["Assessment Year:", computation.assessment_year or "N/A"],
                ["Report Date:", datetime.now().strftime("%d/%m/%Y %H:%M")],
            ]
            t = Table(client_data, colWidths=[120, 350])
            t.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#4a5568")),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 12))

        # ── Tax Computation ──────────────────────────────────────────
        comp_json = computation.computation_json or {}
        comp_type = comp_json.get("type", "income_tax")

        if comp_type == "income_tax":
            elements.append(Paragraph("Tax Computation — Old vs New Regime", heading_style))

            old = comp_json.get("old_regime", {})
            new = comp_json.get("new_regime", {})

            comparison_data = [
                ["Particulars", "Old Regime", "New Regime"],
                ["Gross Total Income",
                 self._fmt(old.get("gross_total_income")),
                 self._fmt(new.get("gross_total_income"))],
                ["Total Deductions",
                 self._fmt(old.get("total_deductions")),
                 self._fmt(new.get("total_deductions"))],
                ["Taxable Income",
                 self._fmt(old.get("taxable_income")),
                 self._fmt(new.get("taxable_income"))],
                ["Tax on Income",
                 self._fmt(old.get("tax_on_income")),
                 self._fmt(new.get("tax_on_income"))],
                ["Surcharge",
                 self._fmt(old.get("surcharge")),
                 self._fmt(new.get("surcharge"))],
                ["Education Cess (4%)",
                 self._fmt(old.get("education_cess")),
                 self._fmt(new.get("education_cess"))],
                ["Total Tax Liability",
                 self._fmt(old.get("total_tax_liability")),
                 self._fmt(new.get("total_tax_liability"))],
            ]

            t = Table(comparison_data, colWidths=[200, 130, 130])
            t.setStyle(TableStyle([
                # Header row
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                # Body
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                # Alternating row colors
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f7fafc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f7fafc"), colors.white]),
                # Last row highlight
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ebf8ff")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                # Grid
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 10))

            # Recommendation
            recommended = comp_json.get("recommended", "")
            savings = comp_json.get("savings", "0")
            if recommended:
                regime_label = "Old Regime" if "old" in recommended else "New Regime"
                elements.append(Paragraph(
                    f"<b>Recommended:</b> {regime_label} "
                    f"(saves Rs. {savings})",
                    normal_style,
                ))
        else:
            # Generic computation display
            elements.append(Paragraph(f"Computation: {comp_type.replace('_', ' ').title()}", heading_style))
            for key, value in comp_json.items():
                if key != "type":
                    elements.append(Paragraph(f"<b>{key}:</b> {value}", normal_style))

        # ── Footer ───────────────────────────────────────────────────
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            f"Generated by {self.firm_name} via OperatorOS | "
            f"{datetime.now().strftime('%d %B %Y, %H:%M IST')}",
            ParagraphStyle("Footer", parent=normal_style, fontSize=8, textColor=colors.grey),
        ))
        elements.append(Paragraph(
            "This is a computer-generated report and does not require a signature.",
            ParagraphStyle("Disclaimer", parent=normal_style, fontSize=7, textColor=colors.grey),
        ))

        doc.build(elements)
        logger.info("Generated PDF report: %s", filepath)
        return filepath

    def generate_client_summary(
        self,
        client: Any,
        tasks: list,
        computations: list,
    ) -> str:
        """Generate a comprehensive client summary PDF."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"client_summary_{client.id}.pdf"
        filepath = str(PDF_OUTPUT_DIR / filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=25 * mm,
            bottomMargin=20 * mm,
        )

        styles = getSampleStyleSheet()
        elements = []

        # Title
        elements.append(Paragraph(
            f"Client Summary — {client.firm_name}",
            ParagraphStyle("Title", parent=styles["Title"], fontSize=16,
                          textColor=colors.HexColor("#1a365d")),
        ))
        elements.append(Spacer(1, 10))

        # Client info
        elements.append(Paragraph("Client Details", styles["Heading2"]))
        info = [
            ["PAN:", client.pan or "N/A"],
            ["GSTIN:", client.gstin or "N/A"],
            ["Entity Type:", client.entity_type.value if client.entity_type else "N/A"],
            ["Contact:", client.contact_person or "N/A"],
            ["Email:", client.email or "N/A"],
        ]
        t = Table(info, colWidths=[100, 380])
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # Compliance tasks
        if tasks:
            elements.append(Paragraph("Compliance Tasks", styles["Heading2"]))
            task_data = [["Task Type", "Due Date", "Status"]]
            for task in tasks[:20]:
                task_data.append([
                    task.task_type.value.replace("_", " ").title(),
                    task.due_date.strftime("%d/%m/%Y") if task.due_date else "N/A",
                    task.status.value.replace("_", " ").title(),
                ])
            t = Table(task_data, colWidths=[200, 120, 120])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 12))

        # Recent computations
        if computations:
            elements.append(Paragraph("Recent Tax Computations", styles["Heading2"]))
            comp_data = [["AY", "Regime", "Tax Liability", "Date"]]
            for comp in computations[:10]:
                comp_data.append([
                    comp.assessment_year or "N/A",
                    comp.regime.value if comp.regime else "N/A",
                    self._fmt(comp.tax_liability),
                    comp.created_at.strftime("%d/%m/%Y") if comp.created_at else "N/A",
                ])
            t = Table(comp_data, colWidths=[80, 80, 150, 120])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(t)

        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            f"Generated by {self.firm_name} via OperatorOS | "
            f"{datetime.now().strftime('%d %B %Y')}",
            ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8, textColor=colors.grey),
        ))

        doc.build(elements)
        logger.info("Generated client summary PDF: %s", filepath)
        return filepath

    @staticmethod
    def _fmt(value: Any) -> str:
        """Format a numeric value as Indian currency."""
        if value is None:
            return "Rs. 0"
        try:
            n = float(value) if not isinstance(value, (int, float)) else value
            if n < 0:
                return f"(Rs. {abs(n):,.2f})"
            return f"Rs. {n:,.2f}"
        except (ValueError, TypeError):
            return str(value)
