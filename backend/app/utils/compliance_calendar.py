"""
Compliance calendar generator — statutory deadlines for Indian entities.

Generates a list of compliance tasks for a given financial year,
entity type, and audit applicability.

Usage:
    tasks = generate_compliance_calendar(
        entity_type="private_limited",
        audit_applicable=True,
        fy="2025-26",
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List


@dataclass
class ComplianceEvent:
    """A single compliance deadline."""

    task_type: str       # matches ComplianceTask.task_type enum
    description: str
    due_date: date
    form_name: str       # e.g. "GSTR-1", "26Q", "ITR-3"
    statute: str         # e.g. "Income Tax", "GST", "Companies Act"
    notes: str = ""


def _parse_fy(fy: str) -> tuple[int, int]:
    """Parse '2025-26' → (2025, 2026)."""
    parts = fy.split("-")
    start_year = int(parts[0])
    end_year_short = int(parts[1])
    # Handle both '2025-26' and '2025-2026' formats
    if end_year_short < 100:
        end_year = start_year // 100 * 100 + end_year_short
    else:
        end_year = end_year_short
    return start_year, end_year


def generate_compliance_calendar(
    entity_type: str,
    audit_applicable: bool,
    fy: str,
) -> List[dict]:
    """Generate compliance tasks for a financial year.

    Args:
        entity_type: One of 'individual', 'huf', 'partnership', 'llp',
                     'private_limited', 'public_limited', 'trust',
                     'society', 'aop', 'boi'.
        audit_applicable: Whether tax audit u/s 44AB is applicable.
        fy: Financial year string, e.g. '2025-26'.

    Returns:
        List of dicts, each with keys: task_type, description, due_date,
        form_name, statute, notes.
    """
    start_year, end_year = _parse_fy(fy)
    ay = f"{end_year}-{(end_year + 1) % 100:02d}"
    events: List[ComplianceEvent] = []

    # --------------------------------------------------------------------- #
    #  ADVANCE TAX  (all assesses with tax liability ≥ ₹10,000)
    # --------------------------------------------------------------------- #
    # Senior citizens without business income are exempt from advance tax,
    # but we include all 4 installments; caller can filter.
    events.extend([
        ComplianceEvent(
            task_type="advance_tax",
            description=f"Advance tax — 1st installment (15% of estimated tax) for AY {ay}",
            due_date=date(start_year, 6, 15),
            form_name="Challan 280",
            statute="Income Tax",
            notes="At least 15% of estimated tax liability.",
        ),
        ComplianceEvent(
            task_type="advance_tax",
            description=f"Advance tax — 2nd installment (45% cumulative) for AY {ay}",
            due_date=date(start_year, 9, 15),
            form_name="Challan 280",
            statute="Income Tax",
            notes="Cumulative 45% of estimated tax liability.",
        ),
        ComplianceEvent(
            task_type="advance_tax",
            description=f"Advance tax — 3rd installment (75% cumulative) for AY {ay}",
            due_date=date(start_year, 12, 15),
            form_name="Challan 280",
            statute="Income Tax",
            notes="Cumulative 75% of estimated tax liability.",
        ),
        ComplianceEvent(
            task_type="advance_tax",
            description=f"Advance tax — 4th installment (100%) for AY {ay}",
            due_date=date(end_year, 3, 15),
            form_name="Challan 280",
            statute="Income Tax",
            notes="100% of estimated tax liability.",
        ),
    ])

    # --------------------------------------------------------------------- #
    #  TDS RETURNS  (quarterly — applicable to deductors)
    # --------------------------------------------------------------------- #
    tds_quarters = [
        ("Q1 (Apr-Jun)", date(start_year, 7, 31), "Q1"),
        ("Q2 (Jul-Sep)", date(start_year, 10, 31), "Q2"),
        ("Q3 (Oct-Dec)", date(end_year, 1, 31), "Q3"),
        ("Q4 (Jan-Mar)", date(end_year, 5, 31), "Q4"),
    ]
    for label, due, qtr in tds_quarters:
        events.append(ComplianceEvent(
            task_type="tds_return",
            description=f"TDS return {label} — Form 24Q/26Q/27Q for FY {fy}",
            due_date=due,
            form_name="24Q/26Q/27Q",
            statute="Income Tax",
            notes=f"Quarter {qtr}. Form 24Q for salary, 26Q for non-salary, 27Q for NRI payments.",
        ))

    # TDS certificates
    events.extend([
        ComplianceEvent(
            task_type="tds_return",
            description=f"Issue TDS certificate (Form 16) for FY {fy}",
            due_date=date(end_year, 6, 15),
            form_name="Form 16",
            statute="Income Tax",
            notes="Annual salary TDS certificate to employees.",
        ),
        ComplianceEvent(
            task_type="tds_return",
            description=f"Issue TDS certificate (Form 16A) — Q4 for FY {fy}",
            due_date=date(end_year, 6, 15),
            form_name="Form 16A",
            statute="Income Tax",
            notes="Quarterly non-salary TDS certificate. Other quarters: within 15 days of filing return.",
        ),
    ])

    # --------------------------------------------------------------------- #
    #  GST RETURNS  (monthly GSTR-1, GSTR-3B; annual GSTR-9)
    # --------------------------------------------------------------------- #
    if entity_type not in ("individual", "huf"):
        # Monthly GSTR-1 and GSTR-3B
        for month_offset in range(12):
            m = (4 + month_offset - 1) % 12 + 1  # Apr=4 ... Mar=3
            yr = start_year if m >= 4 else end_year
            next_m = m % 12 + 1
            next_yr = yr if next_m > 1 else yr + 1

            month_name = date(yr, m, 1).strftime("%B %Y")

            # GSTR-1: 11th of next month
            events.append(ComplianceEvent(
                task_type="gst_return",
                description=f"GSTR-1 for {month_name}",
                due_date=date(next_yr, next_m, 11),
                form_name="GSTR-1",
                statute="GST",
                notes="Outward supplies. Due by 11th of following month.",
            ))

            # GSTR-3B: 20th of next month
            events.append(ComplianceEvent(
                task_type="gst_return",
                description=f"GSTR-3B for {month_name}",
                due_date=date(next_yr, next_m, 20),
                form_name="GSTR-3B",
                statute="GST",
                notes="Summary return + tax payment. Due by 20th of following month.",
            ))

        # Annual GST return (GSTR-9) — due 31 December
        events.append(ComplianceEvent(
            task_type="gst_return",
            description=f"Annual GST return (GSTR-9) for FY {fy}",
            due_date=date(end_year, 12, 31),
            form_name="GSTR-9",
            statute="GST",
            notes="Annual return. GSTR-9C (reconciliation) if turnover > ₹5 crore.",
        ))

    # --------------------------------------------------------------------- #
    #  INCOME TAX RETURN FILING
    # --------------------------------------------------------------------- #
    if audit_applicable:
        itr_due = date(end_year, 10, 31)
        itr_notes = "Due date for entities requiring audit u/s 44AB."
    elif entity_type in ("private_limited", "public_limited", "llp") and not audit_applicable:
        itr_due = date(end_year, 10, 31)
        itr_notes = "Company / LLP — due 31 October. Even without audit, companies file by Oct 31."
    else:
        itr_due = date(end_year, 7, 31)
        itr_notes = "Non-audit case. Individuals / HUFs / firms without audit."

    events.append(ComplianceEvent(
        task_type="itr_filing",
        description=f"Income Tax Return for AY {ay}",
        due_date=itr_due,
        form_name="ITR-1/2/3/4/5/6",
        statute="Income Tax",
        notes=itr_notes,
    ))

    # Belated / revised return deadline
    events.append(ComplianceEvent(
        task_type="itr_filing",
        description=f"Last date for belated/revised ITR for AY {ay}",
        due_date=date(end_year, 12, 31),
        form_name="ITR (Revised/Belated)",
        statute="Income Tax",
        notes="u/s 139(4) belated or u/s 139(5) revised. Penalty u/s 234F applies for belated.",
    ))

    # --------------------------------------------------------------------- #
    #  TAX AUDIT  (Section 44AB)
    # --------------------------------------------------------------------- #
    if audit_applicable:
        events.append(ComplianceEvent(
            task_type="tax_audit",
            description=f"Tax Audit Report for AY {ay}",
            due_date=date(end_year, 9, 30),
            form_name="Form 3CA-3CD / 3CB-3CD",
            statute="Income Tax",
            notes="Tax audit report to be filed by 30 September. "
                  "Form 3CA-3CD if accounts already audited under other law, else 3CB-3CD.",
        ))

    # --------------------------------------------------------------------- #
    #  TRANSFER PRICING REPORT  (if applicable — for entities with
    #  international transactions > ₹1 Cr or specified domestic
    #  transactions > ₹20 Cr)
    # --------------------------------------------------------------------- #
    if entity_type in ("private_limited", "public_limited"):
        events.append(ComplianceEvent(
            task_type="tax_audit",
            description=f"Transfer Pricing Report (Form 3CEB) for AY {ay}",
            due_date=date(end_year, 10, 31),
            form_name="Form 3CEB",
            statute="Income Tax",
            notes="Required if international transactions > ₹1 Cr "
                  "or specified domestic transactions > ₹20 Cr.",
        ))

    # --------------------------------------------------------------------- #
    #  ROC FILINGS  (Companies Act — for companies)
    # --------------------------------------------------------------------- #
    is_company = entity_type in ("private_limited", "public_limited")

    if is_company:
        # AOC-4: Financial statements
        events.append(ComplianceEvent(
            task_type="roc_filing",
            description=f"AOC-4 — Financial statements filing for FY {fy}",
            due_date=date(end_year, 10, 30),
            form_name="AOC-4",
            statute="Companies Act",
            notes="Within 30 days of AGM. AGM must be held within 6 months from FY end (by Sep 30).",
        ))

        # MGT-7: Annual return
        events.append(ComplianceEvent(
            task_type="roc_filing",
            description=f"MGT-7 — Annual return filing for FY {fy}",
            due_date=date(end_year, 11, 29),
            form_name="MGT-7",
            statute="Companies Act",
            notes="Within 60 days of AGM.",
        ))

        # ADT-1: Auditor appointment
        events.append(ComplianceEvent(
            task_type="roc_filing",
            description=f"ADT-1 — Auditor appointment for FY {fy}",
            due_date=date(start_year, 10, 14),
            form_name="ADT-1",
            statute="Companies Act",
            notes="Within 15 days of AGM where auditor is appointed.",
        ))

        # DPT-3: Return of deposits
        events.append(ComplianceEvent(
            task_type="roc_filing",
            description=f"DPT-3 — Return of deposits for FY {fy}",
            due_date=date(end_year, 6, 30),
            form_name="DPT-3",
            statute="Companies Act",
            notes="Annual return of deposits or transactions not considered as deposits.",
        ))

        # MSME-1: Outstanding payment to MSMEs
        events.extend([
            ComplianceEvent(
                task_type="roc_filing",
                description=f"MSME-1 — H1 (Apr-Sep) outstanding payments for FY {fy}",
                due_date=date(start_year, 10, 31),
                form_name="MSME-1",
                statute="Companies Act",
                notes="Half-yearly return if payments to MSME suppliers exceed 45 days.",
            ),
            ComplianceEvent(
                task_type="roc_filing",
                description=f"MSME-1 — H2 (Oct-Mar) outstanding payments for FY {fy}",
                due_date=date(end_year, 4, 30),
                form_name="MSME-1",
                statute="Companies Act",
                notes="Half-yearly return if payments to MSME suppliers exceed 45 days.",
            ),
        ])

    # --------------------------------------------------------------------- #
    #  DIR-3 KYC  (Directors of companies / designated partners of LLPs)
    # --------------------------------------------------------------------- #
    if is_company or entity_type == "llp":
        events.append(ComplianceEvent(
            task_type="dir3_kyc",
            description=f"DIR-3 KYC — Director / Partner KYC for FY {fy}",
            due_date=date(end_year, 9, 30),
            form_name="DIR-3 KYC / DIR-3 KYC-WEB",
            statute="Companies Act",
            notes="Annual KYC for every director/designated partner holding DIN. "
                  "DIR-3 KYC-WEB if already filed once with no changes.",
        ))

    # --------------------------------------------------------------------- #
    #  LLP FORMS
    # --------------------------------------------------------------------- #
    if entity_type == "llp":
        # Form 11: Annual return
        events.append(ComplianceEvent(
            task_type="llp_form",
            description=f"LLP Form 11 — Annual return for FY {fy}",
            due_date=date(end_year, 5, 30),
            form_name="Form 11",
            statute="LLP Act",
            notes="Within 60 days of close of FY.",
        ))

        # Form 8: Statement of accounts and solvency
        events.append(ComplianceEvent(
            task_type="llp_form",
            description=f"LLP Form 8 — Statement of accounts for FY {fy}",
            due_date=date(end_year, 10, 30),
            form_name="Form 8",
            statute="LLP Act",
            notes="Within 30 days from end of 6 months of FY (i.e., 30 October).",
        ))

    # --------------------------------------------------------------------- #
    #  Serialize to dicts
    # --------------------------------------------------------------------- #
    return sorted(
        [
            {
                "task_type": e.task_type,
                "description": e.description,
                "due_date": e.due_date.isoformat(),
                "form_name": e.form_name,
                "statute": e.statute,
                "notes": e.notes,
            }
            for e in events
        ],
        key=lambda x: x["due_date"],
    )
