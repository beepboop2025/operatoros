"""
Recent important CBDT and CBIC circulars relevant to CA practice.

Format:
    {circular_no: {date, subject, key_points, sections_affected}}

These are curated for quick reference during notice drafting, advisory work,
and compliance calendar generation.
"""

CBDT_CIRCULARS: dict[str, dict] = {
    # ── CBDT Circulars (Income Tax) ─────────────────────────────────────────
    "Circular 01/2025": {
        "date": "2025-01-10",
        "subject": "Guidelines for compounding of offences under Direct Tax Laws",
        "key_points": [
            "Revised guidelines for compounding of offences under IT Act",
            "Simplified application process",
            "Time limit for disposal of compounding application: 12 months",
            "Compounding charges revised based on nature of offence",
            "Repeat offenders may be denied compounding",
        ],
        "sections_affected": ["276C", "276CC", "277", "278"],
    },
    "Circular 02/2025": {
        "date": "2025-02-15",
        "subject": "Clarification on TDS obligations for payments to non-residents through e-commerce platforms",
        "key_points": [
            "E-commerce operators liable for TDS on payments to non-resident sellers",
            "Rate: 5% unless DTAA rate is lower",
            "Certificate from AO u/s 197 for lower deduction",
            "Reporting in Form 26Q with specific codes",
        ],
        "sections_affected": ["194O", "195", "206AA"],
    },
    "Circular 03/2025": {
        "date": "2025-03-20",
        "subject": "Updated return u/s 139(8A) — FAQs and clarifications",
        "key_points": [
            "Updated return cannot be filed to claim refund or increase refund",
            "Additional tax must be paid before filing",
            "One updated return per assessment year",
            "Cannot file if reassessment proceedings initiated",
            "Utility updated for filing updated returns on e-filing portal",
        ],
        "sections_affected": ["139(8A)", "140B"],
    },
    "Circular 04/2025": {
        "date": "2025-04-01",
        "subject": "New tax regime (Section 115BAC) — Revised slab rates effective AY 2026-27",
        "key_points": [
            "Revised slabs: 0-4L nil, 4-8L 5%, 8-12L 10%, 12-16L 15%, 16-20L 20%, 20-24L 25%, >24L 30%",
            "Standard deduction increased to Rs. 75,000",
            "Rebate u/s 87A: up to Rs. 60,000 for income up to Rs. 12,00,000",
            "Marginal relief for income marginally exceeding Rs. 12 lakh",
            "Default regime for individuals — opt out for old regime",
        ],
        "sections_affected": ["115BAC", "87A"],
    },
    "Circular 05/2025": {
        "date": "2025-05-15",
        "subject": "Condonation of delay in filing Form 10-IC/10-ID for manufacturing companies",
        "key_points": [
            "CBDT empowered to condone delay in filing Form 10-IC (Section 115BAA)",
            "Form 10-ID for Section 115BAB (new manufacturing companies)",
            "Applications to be filed with jurisdictional Principal Commissioner",
            "Genuine hardship and reasonable cause to be established",
        ],
        "sections_affected": ["115BAA", "115BAB", "119(2)(b)"],
    },
    "Circular 06/2025": {
        "date": "2025-06-01",
        "subject": "Tolerance limit for Section 43B(h) — MSME payments",
        "key_points": [
            "Payments to MSME suppliers must be within 45 days (with agreement) or 15 days",
            "Amounts outstanding beyond due date disallowed under Section 43B(h)",
            "MSME registration on Udyam portal is determinative",
            "Effective from AY 2024-25 onwards",
            "No tolerance limit — strict compliance required",
        ],
        "sections_affected": ["43B(h)"],
    },
    "Circular 07/2025": {
        "date": "2025-07-10",
        "subject": "Guidelines for faceless assessment and appeals",
        "key_points": [
            "All assessments u/s 143(3) to be faceless (with exceptions)",
            "NaFAC (National Faceless Assessment Centre) procedures updated",
            "Video conferencing facility for personal hearing",
            "Transfer pricing cases excluded from faceless regime",
            "Commissioner (Appeals) also faceless from specified date",
        ],
        "sections_affected": ["143(3A)", "143(3B)", "144B", "250"],
    },
    "Circular 08/2025": {
        "date": "2025-08-20",
        "subject": "Safe harbour rules for international transactions — updated thresholds",
        "key_points": [
            "Revised operating margins for IT/ITeS: 17-18% range",
            "Knowledge Process Outsourcing: 20-22% range",
            "Intra-group loans: SOFR + 150-300 bps depending on credit rating",
            "Corporate guarantee: 1-4% depending on related party rating",
            "Valid for 3 consecutive years",
        ],
        "sections_affected": ["92CB", "92CC", "92CD"],
    },
    "Circular 09/2025": {
        "date": "2025-09-15",
        "subject": "Clarification on angel tax provisions — Section 56(2)(viib)",
        "key_points": [
            "Section 56(2)(viib) — scope narrowed post Budget 2024",
            "Non-resident investors excluded from angel tax from AY 2025-26",
            "Valuation methodologies: DCF or NAV (Rule 11UA)",
            "DPIIT-recognized startups exempt (with conditions)",
            "5 prescribed valuation methods available",
        ],
        "sections_affected": ["56(2)(viib)", "68"],
    },
    "Circular 10/2025": {
        "date": "2025-10-01",
        "subject": "TDS on virtual digital assets (VDA) — operational guidelines",
        "key_points": [
            "TDS at 1% on transfer of VDA u/s 194S",
            "Buyer is the deductor",
            "Threshold: Rs. 10,000 (Rs. 50,000 for specified persons)",
            "Loss from VDA cannot be set off against any other income",
            "No deduction for cost of acquisition other than cost of acquisition",
        ],
        "sections_affected": ["194S", "115BBH", "2(47A)"],
    },
    "Circular 11/2025": {
        "date": "2025-11-01",
        "subject": "Charitable trusts — revised compliance framework",
        "key_points": [
            "Mandatory registration u/s 12AB (5-year registration)",
            "Form 10A/10AB online filing mandatory",
            "85% of income must be applied in the year of receipt",
            "Accumulation u/s 11(2): only with Form 10 filed before due date",
            "Corpus donations: only from registered trusts to registered trusts",
        ],
        "sections_affected": ["11", "12A", "12AB", "13"],
    },
    "Circular 12/2025": {
        "date": "2025-12-15",
        "subject": "Extension of due date for filing belated/revised returns for AY 2025-26",
        "key_points": [
            "Due date for belated return u/s 139(4) extended to 15-Jan-2026",
            "Due date for revised return u/s 139(5) also extended",
            "Applicable to all categories of taxpayers",
            "System issues on e-filing portal cited as reason",
        ],
        "sections_affected": ["139(4)", "139(5)", "119(2)(b)"],
    },
    "Circular 01/2026": {
        "date": "2026-01-10",
        "subject": "Clarification on capital gains tax changes effective AY 2025-26",
        "key_points": [
            "LTCG on all assets: 12.5% (previously 20% with indexation)",
            "Indexation benefit removed for all assets acquired after 23-Jul-2024",
            "Listed equity/MF: 12.5% above Rs. 1.25 lakh",
            "STCG on listed equity: 20% (previously 15%)",
            "Holding period: listed equity 12 months, immovable property 24 months",
            "Grandfathering for assets acquired before 23-Jul-2024 (with certain conditions)",
        ],
        "sections_affected": ["112", "112A", "111A", "48", "55"],
    },
}


