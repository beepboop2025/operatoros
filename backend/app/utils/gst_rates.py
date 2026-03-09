"""
GST rate lookup — common goods & services with HSN/SAC codes.

Includes:
  - Standard rate buckets (0%, 5%, 12%, 18%, 28%)
  - Common items/services with their HSN/SAC
  - Composition scheme rates
  - Inter-state vs intra-state split logic
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional


def _d(val: str | int | float) -> Decimal:
    return Decimal(str(val))


# =========================================================================== #
#  DATA STRUCTURES
# =========================================================================== #

@dataclass(frozen=True)
class GSTRateEntry:
    """A single GST rate entry for a good or service."""

    hsn_sac: str                   # HSN code (goods) or SAC code (services)
    description: str
    rate: Decimal                  # Total GST rate (CGST + SGST or IGST)
    category: str = "service"      # "goods" or "service"
    notes: str = ""


# =========================================================================== #
#  STANDARD RATE BUCKETS
# =========================================================================== #

GST_RATE_EXEMPT = _d("0.00")
GST_RATE_5 = _d("0.05")
GST_RATE_12 = _d("0.12")
GST_RATE_18 = _d("0.18")
GST_RATE_28 = _d("0.28")

STANDARD_RATES = [GST_RATE_EXEMPT, GST_RATE_5, GST_RATE_12, GST_RATE_18, GST_RATE_28]


# =========================================================================== #
#  COMMON GOODS & SERVICES RATE TABLE
# =========================================================================== #

GST_RATE_TABLE: List[GSTRateEntry] = [
    # ---------- Exempt / Nil ----------
    GSTRateEntry("0401", "Fresh milk (unprocessed)", _d("0.00"), "goods",
                 "Nil rate — Schedule I"),
    GSTRateEntry("1006", "Rice (not pre-packaged/labelled)", _d("0.00"), "goods"),
    GSTRateEntry("1001", "Wheat (not pre-packaged/labelled)", _d("0.00"), "goods"),
    GSTRateEntry("0703", "Fresh vegetables", _d("0.00"), "goods"),
    GSTRateEntry("9992", "Education services by educational institution", _d("0.00"), "service"),
    GSTRateEntry("9993", "Healthcare services by clinical establishment", _d("0.00"), "service"),

    # ---------- 5% ----------
    GSTRateEntry("9963", "Restaurant services (non-AC, no liquor licence)", _d("0.05"), "service",
                 "No ITC available. Standalone restaurants."),
    GSTRateEntry("9954", "Construction — affordable housing (PMAY)", _d("0.05"), "service",
                 "1% effective rate under affordable housing scheme (no ITC). "
                 "Listed as 5% with 2/3 deemed land abatement."),
    GSTRateEntry("4901", "Printed books, newspapers", _d("0.05"), "goods"),
    GSTRateEntry("9988", "Job work services (goods)", _d("0.05"), "service",
                 "5% for goods other than specified (textiles, food products, etc.)."),
    GSTRateEntry("2710", "Aviation turbine fuel (ATF)", _d("0.05"), "goods",
                 "Currently outside GST; listed for reference if included."),
    GSTRateEntry("9986", "Transport of goods by road (GTA — opting for 5%)", _d("0.05"), "service",
                 "GTA opting for 5% — no ITC available."),

    # ---------- 12% ----------
    GSTRateEntry("9963", "Restaurant services in hotel (tariff ₹1,000–₹7,500)", _d("0.12"), "service",
                 "With ITC available."),
    GSTRateEntry("9954", "Construction — non-affordable residential (new)", _d("0.12"), "service",
                 "5% effective rate (with land abatement), no ITC. "
                 "Actual GST rate 12% with deemed 1/3 land value."),
    GSTRateEntry("8471", "Computers / laptops", _d("0.12"), "goods",
                 "Reduced from 18% to 12%."),
    GSTRateEntry("9972", "Renting of residential dwelling (for business)", _d("0.12"), "service",
                 "W.e.f. 18-07-2022. Reverse charge on registered recipient."),
    GSTRateEntry("9965", "Goods transport agency (GTA) — opting for 12%", _d("0.12"), "service",
                 "GTA opting for 12% — ITC available."),

    # ---------- 18% ----------
    GSTRateEntry("998311", "IT software services", _d("0.18"), "service",
                 "Information technology software development and consulting."),
    GSTRateEntry("998312", "IT infrastructure / cloud hosting", _d("0.18"), "service"),
    GSTRateEntry("998211", "Legal services", _d("0.18"), "service",
                 "Reverse charge if provided by individual advocate to business entity."),
    GSTRateEntry("998231", "Accounting, auditing and bookkeeping services", _d("0.18"), "service"),
    GSTRateEntry("998214", "Management consulting services", _d("0.18"), "service"),
    GSTRateEntry("997212", "Renting of commercial property", _d("0.18"), "service"),
    GSTRateEntry("9954", "Works contract — general", _d("0.18"), "service",
                 "Works contract for non-government, non-affordable housing."),
    GSTRateEntry("9963", "Restaurant in hotel (tariff > ₹7,500)", _d("0.18"), "service",
                 "With ITC."),
    GSTRateEntry("9967", "Courier services", _d("0.18"), "service"),
    GSTRateEntry("9973", "Leasing / rental of machinery without operator", _d("0.18"), "service"),
    GSTRateEntry("998599", "Financial services (banking, NBFC)", _d("0.18"), "service"),
    GSTRateEntry("9985", "Insurance services", _d("0.18"), "service"),
    GSTRateEntry("7318", "Iron / steel fasteners (screws, bolts)", _d("0.18"), "goods"),
    GSTRateEntry("8517", "Telecom equipment, mobile phones (> ₹2,000)", _d("0.18"), "goods"),

    # ---------- 28% ----------
    GSTRateEntry("8703", "Motor vehicles (cars, SUVs)", _d("0.28"), "goods",
                 "Plus compensation cess: 1%–22% depending on type/engine capacity."),
    GSTRateEntry("2402", "Cigarettes, cigars", _d("0.28"), "goods",
                 "Plus compensation cess."),
    GSTRateEntry("2201", "Aerated beverages / carbonated water", _d("0.28"), "goods",
                 "Plus compensation cess 12%."),
    GSTRateEntry("9996", "Betting, gambling, lottery, casino", _d("0.28"), "service",
                 "28% on full face value of bet (w.e.f. 01-10-2023)."),
    GSTRateEntry("3304", "Cosmetics, perfumes, deodorants", _d("0.28"), "goods"),
    GSTRateEntry("8528", "Television sets (> 32 inches)", _d("0.28"), "goods"),
    GSTRateEntry("8418", "Refrigerators, freezers", _d("0.28"), "goods"),
    GSTRateEntry("8450", "Washing machines", _d("0.28"), "goods"),
    GSTRateEntry("8415", "Air conditioners", _d("0.28"), "goods"),
]


# =========================================================================== #
#  COMPOSITION SCHEME RATES (Section 10 of CGST Act)
# =========================================================================== #

@dataclass(frozen=True)
class CompositionRate:
    """Composition scheme GST rates (total of CGST + SGST)."""
    category: str
    rate: Decimal
    notes: str = ""


COMPOSITION_SCHEME_RATES: List[CompositionRate] = [
    CompositionRate("manufacturer", _d("0.01"),
                    "1% total (0.5% CGST + 0.5% SGST). Turnover ≤ ₹1.5 crore."),
    CompositionRate("trader", _d("0.01"),
                    "1% total (0.5% CGST + 0.5% SGST). Turnover ≤ ₹1.5 crore."),
    CompositionRate("restaurant", _d("0.05"),
                    "5% total (2.5% CGST + 2.5% SGST). Turnover ≤ ₹1.5 crore."),
    CompositionRate("service_provider", _d("0.06"),
                    "6% total (3% CGST + 3% SGST). Turnover ≤ ₹50 lakh. "
                    "Available to service providers under notification."),
]


# =========================================================================== #
#  LOOKUP HELPERS
# =========================================================================== #

# Index by HSN/SAC for fast lookup
_RATE_BY_HSN: Dict[str, List[GSTRateEntry]] = {}
for _entry in GST_RATE_TABLE:
    _RATE_BY_HSN.setdefault(_entry.hsn_sac, []).append(_entry)


def lookup_by_hsn(hsn_sac: str) -> List[GSTRateEntry]:
    """Return all GST rate entries matching a given HSN/SAC code."""
    return _RATE_BY_HSN.get(hsn_sac, [])


def lookup_by_keyword(keyword: str) -> List[GSTRateEntry]:
    """Search GST rate entries by keyword in description (case-insensitive)."""
    keyword_lower = keyword.lower()
    return [e for e in GST_RATE_TABLE if keyword_lower in e.description.lower()]


def lookup_by_rate(rate: Decimal) -> List[GSTRateEntry]:
    """Return all entries at a specific GST rate (e.g. 0.18 for 18%)."""
    return [e for e in GST_RATE_TABLE if e.rate == rate]


def compute_gst_split(
    taxable_value: Decimal,
    rate: Decimal,
    is_inter_state: bool,
) -> Dict[str, Decimal]:
    """Compute GST components on a taxable value.

    For intra-state supply: CGST = SGST = rate/2 each.
    For inter-state supply: IGST = rate.

    Returns dict with keys: taxable_value, cgst_rate, cgst, sgst_rate, sgst,
    igst_rate, igst, total_gst, invoice_total.
    """
    total_gst = (taxable_value * rate).quantize(Decimal("0.01"))

    if is_inter_state:
        return {
            "taxable_value": taxable_value,
            "cgst_rate": Decimal("0"),
            "cgst": Decimal("0"),
            "sgst_rate": Decimal("0"),
            "sgst": Decimal("0"),
            "igst_rate": rate,
            "igst": total_gst,
            "total_gst": total_gst,
            "invoice_total": taxable_value + total_gst,
        }
    else:
        half_rate = rate / 2
        half_gst = (taxable_value * half_rate).quantize(Decimal("0.01"))
        # Handle rounding — ensure CGST + SGST = total_gst
        cgst = half_gst
        sgst = total_gst - cgst
        return {
            "taxable_value": taxable_value,
            "cgst_rate": half_rate,
            "cgst": cgst,
            "sgst_rate": half_rate,
            "sgst": sgst,
            "igst_rate": Decimal("0"),
            "igst": Decimal("0"),
            "total_gst": total_gst,
            "invoice_total": taxable_value + total_gst,
        }
