"""
TDS (Tax Deducted at Source) and TCS (Tax Collected at Source) rate tables.

Every entry is a ``TDSEntry`` dataclass with the section, description,
thresholds, applicable rates, and explanatory notes.

Without-PAN rule (Section 206AA):
  Rate = higher of 20% OR twice the applicable rate.
  For TCS (206CC): 5% or twice the rate, whichever is higher.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional


@dataclass(frozen=True)
class TDSEntry:
    """A single TDS/TCS rate entry."""

    section: str
    description: str
    threshold: Optional[Decimal]              # annual threshold (None = no threshold)
    rate_with_pan: Optional[Decimal]          # None means "at slab rates"
    rate_without_pan: Decimal
    recipient_types: List[str] = field(default_factory=list)
    notes: str = ""
    is_tcs: bool = False                      # True for TCS entries


def _d(val: str | int | float) -> Decimal:
    return Decimal(str(val))


# =========================================================================== #
#  TDS RATES TABLE (Section 192–195)
# =========================================================================== #

TDS_RATES: List[TDSEntry] = [
    # --- Section 192: Salary ---
    TDSEntry(
        section="192",
        description="Salary",
        threshold=None,
        rate_with_pan=None,          # at applicable slab rates
        rate_without_pan=_d("0.20"),
        recipient_types=["individual"],
        notes="TDS at average rate of tax on estimated salary income. "
              "Employer must consider declared deductions & regime choice.",
    ),

    # --- Section 194A: Interest other than securities ---
    TDSEntry(
        section="194A",
        description="Interest other than on securities (banks/post office)",
        threshold=_d("40000"),       # ₹50,000 for senior citizens
        rate_with_pan=_d("0.10"),
        rate_without_pan=_d("0.20"),
        recipient_types=["individual", "huf", "firm", "company"],
        notes="Threshold ₹40,000 (₹50,000 for resident senior citizens u/s 194A). "
              "Applies to FD interest, recurring deposit interest, etc.",
    ),

    # --- Section 194B: Lottery / crossword puzzle ---
    TDSEntry(
        section="194B",
        description="Winnings from lottery, crossword puzzles, card games",
        threshold=_d("10000"),
        rate_with_pan=_d("0.30"),
        rate_without_pan=_d("0.30"),   # already at 30%, so 206AA still = 30%
        recipient_types=["individual", "huf", "firm", "company"],
        notes="No surcharge / cess — flat 30%. TDS on amount exceeding ₹10,000.",
    ),

    # --- Section 194C: Contractor ---
    TDSEntry(
        section="194C",
        description="Payment to contractor (individual / HUF)",
        threshold=_d("30000"),       # single payment; ₹1,00,000 aggregate in FY
        rate_with_pan=_d("0.01"),    # 1% for individual/HUF
        rate_without_pan=_d("0.20"),
        recipient_types=["individual", "huf"],
        notes="Single payment > ₹30,000 or aggregate > ₹1,00,000 in FY. "
              "Rate is 1% for individual/HUF, 2% for others.",
    ),
    TDSEntry(
        section="194C",
        description="Payment to contractor (other than individual / HUF)",
        threshold=_d("30000"),
        rate_with_pan=_d("0.02"),    # 2% for non-individual
        rate_without_pan=_d("0.20"),
        recipient_types=["firm", "company", "llp", "trust"],
        notes="Single payment > ₹30,000 or aggregate > ₹1,00,000 in FY.",
    ),

    # --- Section 194D: Insurance commission ---
    TDSEntry(
        section="194D",
        description="Insurance commission",
        threshold=_d("15000"),
        rate_with_pan=_d("0.05"),
        rate_without_pan=_d("0.20"),
        recipient_types=["individual", "huf", "firm", "company"],
        notes="5% for all recipients (w.e.f. 01-04-2020).",
    ),

    # --- Section 194H: Commission or brokerage ---
    TDSEntry(
        section="194H",
        description="Commission or brokerage",
        threshold=_d("15000"),
        rate_with_pan=_d("0.05"),
        rate_without_pan=_d("0.20"),
        recipient_types=["individual", "huf", "firm", "company"],
        notes="Threshold ₹15,000 per FY.",
    ),

    # --- Section 194I(a): Rent — plant & machinery ---
    TDSEntry(
        section="194I(a)",
        description="Rent — plant and machinery",
        threshold=_d("240000"),
        rate_with_pan=_d("0.02"),
        rate_without_pan=_d("0.20"),
        recipient_types=["individual", "huf", "firm", "company"],
        notes="Threshold ₹2,40,000 per FY (w.e.f. AY 2024-25).",
    ),

    # --- Section 194I(b): Rent — land/building/furniture ---
    TDSEntry(
        section="194I(b)",
        description="Rent — land, building, or furniture/fittings",
        threshold=_d("240000"),
        rate_with_pan=_d("0.10"),
        rate_without_pan=_d("0.20"),
        recipient_types=["individual", "huf", "firm", "company"],
        notes="Threshold ₹2,40,000 per FY (w.e.f. AY 2024-25).",
    ),

    # --- Section 194IA: Transfer of immovable property ---
    TDSEntry(
        section="194IA",
        description="Transfer of immovable property (other than agricultural land)",
        threshold=_d("5000000"),
        rate_with_pan=_d("0.01"),
        rate_without_pan=_d("0.20"),
        recipient_types=["individual", "huf", "firm", "company"],
        notes="Applicable when consideration ≥ ₹50 lakh. Buyer deducts TDS.",
    ),

    # --- Section 194IB: Rent by individual / HUF ---
    TDSEntry(
        section="194IB",
        description="Rent paid by individual / HUF (not liable for audit)",
        threshold=_d("50000"),       # per month
        rate_with_pan=_d("0.05"),
        rate_without_pan=_d("0.20"),
        recipient_types=["individual", "huf"],
        notes="Monthly rent exceeding ₹50,000. Deductible from last month's rent in FY.",
    ),

    # --- Section 194J: Professional / Technical fees ---
    TDSEntry(
        section="194J(a)",
        description="Fees for technical services / call centre",
        threshold=_d("30000"),
        rate_with_pan=_d("0.02"),
        rate_without_pan=_d("0.20"),
        recipient_types=["individual", "huf", "firm", "company"],
        notes="2% for technical services and call centre payments.",
    ),
    TDSEntry(
        section="194J(b)",
        description="Professional fees / royalty / non-compete fees",
        threshold=_d("30000"),
        rate_with_pan=_d("0.10"),
        rate_without_pan=_d("0.20"),
        recipient_types=["individual", "huf", "firm", "company"],
        notes="10% for professional services, royalty, director fees, etc.",
    ),

    # --- Section 194K: Income from units of MF ---
    TDSEntry(
        section="194K",
        description="Income from units of mutual fund",
        threshold=_d("5000"),
        rate_with_pan=_d("0.10"),
        rate_without_pan=_d("0.20"),
        recipient_types=["individual", "huf", "firm", "company"],
        notes="Threshold ₹5,000 per FY. Only on dividend income.",
    ),

    # --- Section 194Q: Purchase of goods ---
    TDSEntry(
        section="194Q",
        description="Purchase of goods",
        threshold=_d("5000000"),
        rate_with_pan=_d("0.001"),   # 0.1%
        rate_without_pan=_d("0.05"),
        recipient_types=["individual", "huf", "firm", "company"],
        notes="Buyer with turnover > ₹10 crore. On amount exceeding ₹50 lakh. "
              "Does not apply if TCS u/s 206C(1H) applies.",
    ),

    # --- Section 194R: Perquisites / benefits to business ---
    TDSEntry(
        section="194R",
        description="Perquisites or benefits to residents (business/profession)",
        threshold=_d("20000"),
        rate_with_pan=_d("0.10"),
        rate_without_pan=_d("0.20"),
        recipient_types=["individual", "huf", "firm", "company"],
        notes="On value of perquisite/benefit exceeding ₹20,000 in FY. "
              "W.e.f. 01-07-2022.",
    ),

    # --- Section 194S: Virtual digital assets ---
    TDSEntry(
        section="194S",
        description="Transfer of virtual digital assets (crypto, NFTs)",
        threshold=_d("50000"),       # ₹10,000 for specified persons
        rate_with_pan=_d("0.01"),
        rate_without_pan=_d("0.20"),
        recipient_types=["individual", "huf", "firm", "company"],
        notes="Threshold ₹50,000 (₹10,000 if payer is specified person — exchange, etc.). "
              "W.e.f. 01-07-2022.",
    ),

    # --- Section 195: Payment to NRI ---
    TDSEntry(
        section="195",
        description="Payment to non-resident (other than salary)",
        threshold=None,
        rate_with_pan=None,          # rates vary by nature and DTAA
        rate_without_pan=_d("0.20"),
        recipient_types=["non_resident"],
        notes="Rates vary by nature of income and applicable DTAA. "
              "Common: Interest 20%, Royalty 10%, FTS 10%. "
              "Payer must obtain TAN and file Form 27Q.",
    ),
]


# =========================================================================== #
#  TCS RATES TABLE (Section 206C)
# =========================================================================== #

TCS_RATES: List[TDSEntry] = [
    TDSEntry(
        section="206C(1)",
        description="Sale of specified goods (timber, tendu leaves, minerals, etc.)",
        threshold=None,
        rate_with_pan=_d("0.025"),   # varies 1%-5%, using 2.5% as common
        rate_without_pan=_d("0.05"),
        recipient_types=["individual", "huf", "firm", "company"],
        notes="Rates vary: timber 2.5%, tendu leaves 5%, minerals 2%, scrap 1%.",
        is_tcs=True,
    ),
    TDSEntry(
        section="206C(1F)",
        description="Sale of motor vehicle (value > ₹10 lakh)",
        threshold=_d("1000000"),
        rate_with_pan=_d("0.01"),
        rate_without_pan=_d("0.05"),
        recipient_types=["individual", "huf", "firm", "company"],
        notes="On sale consideration exceeding ₹10 lakh.",
        is_tcs=True,
    ),
    TDSEntry(
        section="206C(1G)",
        description="Overseas remittance under LRS",
        threshold=_d("700000"),
        rate_with_pan=_d("0.05"),    # 5% general, 20% for non-education/medical
        rate_without_pan=_d("0.10"),
        recipient_types=["individual"],
        notes="0.5% for education loan, 5% for education (no loan) up to ₹10L, "
              "20% for other purposes above ₹7L threshold. "
              "No TCS on first ₹7 lakh in aggregate.",
        is_tcs=True,
    ),
    TDSEntry(
        section="206C(1H)",
        description="Sale of goods (seller turnover > ₹10 Cr)",
        threshold=_d("5000000"),
        rate_with_pan=_d("0.001"),   # 0.1%
        rate_without_pan=_d("0.01"),
        recipient_types=["individual", "huf", "firm", "company"],
        notes="On amount exceeding ₹50 lakh. "
              "Not applicable if buyer is liable to deduct TDS u/s 194Q.",
        is_tcs=True,
    ),
]


# =========================================================================== #
#  LOOKUP HELPERS
# =========================================================================== #

# Index by section for fast lookup
_TDS_BY_SECTION: Dict[str, List[TDSEntry]] = {}
for _entry in TDS_RATES + TCS_RATES:
    _TDS_BY_SECTION.setdefault(_entry.section, []).append(_entry)


def lookup_tds_section(section: str) -> List[TDSEntry]:
    """Return all TDS/TCS entries for a given section string (e.g. '194C')."""
    return _TDS_BY_SECTION.get(section, [])


def lookup_tds_by_payment_type(keyword: str) -> List[TDSEntry]:
    """Search TDS entries by keyword in description (case-insensitive)."""
    keyword_lower = keyword.lower()
    return [
        e for e in (TDS_RATES + TCS_RATES)
        if keyword_lower in e.description.lower()
    ]


def compute_without_pan_rate(rate_with_pan: Optional[Decimal], is_tcs: bool = False) -> Decimal:
    """Compute the applicable rate when PAN is not furnished.

    Section 206AA (TDS): higher of 20% or twice the specified rate.
    Section 206CC (TCS): higher of 5% or twice the specified rate.
    """
    if rate_with_pan is None:
        # Slab-rate based — 206AA prescribes 20% flat
        return _d("0.20")

    twice = rate_with_pan * 2
    floor = _d("0.05") if is_tcs else _d("0.20")
    return max(twice, floor)
