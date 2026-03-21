"""
Tax computation engine — the core money-making service.

All monetary calculations use ``Decimal`` to avoid floating-point errors.
Every function returns step-by-step working in a structured dict so the
front-end can render a transparent, auditable computation worksheet.

Public API
----------
- compute_income_tax(request) → IncomeTaxResponse
- compute_tds(request) → TDSResponse
- compute_gst(request) → GSTResponse
- compute_capital_gains(request) → CapitalGainsResponse
- compute_interest_234(request) → InterestResponse
- compute_hra_exemption(…) → dict
- compute_depreciation(…) → list[dict]
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING, ROUND_FLOOR
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.utils.tax_constants import (
    NEW_REGIME_SLABS,
    OLD_REGIME_SLABS,
    STANDARD_DEDUCTION_NEW_REGIME,
    STANDARD_DEDUCTION_OLD_REGIME,
    REBATE_87A_OLD_LIMIT,
    REBATE_87A_OLD_MAX,
    REBATE_87A_NEW,
    OLD_REGIME_SURCHARGE,
    NEW_REGIME_SURCHARGE,
    CESS_RATE,
    SEC_80C_LIMIT,
    SEC_80CCD1B_LIMIT,
    SEC_80D_SELF_BELOW_60,
    SEC_80D_SELF_SENIOR,
    SEC_80D_PARENTS_BELOW_60,
    SEC_80D_PARENTS_SENIOR,
    SEC_80TTA_LIMIT,
    SEC_80TTB_LIMIT,
    HRA_METRO_PERCENT,
    HRA_NON_METRO_PERCENT,
    HRA_SALARY_PERCENT,
    LTCG_EQUITY_RATE,
    LTCG_EQUITY_EXEMPTION,
    STCG_EQUITY_RATE,
    LTCG_OTHER_RATE,
    LTCG_OTHER_RATE_WITH_INDEXATION,
    HOLDING_PERIOD_LISTED_EQUITY_MONTHS,
    HOLDING_PERIOD_UNLISTED_SHARES_MONTHS,
    HOLDING_PERIOD_IMMOVABLE_PROPERTY_MONTHS,
    HOLDING_PERIOD_OTHER_MONTHS_NEW,
    ADVANCE_TAX_SCHEDULE,
    INTEREST_234A_RATE,
    INTEREST_234B_RATE,
    INTEREST_234C_RATE,
    LATE_FEE_234F_ABOVE_5L,
    LATE_FEE_234F_UPTO_5L,
    DEPRECIATION_RATES,
    ADDITIONAL_DEPRECIATION_RATE,
    SlabTable,
    INF,
)
from app.utils.cii_table import CIINotFoundError, compute_indexed_cost, get_cii
from app.utils.tds_rates import (
    TDS_RATES,
    lookup_tds_section,
    lookup_tds_by_payment_type,
    compute_without_pan_rate,
)
from app.utils.gst_rates import (
    compute_gst_split,
    lookup_by_hsn,
    lookup_by_keyword as gst_lookup_by_keyword,
)

_ZERO = Decimal("0")
_ONE = Decimal("1")
_TWO_PLACES = Decimal("0.01")


def _q(val: Decimal) -> Decimal:
    """Quantize to 2 decimal places, rounding half-up."""
    return val.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def _ceil_to_ten(val: Decimal) -> Decimal:
    """Round UP to the nearest ₹10 (tax rounding rule)."""
    return (val / 10).to_integral_value(rounding=ROUND_CEILING) * 10


# =========================================================================== #
#  REQUEST / RESPONSE DATACLASSES
# =========================================================================== #

class AgeCategory(str, Enum):
    below_60 = "below_60"
    senior_60_to_80 = "60_to_80"
    super_senior_80_plus = "80_plus"


class AssetType(str, Enum):
    listed_equity = "listed_equity"
    equity_mutual_fund = "equity_mutual_fund"
    unlisted_shares = "unlisted_shares"
    immovable_property = "immovable_property"
    gold = "gold"
    debt_mutual_fund = "debt_mutual_fund"
    other = "other"


@dataclass
class Deductions:
    """Chapter VI-A deductions for old regime."""
    sec_80c: Decimal = _ZERO               # PPF, ELSS, LIC, etc.
    sec_80ccc: Decimal = _ZERO             # Pension fund
    sec_80ccd_1: Decimal = _ZERO           # Employee NPS (within 80C limit)
    sec_80ccd_1b: Decimal = _ZERO          # Additional NPS (₹50,000)
    sec_80ccd_2: Decimal = _ZERO           # Employer NPS (no cap, allowed in both regimes)
    sec_80d_self: Decimal = _ZERO          # Medical insurance — self
    sec_80d_parents: Decimal = _ZERO       # Medical insurance — parents
    sec_80dd: Decimal = _ZERO              # Disabled dependent
    sec_80e: Decimal = _ZERO               # Education loan interest
    sec_80eea: Decimal = _ZERO             # Home loan interest (first-time buyer)
    sec_80g: Decimal = _ZERO               # Donations
    sec_80gg: Decimal = _ZERO              # Rent paid (no HRA)
    sec_80tta: Decimal = _ZERO             # Savings interest (non-senior)
    sec_80ttb: Decimal = _ZERO             # Deposit interest (senior)
    sec_80u: Decimal = _ZERO               # Self-disability
    sec_24b: Decimal = _ZERO               # Home loan interest (₹2L for self-occupied)
    other_deductions: Decimal = _ZERO


@dataclass
class IncomeTaxRequest:
    """Input for income tax computation."""
    assessment_year: str                       # "2025-26" or "2026-27"
    age_category: AgeCategory
    gross_salary: Decimal = _ZERO
    income_from_house_property: Decimal = _ZERO   # can be negative (loss)
    income_from_business: Decimal = _ZERO
    short_term_capital_gains: Decimal = _ZERO     # taxed at slab (non-equity STCG)
    short_term_capital_gains_equity: Decimal = _ZERO  # 15%/20% special rate
    long_term_capital_gains: Decimal = _ZERO      # special rate
    income_from_other_sources: Decimal = _ZERO
    agricultural_income: Decimal = _ZERO          # exempt but affects slab for > ₹5,000
    deductions: Deductions = field(default_factory=Deductions)
    tds_already_paid: Decimal = _ZERO
    advance_tax_paid: Decimal = _ZERO
    self_assessment_tax_paid: Decimal = _ZERO


@dataclass
class RegimeResult:
    """Computation result for one regime."""
    regime: str
    gross_total_income: Decimal
    standard_deduction: Decimal
    chapter_via_deductions: Decimal
    deduction_details: Dict[str, Decimal]
    total_income: Decimal                    # after deductions, rounded to ₹10
    tax_on_normal_income: Decimal
    tax_on_stcg_equity: Decimal
    tax_on_ltcg: Decimal
    total_tax_before_rebate: Decimal
    rebate_87a: Decimal
    tax_after_rebate: Decimal
    surcharge: Decimal
    surcharge_rate: Decimal
    cess: Decimal
    total_tax_liability: Decimal
    taxes_paid: Decimal
    net_tax_payable: Decimal                 # positive = due, negative = refund
    slab_working: List[Dict[str, str]]       # step-by-step slab calculation
    marginal_relief_applied: bool = False
    marginal_relief_amount: Decimal = _ZERO


@dataclass
class IncomeTaxResponse:
    """Output of income tax computation — both regimes + recommendation."""
    old_regime: RegimeResult
    new_regime: RegimeResult
    recommended_regime: str                  # "old" or "new"
    tax_saving: Decimal                      # how much the better regime saves
    computation_json: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TDSRequest:
    section: str                             # e.g. "194C"
    payment_amount: Decimal
    has_pan: bool = True
    recipient_type: str = "individual"       # to pick correct sub-rate
    is_senior_citizen: bool = False           # affects 194A threshold


@dataclass
class TDSResponse:
    section: str
    description: str
    threshold: Optional[Decimal]
    applicable_rate: Decimal
    tds_amount: Decimal
    notes: str
    working: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GSTRequest:
    taxable_value: Decimal
    hsn_sac: Optional[str] = None
    gst_rate: Optional[Decimal] = None       # explicit rate overrides HSN lookup
    place_of_supply_state: str = ""
    place_of_origin_state: str = ""
    description: Optional[str] = None


@dataclass
class GSTResponse:
    taxable_value: Decimal
    gst_rate: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    total_gst: Decimal
    invoice_total: Decimal
    is_inter_state: bool
    hsn_sac: str
    description: str
    working: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapitalGainsRequest:
    asset_type: AssetType
    purchase_date: date
    sale_date: date
    purchase_cost: Decimal
    sale_consideration: Decimal
    improvement_cost: Decimal = _ZERO
    purchase_fy: Optional[str] = None        # for CII lookup; auto-derived if None
    sale_fy: Optional[str] = None
    expenses_on_transfer: Decimal = _ZERO    # brokerage, stamp duty on sale, etc.


@dataclass
class CapitalGainsResponse:
    asset_type: str
    holding_period_days: int
    holding_period_months: int
    is_long_term: bool
    classification: str                      # "LTCG" or "STCG"
    purchase_cost: Decimal
    indexed_cost: Optional[Decimal]          # None if not applicable
    sale_consideration: Decimal
    expenses_on_transfer: Decimal
    capital_gain: Decimal
    exemption_available: Decimal             # e.g. ₹1.25L for listed equity LTCG
    taxable_gain: Decimal
    tax_rate: Optional[Decimal]              # None = slab rates
    tax_amount: Decimal
    # For pre-July-2024 property: both options
    option_with_indexation: Optional[Dict[str, Decimal]] = None
    option_without_indexation: Optional[Dict[str, Decimal]] = None
    recommended_option: Optional[str] = None
    available_exemptions: List[str] = field(default_factory=list)
    working: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InterestRequest:
    total_tax_liability: Decimal
    tds_paid: Decimal = _ZERO
    advance_tax_paid: Decimal = _ZERO
    advance_tax_dates: Optional[List[Dict[str, Any]]] = None
    # e.g. [{"date": "2025-06-15", "amount": 25000}, ...]
    due_date_of_filing: date = date(2026, 7, 31)
    actual_date_of_filing: Optional[date] = None
    assessment_year: str = "2026-27"


@dataclass
class InterestResponse:
    interest_234a: Decimal
    interest_234b: Decimal
    interest_234c: Decimal
    total_interest: Decimal
    late_fee_234f: Decimal
    working_234a: Dict[str, Any] = field(default_factory=dict)
    working_234b: Dict[str, Any] = field(default_factory=dict)
    working_234c: Dict[str, Any] = field(default_factory=dict)


# =========================================================================== #
#  INTERNAL HELPERS
# =========================================================================== #

def _compute_tax_from_slabs(taxable_income: Decimal, slabs: SlabTable) -> Tuple[Decimal, List[Dict[str, str]]]:
    """Apply progressive slab rates and return (tax, step-by-step working)."""
    tax = _ZERO
    working: List[Dict[str, str]] = []

    for lower, upper, rate in slabs:
        if taxable_income <= lower:
            break

        slab_upper = min(taxable_income, upper) if upper != INF else taxable_income
        taxable_in_slab = slab_upper - lower

        if taxable_in_slab <= _ZERO:
            continue

        slab_tax = _q(taxable_in_slab * rate)
        tax += slab_tax

        upper_label = "∞" if upper == INF else f"₹{upper:,.0f}"
        working.append({
            "slab": f"₹{lower:,.0f} – {upper_label}",
            "rate": f"{rate * 100:.1f}%",
            "taxable_amount": f"₹{taxable_in_slab:,.2f}",
            "tax": f"₹{slab_tax:,.2f}",
        })

    return tax, working


def _get_surcharge_rate(total_income: Decimal, surcharge_slabs: SlabTable) -> Decimal:
    """Determine the surcharge rate based on total income."""
    for lower, upper, rate in surcharge_slabs:
        if lower <= total_income < upper:
            return rate
        if upper == INF and total_income >= lower:
            return rate
    return _ZERO


def _apply_marginal_relief(
    income: Decimal,
    tax_before_surcharge: Decimal,
    surcharge: Decimal,
    surcharge_threshold: Decimal,
    slabs: SlabTable,
) -> Tuple[Decimal, Decimal, bool]:
    """Apply marginal relief on surcharge.

    Principle: The total tax + surcharge on income just above a surcharge
    threshold should not exceed the tax on income at the threshold PLUS the
    excess income above the threshold.

    Returns: (adjusted_surcharge, marginal_relief_amount, was_applied)
    """
    if surcharge <= _ZERO or income <= surcharge_threshold:
        return surcharge, _ZERO, False

    excess_income = income - surcharge_threshold
    # Tax at the threshold (no surcharge applies AT the threshold)
    tax_at_threshold, _ = _compute_tax_from_slabs(surcharge_threshold, slabs)

    total_with_surcharge = tax_before_surcharge + surcharge
    max_total = tax_at_threshold + excess_income

    relief = max(total_with_surcharge - max_total, _ZERO)
    if relief > _ZERO:
        adjusted_surcharge = max(surcharge - relief, _ZERO)
        return adjusted_surcharge, relief, True

    return surcharge, _ZERO, False


def _compute_old_regime_deductions(deductions: Deductions, age: AgeCategory) -> Tuple[Decimal, Dict[str, Decimal]]:
    """Compute total Chapter VI-A deductions for old regime with limits.

    Returns: (total_deduction, breakdown_dict)
    """
    details: Dict[str, Decimal] = {}
    total = _ZERO

    # 80C + 80CCC + 80CCD(1) — combined limit ₹1,50,000
    combined_80c = min(
        deductions.sec_80c + deductions.sec_80ccc + deductions.sec_80ccd_1,
        SEC_80C_LIMIT,
    )
    details["80C/80CCC/80CCD(1)"] = combined_80c
    total += combined_80c

    # 80CCD(1B) — additional NPS, ₹50,000
    ccd1b = min(deductions.sec_80ccd_1b, SEC_80CCD1B_LIMIT)
    details["80CCD(1B)"] = ccd1b
    total += ccd1b

    # 80CCD(2) — employer NPS (no fixed limit, 10%/14% of salary — we trust the input)
    details["80CCD(2)"] = deductions.sec_80ccd_2
    total += deductions.sec_80ccd_2

    # 80D — medical insurance
    is_senior = age in (AgeCategory.senior_60_to_80, AgeCategory.super_senior_80_plus)
    self_limit = SEC_80D_SELF_SENIOR if is_senior else SEC_80D_SELF_BELOW_60
    parent_limit = SEC_80D_PARENTS_SENIOR  # conservative — parent age unknown, use max
    d_self = min(deductions.sec_80d_self, self_limit)
    d_parents = min(deductions.sec_80d_parents, parent_limit)
    details["80D (self)"] = d_self
    details["80D (parents)"] = d_parents
    total += d_self + d_parents

    # 80DD — disabled dependent
    details["80DD"] = deductions.sec_80dd
    total += deductions.sec_80dd

    # 80E — education loan interest (no limit)
    details["80E"] = deductions.sec_80e
    total += deductions.sec_80e

    # 80EEA — home loan interest first-time buyer
    eea = min(deductions.sec_80eea, Decimal("150000"))
    details["80EEA"] = eea
    total += eea

    # 80G — donations (we trust the computed amount)
    details["80G"] = deductions.sec_80g
    total += deductions.sec_80g

    # 80GG — rent paid (no HRA), max ₹5,000/month
    gg = min(deductions.sec_80gg, Decimal("60000"))
    details["80GG"] = gg
    total += gg

    # 80TTA / 80TTB
    if is_senior:
        ttb = min(deductions.sec_80ttb, SEC_80TTB_LIMIT)
        details["80TTB"] = ttb
        total += ttb
    else:
        tta = min(deductions.sec_80tta, SEC_80TTA_LIMIT)
        details["80TTA"] = tta
        total += tta

    # 80U — self-disability
    details["80U"] = deductions.sec_80u
    total += deductions.sec_80u

    # Section 24(b) — home loan interest (not Chapter VI-A but applied to HP income,
    # included here for completeness; caller may already have adjusted HP income)
    details["24(b)"] = deductions.sec_24b

    # Other deductions
    details["Other"] = deductions.other_deductions
    total += deductions.other_deductions

    return total, details


def _round_total_income(income: Decimal) -> Decimal:
    """Round total income DOWN to nearest ₹10 (as per IT Act)."""
    return (income / 10).to_integral_value(rounding=ROUND_FLOOR) * 10


# =========================================================================== #
#  PUBLIC API
# =========================================================================== #

def compute_income_tax(request: IncomeTaxRequest) -> IncomeTaxResponse:
    """Compute income tax under both old and new regimes, compare, recommend.

    Returns an ``IncomeTaxResponse`` with full step-by-step working for
    each regime.
    """
    ay = request.assessment_year

    # ---- Gross Total Income (common to both regimes) ----
    gross_salary = request.gross_salary
    hp_income = request.income_from_house_property
    biz_income = request.income_from_business
    stcg_slab = request.short_term_capital_gains       # taxed at slab
    stcg_equity = request.short_term_capital_gains_equity
    ltcg = request.long_term_capital_gains
    other_income = request.income_from_other_sources

    # Normal income (taxed at slab rates)
    gross_normal_income = gross_salary + hp_income + biz_income + stcg_slab + other_income

    taxes_paid = request.tds_already_paid + request.advance_tax_paid + request.self_assessment_tax_paid

    # ---- Compute OLD regime ----
    old_result = _compute_regime(
        regime="old",
        ay=ay,
        age_category=request.age_category,
        gross_salary=gross_salary,
        gross_normal_income=gross_normal_income,
        hp_income=hp_income,
        stcg_equity=stcg_equity,
        ltcg=ltcg,
        deductions=request.deductions,
        taxes_paid=taxes_paid,
    )

    # ---- Compute NEW regime ----
    new_result = _compute_regime(
        regime="new",
        ay=ay,
        age_category=request.age_category,
        gross_salary=gross_salary,
        gross_normal_income=gross_normal_income,
        hp_income=hp_income,
        stcg_equity=stcg_equity,
        ltcg=ltcg,
        deductions=request.deductions,
        taxes_paid=taxes_paid,
    )

    # ---- Recommend ----
    if old_result.total_tax_liability <= new_result.total_tax_liability:
        recommended = "old"
        saving = new_result.total_tax_liability - old_result.total_tax_liability
    else:
        recommended = "new"
        saving = old_result.total_tax_liability - new_result.total_tax_liability

    return IncomeTaxResponse(
        old_regime=old_result,
        new_regime=new_result,
        recommended_regime=recommended,
        tax_saving=saving,
        computation_json={
            "assessment_year": ay,
            "age_category": request.age_category.value,
            "recommended_regime": recommended,
            "tax_saving": str(saving),
            "old_regime_tax": str(old_result.total_tax_liability),
            "new_regime_tax": str(new_result.total_tax_liability),
        },
    )


def _compute_regime(
    regime: str,
    ay: str,
    age_category: AgeCategory,
    gross_salary: Decimal,
    gross_normal_income: Decimal,
    hp_income: Decimal,
    stcg_equity: Decimal,
    ltcg: Decimal,
    deductions: Deductions,
    taxes_paid: Decimal,
) -> RegimeResult:
    """Compute tax for a single regime (old or new)."""

    # ---- Standard Deduction ----
    if regime == "old":
        std_ded = min(STANDARD_DEDUCTION_OLD_REGIME, gross_salary) if gross_salary > _ZERO else _ZERO
    else:
        std_ded = min(STANDARD_DEDUCTION_NEW_REGIME, gross_salary) if gross_salary > _ZERO else _ZERO

    income_after_std_ded = gross_normal_income - std_ded

    # ---- Chapter VI-A Deductions (old regime only) ----
    if regime == "old":
        chapter_via, ded_details = _compute_old_regime_deductions(deductions, age_category)
        # 80CCD(2) — employer NPS — available in both regimes, so subtract it regardless
    else:
        # New regime: only 80CCD(2) is allowed
        chapter_via = deductions.sec_80ccd_2
        ded_details = {"80CCD(2)": deductions.sec_80ccd_2}

    total_income_normal = max(income_after_std_ded - chapter_via, _ZERO)
    total_income_normal = _round_total_income(total_income_normal)

    gross_total_income = gross_normal_income + stcg_equity + ltcg

    # ---- Tax on normal income from slabs ----
    if regime == "old":
        age_key = age_category.value
        slabs = OLD_REGIME_SLABS[age_key]
    else:
        if ay not in NEW_REGIME_SLABS:
            # Default to latest available
            ay_key = max(NEW_REGIME_SLABS.keys())
        else:
            ay_key = ay
        slabs = NEW_REGIME_SLABS[ay_key]

    tax_on_normal, slab_working = _compute_tax_from_slabs(total_income_normal, slabs)

    # ---- Tax on special-rate income ----
    tax_on_stcg_eq = _q(stcg_equity * STCG_EQUITY_RATE) if stcg_equity > _ZERO else _ZERO

    ltcg_taxable = max(ltcg - LTCG_EQUITY_EXEMPTION, _ZERO)
    tax_on_ltcg = _q(ltcg_taxable * LTCG_EQUITY_RATE) if ltcg_taxable > _ZERO else _ZERO

    total_tax_before_rebate = tax_on_normal + tax_on_stcg_eq + tax_on_ltcg

    # ---- Section 87A Rebate ----
    rebate = _ZERO
    if regime == "old":
        # Old regime: rebate up to ₹12,500 if total income ≤ ₹5 lakh
        if total_income_normal <= REBATE_87A_OLD_LIMIT:
            rebate = min(tax_on_normal, REBATE_87A_OLD_MAX)
    else:
        # New regime: AY-dependent
        rebate_info = REBATE_87A_NEW.get(ay)
        if rebate_info and total_income_normal <= rebate_info["limit"]:
            rebate = min(tax_on_normal, rebate_info["max_rebate"])

    tax_after_rebate = max(total_tax_before_rebate - rebate, _ZERO)

    # ---- Surcharge ----
    total_income_for_surcharge = total_income_normal + stcg_equity + ltcg
    if regime == "old":
        surcharge_slabs = OLD_REGIME_SURCHARGE
    else:
        surcharge_slabs = NEW_REGIME_SURCHARGE

    surcharge_rate = _get_surcharge_rate(total_income_for_surcharge, surcharge_slabs)

    # Special surcharge rules for capital gains:
    # LTCG/STCG on equity — surcharge max 15%
    # We apply surcharge on each component separately for accuracy.
    # Simplified approach: surcharge on total tax
    surcharge = _q(tax_after_rebate * surcharge_rate)

    # ---- Marginal Relief (Section 87A(2)) ----
    # Principle: when income marginally exceeds a surcharge threshold,
    # total tax + surcharge must not exceed (tax at threshold + excess income).
    # Apply at each surcharge threshold to find the best relief.
    marginal_applied = False
    marginal_amount = _ZERO

    if surcharge > _ZERO:
        # Identify which threshold was just crossed
        surcharge_thresholds = [lower for lower, _upper, rate in surcharge_slabs if rate > _ZERO]
        for threshold in surcharge_thresholds:
            if total_income_for_surcharge > threshold:
                adjusted, relief, applied = _apply_marginal_relief(
                    income=total_income_for_surcharge,
                    tax_before_surcharge=tax_after_rebate,
                    surcharge=surcharge,
                    surcharge_threshold=threshold,
                    slabs=slabs,
                )
                if applied and relief > marginal_amount:
                    surcharge = adjusted
                    marginal_amount = relief
                    marginal_applied = True

    # ---- Cess ----
    cess = _q((tax_after_rebate + surcharge) * CESS_RATE)

    total_tax_liability = _ceil_to_ten(tax_after_rebate + surcharge + cess)

    net_payable = total_tax_liability - taxes_paid

    return RegimeResult(
        regime=regime,
        gross_total_income=gross_total_income,
        standard_deduction=std_ded,
        chapter_via_deductions=chapter_via,
        deduction_details=ded_details,
        total_income=total_income_normal,
        tax_on_normal_income=tax_on_normal,
        tax_on_stcg_equity=tax_on_stcg_eq,
        tax_on_ltcg=tax_on_ltcg,
        total_tax_before_rebate=total_tax_before_rebate,
        rebate_87a=rebate,
        tax_after_rebate=tax_after_rebate,
        surcharge=surcharge,
        surcharge_rate=surcharge_rate,
        cess=cess,
        total_tax_liability=total_tax_liability,
        taxes_paid=taxes_paid,
        net_tax_payable=net_payable,
        slab_working=slab_working,
        marginal_relief_applied=marginal_applied,
        marginal_relief_amount=marginal_amount,
    )


# --------------------------------------------------------------------------- #
#  TDS Computation
# --------------------------------------------------------------------------- #

def compute_tds(request: TDSRequest) -> TDSResponse:
    """Compute TDS on a payment.

    Looks up the applicable section and rate, applies PAN/no-PAN logic,
    and returns the TDS amount with full working.
    """
    entries = lookup_tds_section(request.section)
    if not entries:
        return TDSResponse(
            section=request.section,
            description="Section not found",
            threshold=None,
            applicable_rate=_ZERO,
            tds_amount=_ZERO,
            notes=f"No TDS rate entry found for section {request.section}.",
        )

    # Pick the entry matching recipient type
    entry = entries[0]
    for e in entries:
        if request.recipient_type in e.recipient_types:
            entry = e
            break

    # Threshold check
    if entry.threshold is not None and request.payment_amount < entry.threshold:
        return TDSResponse(
            section=entry.section,
            description=entry.description,
            threshold=entry.threshold,
            applicable_rate=_ZERO,
            tds_amount=_ZERO,
            notes=f"Payment ₹{request.payment_amount:,.2f} is below threshold "
                  f"₹{entry.threshold:,.2f}. No TDS applicable.",
            working={
                "payment_amount": str(request.payment_amount),
                "threshold": str(entry.threshold),
                "result": "Below threshold — no TDS",
            },
        )

    # Determine rate
    if entry.rate_with_pan is None:
        # Slab-rate based (e.g., Section 192 salary)
        rate = None
        rate_display = "At slab rates"
    elif request.has_pan:
        rate = entry.rate_with_pan
        rate_display = f"{rate * 100:.2f}%"
    else:
        rate = compute_without_pan_rate(entry.rate_with_pan, is_tcs=entry.is_tcs)
        rate_display = f"{rate * 100:.2f}% (no PAN)"

    # Compute TDS
    if rate is None:
        tds_amount = _ZERO
        notes = (
            f"{entry.description}: TDS is at slab rates. "
            "Exact amount depends on the employee's income and regime choice. "
            f"{entry.notes}"
        )
    else:
        tds_amount = _q(request.payment_amount * rate)
        notes = (
            f"{entry.description}: {rate_display} on ₹{request.payment_amount:,.2f} = "
            f"₹{tds_amount:,.2f}. {entry.notes}"
        )

    # Senior citizen — higher threshold for 194A
    if request.section == "194A" and request.is_senior_citizen:
        senior_threshold = Decimal("50000")
        if request.payment_amount < senior_threshold:
            return TDSResponse(
                section=entry.section,
                description=entry.description,
                threshold=senior_threshold,
                applicable_rate=_ZERO,
                tds_amount=_ZERO,
                notes=f"Senior citizen — threshold is ₹50,000. Payment below threshold.",
                working={"senior_citizen_threshold": "50000"},
            )

    return TDSResponse(
        section=entry.section,
        description=entry.description,
        threshold=entry.threshold,
        applicable_rate=rate if rate is not None else _ZERO,
        tds_amount=tds_amount,
        notes=notes,
        working={
            "payment_amount": str(request.payment_amount),
            "has_pan": request.has_pan,
            "rate_with_pan": str(entry.rate_with_pan) if entry.rate_with_pan else "slab",
            "rate_without_pan": str(entry.rate_without_pan),
            "applied_rate": str(rate) if rate else "slab",
            "tds_amount": str(tds_amount),
        },
    )


# --------------------------------------------------------------------------- #
#  GST Computation
# --------------------------------------------------------------------------- #

def compute_gst(request: GSTRequest) -> GSTResponse:
    """Compute GST on a supply (goods or service).

    Determines intra-state vs inter-state based on place of supply/origin,
    applies the appropriate rate, and splits into CGST+SGST or IGST.
    """
    # Determine GST rate
    rate = request.gst_rate
    hsn = request.hsn_sac or ""
    desc = request.description or ""

    if rate is None and hsn:
        entries = lookup_by_hsn(hsn)
        if entries:
            rate = entries[0].rate
            desc = desc or entries[0].description
            hsn = entries[0].hsn_sac

    if rate is None and desc:
        entries = gst_lookup_by_keyword(desc)
        if entries:
            rate = entries[0].rate
            hsn = hsn or entries[0].hsn_sac
            desc = desc or entries[0].description

    if rate is None:
        rate = Decimal("0.18")  # default 18%
        desc = desc or "Default GST rate applied"

    # Inter-state or intra-state?
    is_inter = (
        request.place_of_supply_state.strip().lower()
        != request.place_of_origin_state.strip().lower()
    ) if request.place_of_supply_state and request.place_of_origin_state else False

    split = compute_gst_split(request.taxable_value, rate, is_inter)

    return GSTResponse(
        taxable_value=request.taxable_value,
        gst_rate=rate,
        cgst=split["cgst"],
        sgst=split["sgst"],
        igst=split["igst"],
        total_gst=split["total_gst"],
        invoice_total=split["invoice_total"],
        is_inter_state=is_inter,
        hsn_sac=hsn,
        description=desc,
        working={
            "taxable_value": str(request.taxable_value),
            "rate": str(rate),
            "is_inter_state": is_inter,
            "place_of_supply": request.place_of_supply_state,
            "place_of_origin": request.place_of_origin_state,
            "cgst_rate": str(split["cgst_rate"]),
            "sgst_rate": str(split["sgst_rate"]),
            "igst_rate": str(split["igst_rate"]),
        },
    )


# --------------------------------------------------------------------------- #
#  Capital Gains Computation
# --------------------------------------------------------------------------- #

def _derive_fy(d: date) -> str:
    """Derive FY string from a date.  April-March year."""
    if d.month >= 4:
        return f"{d.year}-{(d.year + 1) % 100:02d}"
    else:
        return f"{d.year - 1}-{d.year % 100:02d}"


def _holding_months(purchase: date, sale: date) -> int:
    """Approximate holding period in months."""
    return (sale.year - purchase.year) * 12 + (sale.month - purchase.month)


def _get_holding_threshold(asset_type: AssetType) -> int:
    """Return the months threshold for LTCG classification."""
    thresholds = {
        AssetType.listed_equity: HOLDING_PERIOD_LISTED_EQUITY_MONTHS,
        AssetType.equity_mutual_fund: HOLDING_PERIOD_LISTED_EQUITY_MONTHS,
        AssetType.unlisted_shares: HOLDING_PERIOD_UNLISTED_SHARES_MONTHS,
        AssetType.immovable_property: HOLDING_PERIOD_IMMOVABLE_PROPERTY_MONTHS,
        AssetType.gold: HOLDING_PERIOD_OTHER_MONTHS_NEW,
        AssetType.debt_mutual_fund: HOLDING_PERIOD_OTHER_MONTHS_NEW,
        AssetType.other: HOLDING_PERIOD_OTHER_MONTHS_NEW,
    }
    return thresholds.get(asset_type, HOLDING_PERIOD_OTHER_MONTHS_NEW)


def compute_capital_gains(request: CapitalGainsRequest) -> CapitalGainsResponse:
    """Compute capital gains tax with full working.

    Handles:
    - LTCG vs STCG classification based on asset type and holding period
    - CII indexation for eligible assets (pre-July 2024)
    - Grandfathering: choice of 20% with indexation or 12.5% without for
      properties acquired before 23 July 2024
    - Exemption of ₹1.25 lakh for listed equity LTCG
    - Available exemptions listing (54, 54EC, 54F)
    """
    holding_days = (request.sale_date - request.purchase_date).days
    holding_months = _holding_months(request.purchase_date, request.sale_date)
    threshold_months = _get_holding_threshold(request.asset_type)
    is_long_term = holding_months > threshold_months

    purchase_fy = request.purchase_fy or _derive_fy(request.purchase_date)
    sale_fy = request.sale_fy or _derive_fy(request.sale_date)

    classification = "LTCG" if is_long_term else "STCG"

    # Baseline gain (without indexation)
    net_sale = request.sale_consideration - request.expenses_on_transfer
    base_gain = net_sale - request.purchase_cost - request.improvement_cost

    # --- Listed equity / equity MF ---
    if request.asset_type in (AssetType.listed_equity, AssetType.equity_mutual_fund):
        if is_long_term:
            exemption = LTCG_EQUITY_EXEMPTION
            taxable = max(base_gain - exemption, _ZERO)
            tax_rate = LTCG_EQUITY_RATE
            tax = _q(taxable * tax_rate)
        else:
            exemption = _ZERO
            taxable = max(base_gain, _ZERO)
            tax_rate = STCG_EQUITY_RATE
            tax = _q(taxable * tax_rate)

        return CapitalGainsResponse(
            asset_type=request.asset_type.value,
            holding_period_days=holding_days,
            holding_period_months=holding_months,
            is_long_term=is_long_term,
            classification=classification,
            purchase_cost=request.purchase_cost,
            indexed_cost=None,
            sale_consideration=request.sale_consideration,
            expenses_on_transfer=request.expenses_on_transfer,
            capital_gain=base_gain,
            exemption_available=exemption,
            taxable_gain=taxable,
            tax_rate=tax_rate,
            tax_amount=tax,
            available_exemptions=[],
            working={
                "holding_days": holding_days,
                "holding_months": holding_months,
                "threshold_months": threshold_months,
                "net_sale_consideration": str(net_sale),
                "base_gain": str(base_gain),
                "exemption": str(exemption),
                "taxable_gain": str(taxable),
                "tax_rate": str(tax_rate),
                "tax": str(tax),
            },
        )

    # --- Other assets (property, gold, unlisted, debt MF) ---
    july_2024 = date(2024, 7, 23)

    if is_long_term:
        exemptions_list: List[str] = []

        if request.asset_type == AssetType.immovable_property:
            exemptions_list.extend([
                "Section 54 — Reinvest in residential property (within 2 years purchase / 3 years construction)",
                "Section 54EC — Invest up to ₹50 lakh in specified bonds (NHAI/REC) within 6 months",
                "Section 54F — Sale of any asset (other than house) — reinvest full consideration in house",
            ])
        elif request.asset_type in (AssetType.gold, AssetType.debt_mutual_fund, AssetType.other):
            exemptions_list.append(
                "Section 54F — Reinvest full net consideration in one residential house"
            )

        # Pre-July-2024 purchase: offer BOTH indexation options
        if request.purchase_date < july_2024 and request.asset_type in (
            AssetType.immovable_property,
            AssetType.unlisted_shares,
            AssetType.gold,
            AssetType.other,
        ):
            # Option A: 20% with indexation
            try:
                indexed_cost = compute_indexed_cost(
                    request.purchase_cost, purchase_fy, sale_fy
                )
                indexed_improvement = compute_indexed_cost(
                    request.improvement_cost, purchase_fy, sale_fy
                ) if request.improvement_cost > _ZERO else _ZERO
            except CIINotFoundError:
                # CII data not available for the given FY — skip indexation option
                indexed_cost = None
                indexed_improvement = _ZERO

            if indexed_cost is not None:
                gain_with_idx = net_sale - indexed_cost - (indexed_improvement or _ZERO)
                tax_with_idx = _q(max(gain_with_idx, _ZERO) * LTCG_OTHER_RATE_WITH_INDEXATION)
                option_a = {
                    "indexed_cost": indexed_cost,
                    "indexed_improvement_cost": indexed_improvement or _ZERO,
                    "capital_gain": max(gain_with_idx, _ZERO),
                    "tax_rate": LTCG_OTHER_RATE_WITH_INDEXATION,
                    "tax": tax_with_idx,
                    "cii_purchase": str(get_cii(purchase_fy)),
                    "cii_sale": str(get_cii(sale_fy)),
                }
            else:
                option_a = None

            # Option B: 12.5% without indexation
            gain_without_idx = base_gain
            tax_without_idx = _q(max(gain_without_idx, _ZERO) * LTCG_OTHER_RATE)
            option_b = {
                "cost": request.purchase_cost,
                "capital_gain": max(gain_without_idx, _ZERO),
                "tax_rate": LTCG_OTHER_RATE,
                "tax": tax_without_idx,
            }

            # Recommend the lower-tax option
            if option_a and option_a["tax"] < option_b["tax"]:
                recommended = "with_indexation"
                final_tax = option_a["tax"]
                final_gain = option_a["capital_gain"]
                final_indexed_cost = option_a["indexed_cost"]
                final_rate = LTCG_OTHER_RATE_WITH_INDEXATION
            else:
                recommended = "without_indexation"
                final_tax = option_b["tax"]
                final_gain = option_b["capital_gain"]
                final_indexed_cost = None
                final_rate = LTCG_OTHER_RATE

            return CapitalGainsResponse(
                asset_type=request.asset_type.value,
                holding_period_days=holding_days,
                holding_period_months=holding_months,
                is_long_term=True,
                classification="LTCG",
                purchase_cost=request.purchase_cost,
                indexed_cost=final_indexed_cost,
                sale_consideration=request.sale_consideration,
                expenses_on_transfer=request.expenses_on_transfer,
                capital_gain=final_gain,
                exemption_available=_ZERO,
                taxable_gain=final_gain,
                tax_rate=final_rate,
                tax_amount=final_tax,
                option_with_indexation=option_a,
                option_without_indexation=option_b,
                recommended_option=recommended,
                available_exemptions=exemptions_list,
                working={
                    "holding_days": holding_days,
                    "holding_months": holding_months,
                    "pre_july_2024": True,
                    "purchase_fy": purchase_fy,
                    "sale_fy": sale_fy,
                },
            )

        # Post-July-2024 purchase (or debt MF): flat 12.5%, no indexation
        taxable = max(base_gain, _ZERO)
        tax = _q(taxable * LTCG_OTHER_RATE)

        return CapitalGainsResponse(
            asset_type=request.asset_type.value,
            holding_period_days=holding_days,
            holding_period_months=holding_months,
            is_long_term=True,
            classification="LTCG",
            purchase_cost=request.purchase_cost,
            indexed_cost=None,
            sale_consideration=request.sale_consideration,
            expenses_on_transfer=request.expenses_on_transfer,
            capital_gain=base_gain,
            exemption_available=_ZERO,
            taxable_gain=taxable,
            tax_rate=LTCG_OTHER_RATE,
            tax_amount=tax,
            available_exemptions=exemptions_list,
            working={
                "holding_days": holding_days,
                "holding_months": holding_months,
                "post_july_2024": True,
                "base_gain": str(base_gain),
                "tax_rate": str(LTCG_OTHER_RATE),
            },
        )

    else:
        # STCG on non-equity: taxed at slab rates
        taxable = max(base_gain, _ZERO)
        return CapitalGainsResponse(
            asset_type=request.asset_type.value,
            holding_period_days=holding_days,
            holding_period_months=holding_months,
            is_long_term=False,
            classification="STCG",
            purchase_cost=request.purchase_cost,
            indexed_cost=None,
            sale_consideration=request.sale_consideration,
            expenses_on_transfer=request.expenses_on_transfer,
            capital_gain=base_gain,
            exemption_available=_ZERO,
            taxable_gain=taxable,
            tax_rate=None,  # slab rates
            tax_amount=_ZERO,  # cannot compute without full income context
            available_exemptions=[],
            working={
                "holding_days": holding_days,
                "holding_months": holding_months,
                "note": "STCG on non-equity assets is taxed at applicable slab rates. "
                        "Include this in total income for slab calculation.",
            },
        )


# --------------------------------------------------------------------------- #
#  Interest u/s 234A, 234B, 234C
# --------------------------------------------------------------------------- #

def compute_interest_234(request: InterestRequest) -> InterestResponse:
    """Compute interest u/s 234A, 234B, and 234C with month-wise breakdown.

    Also computes late filing fee u/s 234F where applicable.
    """
    total_tax = request.total_tax_liability
    total_prepaid = request.tds_paid + request.advance_tax_paid
    net_tax_due = max(total_tax - total_prepaid, _ZERO)

    # ---- 234A: Interest for late filing ----
    interest_234a = _ZERO
    working_234a: Dict[str, Any] = {"applicable": False}

    filing_due = request.due_date_of_filing
    filing_actual = request.actual_date_of_filing

    if filing_actual and filing_actual > filing_due and net_tax_due > _ZERO:
        # Months (or part thereof) of delay
        delay_months = (
            (filing_actual.year - filing_due.year) * 12
            + (filing_actual.month - filing_due.month)
        )
        # If any days remain beyond full months, count as additional month
        if filing_actual.day > filing_due.day:
            delay_months += 1
        delay_months = max(delay_months, 1)

        interest_234a = _q(net_tax_due * INTEREST_234A_RATE * delay_months)
        working_234a = {
            "applicable": True,
            "due_date": filing_due.isoformat(),
            "actual_date": filing_actual.isoformat(),
            "delay_months": delay_months,
            "net_tax_due": str(net_tax_due),
            "rate": str(INTEREST_234A_RATE),
            "interest": str(interest_234a),
            "formula": f"₹{net_tax_due:,.2f} × {INTEREST_234A_RATE * 100}% × {delay_months} months",
        }

    # ---- 234B: Interest for non-payment of advance tax ----
    interest_234b = _ZERO
    working_234b: Dict[str, Any] = {"applicable": False}

    # 234B applies if advance tax paid < 90% of assessed tax
    assessed_tax = total_tax  # simplified — actual assessed tax after assessment
    ninety_percent = _q(assessed_tax * Decimal("0.90"))

    if request.advance_tax_paid < ninety_percent and net_tax_due > _ZERO:
        # Interest from April 1 of AY to date of determination/payment
        # Simplified: compute from April 1 to filing date
        parts = request.assessment_year.split("-")
        ay_start_year = int(parts[0])
        april_1 = date(ay_start_year, 4, 1)

        end_date = filing_actual or filing_due
        months_234b = (
            (end_date.year - april_1.year) * 12
            + (end_date.month - april_1.month)
        )
        if end_date.day > 1:
            months_234b += 1
        months_234b = max(months_234b, 1)

        shortfall = max(assessed_tax - request.advance_tax_paid - request.tds_paid, _ZERO)
        interest_234b = _q(shortfall * INTEREST_234B_RATE * months_234b)

        working_234b = {
            "applicable": True,
            "assessed_tax": str(assessed_tax),
            "advance_tax_paid": str(request.advance_tax_paid),
            "tds_paid": str(request.tds_paid),
            "shortfall": str(shortfall),
            "from_date": april_1.isoformat(),
            "to_date": end_date.isoformat(),
            "months": months_234b,
            "rate": str(INTEREST_234B_RATE),
            "interest": str(interest_234b),
            "formula": f"₹{shortfall:,.2f} × {INTEREST_234B_RATE * 100}% × {months_234b} months",
        }

    # ---- 234C: Interest for deferment of advance tax ----
    interest_234c = _ZERO
    working_234c: Dict[str, Any] = {"applicable": False, "quarters": []}

    if total_tax > Decimal("10000"):  # advance tax not required if < ₹10,000
        # Expected cumulative payments at each installment
        advance_dates = request.advance_tax_dates or []
        cumulative_paid: Dict[str, Decimal] = {}
        running = _ZERO

        for ad in advance_dates:
            running += Decimal(str(ad.get("amount", 0)))
            cumulative_paid[ad.get("date", "")] = running

        quarter_details = []

        for i, schedule in enumerate(ADVANCE_TAX_SCHEDULE):
            expected_cumulative = _q(total_tax * schedule["cumulative_percent"])
            label = schedule["due_date_label"]

            # Find how much was actually paid by this date
            paid_by_date = _ZERO
            for ad in advance_dates:
                ad_date_str = ad.get("date", "")
                # Simple comparison — dates should be ISO format
                if ad_date_str and ad_date_str <= _schedule_date_str(request.assessment_year, label):
                    paid_by_date += Decimal(str(ad.get("amount", 0)))

            shortfall_c = max(expected_cumulative - paid_by_date, _ZERO)

            if shortfall_c > _ZERO:
                # Interest for 3 months (each quarter) or 1 month (last quarter)
                months_c = 1 if i == 3 else 3
                qi = _q(shortfall_c * INTEREST_234C_RATE * months_c)
                interest_234c += qi
                quarter_details.append({
                    "installment": label,
                    "expected_cumulative": str(expected_cumulative),
                    "paid_by_date": str(paid_by_date),
                    "shortfall": str(shortfall_c),
                    "months": months_c,
                    "interest": str(qi),
                })
            else:
                quarter_details.append({
                    "installment": label,
                    "expected_cumulative": str(expected_cumulative),
                    "paid_by_date": str(paid_by_date),
                    "shortfall": "0",
                    "months": 0,
                    "interest": "0",
                })

        if interest_234c > _ZERO:
            working_234c = {
                "applicable": True,
                "total_tax": str(total_tax),
                "quarters": quarter_details,
                "total_interest": str(interest_234c),
            }

    # ---- Late filing fee u/s 234F ----
    late_fee = _ZERO
    if filing_actual and filing_actual > filing_due:
        if total_tax - total_prepaid > Decimal("500000"):
            late_fee = LATE_FEE_234F_ABOVE_5L
        else:
            late_fee = LATE_FEE_234F_UPTO_5L

    total_interest = interest_234a + interest_234b + interest_234c

    return InterestResponse(
        interest_234a=interest_234a,
        interest_234b=interest_234b,
        interest_234c=interest_234c,
        total_interest=total_interest,
        late_fee_234f=late_fee,
        working_234a=working_234a,
        working_234b=working_234b,
        working_234c=working_234c,
    )


def _schedule_date_str(ay: str, label: str) -> str:
    """Convert '15 June' + AY '2026-27' → '2025-06-15' (FY date)."""
    parts = ay.split("-")
    ay_start = int(parts[0])
    fy_start = ay_start - 1  # AY 2026-27 → FY 2025-26

    month_map = {
        "15 June": f"{fy_start}-06-15",
        "15 September": f"{fy_start}-09-15",
        "15 December": f"{fy_start}-12-15",
        "15 March": f"{fy_start + 1}-03-15",
    }
    return month_map.get(label, f"{fy_start}-03-31")


# --------------------------------------------------------------------------- #
#  HRA Exemption
# --------------------------------------------------------------------------- #

def compute_hra_exemption(
    basic_salary: Decimal,
    da: Decimal,
    hra_received: Decimal,
    rent_paid: Decimal,
    is_metro: bool,
) -> Dict[str, Any]:
    """Compute HRA exemption u/s 10(13A).

    Exempt amount = minimum of:
      1. Actual HRA received
      2. 50% of (basic + DA) for metro cities / 40% for non-metro
      3. Rent paid minus 10% of (basic + DA)

    Args:
        basic_salary: Annual basic salary.
        da: Annual dearness allowance.
        hra_received: Annual HRA received from employer.
        rent_paid: Annual rent actually paid.
        is_metro: True if employee lives in Delhi, Mumbai, Kolkata, or Chennai.

    Returns:
        Dict with exempt_amount, taxable_hra, and step-by-step working.
    """
    salary = basic_salary + da

    # Three limits
    actual_hra = hra_received

    percent = HRA_METRO_PERCENT if is_metro else HRA_NON_METRO_PERCENT
    percent_of_salary = _q(salary * percent)

    rent_minus_10 = max(rent_paid - _q(salary * HRA_SALARY_PERCENT), _ZERO)

    exempt = min(actual_hra, percent_of_salary, rent_minus_10)
    taxable = hra_received - exempt

    return {
        "exempt_amount": exempt,
        "taxable_hra": taxable,
        "working": {
            "basic_salary": str(basic_salary),
            "da": str(da),
            "salary_for_hra": str(salary),
            "hra_received": str(hra_received),
            "rent_paid": str(rent_paid),
            "is_metro": is_metro,
            "limit_1_actual_hra": str(actual_hra),
            "limit_2_percent_of_salary": str(percent_of_salary),
            "limit_2_percent_used": f"{'50' if is_metro else '40'}%",
            "limit_3_rent_minus_10_pct": str(rent_minus_10),
            "exempt_amount": str(exempt),
            "taxable_hra": str(taxable),
            "formula": (
                f"Exempt = min(₹{actual_hra:,.2f}, "
                f"₹{percent_of_salary:,.2f}, "
                f"₹{rent_minus_10:,.2f}) = ₹{exempt:,.2f}"
            ),
        },
    }


# --------------------------------------------------------------------------- #
#  Depreciation (WDV method)
# --------------------------------------------------------------------------- #

def compute_depreciation(
    asset_cost: Decimal,
    asset_type: str,
    wdv_rate: Optional[Decimal] = None,
    years: int = 5,
    additional_dep_eligible: bool = False,
    purchased_in_second_half: bool = False,
) -> List[Dict[str, Any]]:
    """Compute year-by-year depreciation using Written Down Value (WDV) method.

    Args:
        asset_cost: Original cost of the asset.
        asset_type: Key from DEPRECIATION_RATES (e.g. 'plant_machinery_general').
        wdv_rate: Override rate. If None, looked up from DEPRECIATION_RATES.
        years: Number of years to project.
        additional_dep_eligible: If True, 20% additional depreciation in year 1
                                 (for new plant & machinery in manufacturing).
        purchased_in_second_half: If True, half-year rule applies in year 1
                                  (asset put to use < 180 days in first year).

    Returns:
        List of dicts, one per year, with: year, opening_wdv, depreciation_rate,
        depreciation_amount, additional_depreciation, total_depreciation,
        closing_wdv.
    """
    rate = wdv_rate or DEPRECIATION_RATES.get(asset_type)
    if rate is None:
        raise ValueError(
            f"Unknown asset_type '{asset_type}'. "
            f"Valid types: {list(DEPRECIATION_RATES.keys())}"
        )

    schedule: List[Dict[str, Any]] = []
    opening_wdv = asset_cost

    for yr in range(1, years + 1):
        # Half-year rule: in year of purchase, if used < 180 days, depreciation = 50%
        effective_rate = rate
        if yr == 1 and purchased_in_second_half:
            effective_rate = rate / 2

        dep = _q(opening_wdv * effective_rate)

        # Additional depreciation (year 1 only)
        add_dep = _ZERO
        if yr == 1 and additional_dep_eligible:
            add_dep_rate = ADDITIONAL_DEPRECIATION_RATE
            if purchased_in_second_half:
                add_dep_rate = add_dep_rate / 2  # 50% of additional dep
            add_dep = _q(opening_wdv * add_dep_rate)
        elif yr == 2 and additional_dep_eligible and purchased_in_second_half:
            # Remaining 50% of additional depreciation in year 2
            add_dep = _q(asset_cost * ADDITIONAL_DEPRECIATION_RATE / 2)

        total_dep = dep + add_dep
        closing_wdv = opening_wdv - total_dep

        schedule.append({
            "year": yr,
            "opening_wdv": str(opening_wdv),
            "depreciation_rate": str(effective_rate),
            "depreciation_amount": str(dep),
            "additional_depreciation": str(add_dep),
            "total_depreciation": str(total_dep),
            "closing_wdv": str(closing_wdv),
        })

        opening_wdv = closing_wdv

        if opening_wdv <= _ZERO:
            break

    return schedule