CBIC_CIRCULARS: dict[str, dict] = {
    # ── CBIC Circulars (GST) ────────────────────────────────────────────────
    "Circular 230/24/2025-GST": {
        "date": "2025-03-15",
        "subject": "Clarification on ITC reversal for exempt supplies — Rule 42/43",
        "key_points": [
            "Proportionate reversal methodology clarified",
            "Annual reversal computation in GSTR-9 mandatory",
            "Credit notes impact on ITC reversal explained",
            "Banking/financial services companies: 50% ITC reversal option continues",
        ],
        "sections_affected": ["Section 17(2)", "Rule 42", "Rule 43"],
    },
    "Circular 231/25/2025-GST": {
        "date": "2025-05-01",
        "subject": "E-invoicing threshold reduced to Rs. 5 crore",
        "key_points": [
            "E-invoicing mandatory for businesses with turnover > Rs. 5 crore",
            "Effective from 01-Aug-2025",
            "B2B and export invoices must be e-invoiced",
            "Penalties for non-compliance: 100% tax or Rs. 10,000 (higher)",
            "Invoice Reference Number (IRN) mandatory",
        ],
        "sections_affected": ["Section 31", "Rule 48(4)"],
    },
    "Circular 232/26/2025-GST": {
        "date": "2025-07-01",
        "subject": "GST on corporate guarantees between related parties",
        "key_points": [
            "GST applicable on corporate guarantee even without consideration",
            "Taxable value: 1% of guarantee amount per annum",
            "Applicable between related parties / distinct persons",
            "No GST if guarantee is on behalf of subsidiary for secured loan from bank",
        ],
        "sections_affected": ["Section 15", "Rule 28"],
    },
    "Circular 233/27/2025-GST": {
        "date": "2025-09-01",
        "subject": "Amnesty scheme for revocation of cancelled GST registrations",
        "key_points": [
            "Registrations cancelled for non-filing can be revoked",
            "Application window: 01-Sep-2025 to 31-Dec-2025",
            "All pending returns must be filed with late fees",
            "Condonation of delay in filing revocation application",
            "Late fee cap: Rs. 500 per return (Rs. 250 CGST + Rs. 250 SGST) for nil returns",
        ],
        "sections_affected": ["Section 29", "Section 30"],
    },
    "Circular 234/28/2025-GST": {
        "date": "2025-10-15",
        "subject": "Clarification on place of supply for transportation of goods",
        "key_points": [
            "Domestic transport: location of person initiating movement",
            "International: destination of goods for import, place of dispatch for export",
            "GTA services: place of supply as per Section 12(8)",
            "Multimodal transport: treated as single supply",
        ],
        "sections_affected": ["Section 10 (IGST)", "Section 12 (IGST)"],
    },
    "Circular 235/29/2025-GST": {
        "date": "2025-11-01",
        "subject": "GSTR-2B reconciliation — auto-populated ITC",
        "key_points": [
            "GSTR-2B is the sole basis for ITC claim from AY onwards",
            "Discrepancy between books and GSTR-2B: 10% provisional ITC removed",
            "Suppliers must file GSTR-1 by due date for buyer to get ITC",
            "Invoice Management System (IMS) introduced for accept/reject",
            "Annual reconciliation in GSTR-9 / GSTR-9C mandatory",
        ],
        "sections_affected": ["Section 16(2)(aa)", "Rule 36(4)"],
    },
    "Circular 236/30/2026-GST": {
        "date": "2026-01-15",
        "subject": "Interest on delayed GST payment — gross vs net liability",
        "key_points": [
            "Interest payable on gross tax liability (not net of ITC)",
            "Amendment to Section 50 effective retrospectively from 01-Jul-2017",
            "Interest on delayed filing: 18% per annum",
            "Interest on undue ITC claim: 24% per annum",
            "Automatic computation in GST portal",
        ],
        "sections_affected": ["Section 50"],
    },
    "Circular 237/31/2026-GST": {
        "date": "2026-02-01",
        "subject": "RCM on renting of commercial property by unregistered persons",
        "key_points": [
            "GST on renting of commercial property under RCM from 01-Oct-2024",
            "Tenant liable to pay GST under reverse charge",
            "Applicable when landlord is unregistered",
            "ITC available to tenant on RCM payment",
            "Notification 09/2024-CT(R) reference",
        ],
        "sections_affected": ["Section 9(3)", "Section 9(4)"],
    },
}


# Combined reference for convenience
ALL_CIRCULARS = {**CBDT_CIRCULARS, **CBIC_CIRCULARS}
