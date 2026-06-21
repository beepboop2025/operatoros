"""
NRI cross-border taxation engines — Phase 7 backend logic.

All monetary calculations use ``Decimal`` to avoid floating-point errors.
Engines are pure (no DB, no I/O) and return request/response dataclasses.

Legal guardrail
---------------
Rates, thresholds, treaty values and customs numbers that have not been
sourced from an authoritative text are stored as ``None`` and surfaced with
a "CA review required" note.  See ``backend/DTAA_TODO.md`` and
``backend/TARIFF_TODO.md`` for the outstanding items.

Modules
-------
1. Residential status determiner (Section 6, IT Act — AY-keyed)
2. DTAA explorer (top NRI corridors, data-driven)
3. Section 195 / Form 15CA/15CB / Form 15E toolkit
4. Foreign Tax Credit (Rule 128 / Form 67)
5. Customs & tariffs import-duty calculator
6. GST cross-border extensions (import IGST, export LUT, OIDAR)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# --------------------------------------------------------------------------- #
#  SHARED HELPERS
# --------------------------------------------------------------------------- #

_ZERO = Decimal("0")
_ONE = Decimal("1")
_TWO_PLACES = Decimal("0.01")


def _d(value: str | int | float) -> Decimal:
    """Build a Decimal from a readable literal."""
    return Decimal(str(value))


def _q(val: Decimal) -> Decimal:
    """Quantize to 2 decimal places, rounding half-up."""
    return val.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def _parse_ay_start(assessment_year: str) -> int:
    """Return the calendar year in which the assessment year starts.

    Example: ``"2026-27"`` -> ``2026``.
    """
    return int(assessment_year.split("-")[0])


def _itr_due_date(assessment_year: str) -> date:
    """Default ITR due date for Form 67 alignment (31 July of AY start)."""
    return date(_parse_ay_start(assessment_year), 7, 31)


# =========================================================================== #
#  1. RESIDENTIAL STATUS DETERMINER
# =========================================================================== #

class ResidentialStatus(str, Enum):
    resident = "Resident"
    resident_not_ordinarily_resident = "RNOR"
    non_resident = "NRI"
    deemed_resident = "Deemed Resident"


class TaxScope(str, Enum):
    global_income = "global"
    india_sourced_plus_controlled = "india_sourced_plus_foreign_controlled"
    india_sourced = "india_sourced"


@dataclass
class ResidentialStatusRequest:
    """Input for determining residential status under Section 6."""

    assessment_year: str                       # e.g. "2025-26"
    days_in_india_current_fy: int              # days in the relevant FY
    days_in_india_prior_4_fys: List[int]       # most recent first, length 4
    # Data needed for RNOR tests (Section 6(6))
    days_in_india_prior_7_fys: Optional[List[int]] = None  # length 7
    prior_10_fys_resident: Optional[List[bool]] = None     # True = resident
    # Citizenship / purpose flags
    is_indian_citizen: bool = False
    is_person_of_indian_origin: bool = False
    leaving_for_employment: bool = False       # Indian citizen leaving for job
    is_crew_of_indian_ship: bool = False
    indian_source_income: Decimal = _ZERO      # income other than foreign sources
    tax_resident_elsewhere: bool = False       # for deemed-resident test


@dataclass
class ResidentialStatusResponse:
    status: ResidentialStatus
    taxable_scope: TaxScope
    controlling_rule: str
    rnor_test_result: Optional[str]
    is_deemed_resident: bool
    days_in_india_current_fy: int
    days_in_india_prior_4_fys: List[int]
    threshold_days: int
    working: Dict[str, Any] = field(default_factory=dict)


# AY-keyed residency configuration.  The transition point is AY 2026-27,
# which aligns with the 1 Apr 2026 rule change flagged in the spec.
_RESIDENCY_CONFIG: Dict[str, Dict[str, Any]] = {
    "default": {
        "high_income_visitor_threshold": 182,
        "high_income_threshold": _d("1_500_000"),
    },
    "2026-27": {
        "high_income_visitor_threshold": 120,
        "high_income_threshold": _d("1_500_000"),
    },
}


def _residency_config(assessment_year: str) -> Dict[str, Any]:
    """Return AY-specific residency thresholds."""
    # For AYs on or after the transition, use the post-Apr-2026 config.
    if assessment_year >= "2026-27":
        return _RESIDENCY_CONFIG["2026-27"]
    return _RESIDENCY_CONFIG["default"]


def _visitor_threshold(
    assessment_year: str,
    is_citizen: bool,
    is_pio: bool,
    leaving_for_employment: bool,
    is_crew: bool,
    indian_source_income: Decimal,
) -> int:
    """Return the days-in-India threshold for the second basic condition."""
    # Indian citizen leaving for employment or as a crew member of an Indian ship:
    # the 60-day limb is replaced by 182 days.
    if leaving_for_employment or is_crew:
        return 182

    # Indian citizen or PIO visiting India
    if is_citizen or is_pio:
        config = _residency_config(assessment_year)
        if indian_source_income > config["high_income_threshold"]:
            return config["high_income_visitor_threshold"]
        # Lower-income visitors remain subject to the 60-day limb.
        return 60

    # Default: 60 days for all other individuals.
    return 60


def determine_residential_status(request: ResidentialStatusRequest) -> ResidentialStatusResponse:
    """Determine residential status and the resulting taxable scope.

    Implements the basic conditions of Section 6(1), the deemed-resident
    provision of Section 6(1A), and the RNOR tests in Section 6(6).

    Note:
        RNOR determination requires prior-year data.  If the caller does not
        supply ``days_in_india_prior_7_fys`` or ``prior_10_fys_resident``,
        the engine marks the RNOR test as ``"insufficient_data"`` and treats
        the individual as ordinarily resident.
    """
    current_days = request.days_in_india_current_fy
    prior_4 = request.days_in_india_prior_4_fys
    prior_4_total = sum(prior_4) if prior_4 else 0

    threshold = _visitor_threshold(
        request.assessment_year,
        request.is_indian_citizen,
        request.is_person_of_indian_origin,
        request.leaving_for_employment,
        request.is_crew_of_indian_ship,
        request.indian_source_income,
    )

    # ---- Basic conditions (Section 6(1)) ----
    condition_182 = current_days >= 182
    condition_60_365 = current_days >= threshold and prior_4_total >= 365
    is_resident = condition_182 or condition_60_365

    # ---- Deemed resident (Section 6(1A)) ----
    config = _residency_config(request.assessment_year)
    deemed = False
    if (
        not is_resident
        and request.is_indian_citizen
        and request.indian_source_income > config["high_income_threshold"]
        and not request.tax_resident_elsewhere
    ):
        deemed = True

    # ---- RNOR tests (Section 6(6)) ----
    rnor_reason: Optional[str] = None
    if is_resident and not deemed:
        prior_10 = request.prior_10_fys_resident
        prior_7 = request.days_in_india_prior_7_fys

        test_9_10 = None
        if prior_10 is not None and len(prior_10) >= 9:
            non_resident_count = sum(1 for r in prior_10 if not r)
            test_9_10 = non_resident_count >= 9

        test_729 = None
        if prior_7 is not None and len(prior_7) >= 7:
            test_729 = sum(prior_7) <= 729

        if test_9_10 is True or test_729 is True:
            rnor_reason = (
                "non-resident in 9 out of 10 preceding FYs"
                if test_9_10
                else "<= 729 days in India in preceding 7 FYs"
            )
        elif test_9_10 is None and test_729 is None:
            rnor_reason = "insufficient_data"
        else:
            rnor_reason = "ordinarily resident"

    # ---- Final status and scope ----
    if deemed:
        status = ResidentialStatus.deemed_resident
        scope = TaxScope.global_income
        rule = "Section 6(1A) — deemed resident (citizen, India-source income > ₹15 lakh, not tax-resident elsewhere)"
    elif is_resident:
        if rnor_reason and rnor_reason not in ("ordinarily resident", "insufficient_data"):
            status = ResidentialStatus.resident_not_ordinarily_resident
            scope = TaxScope.india_sourced_plus_controlled
            rule = "Section 6(1) + Section 6(6) — Resident but Not Ordinarily Resident"
        else:
            status = ResidentialStatus.resident
            scope = TaxScope.global_income
            rule = "Section 6(1) — Resident and Ordinarily Resident"
    else:
        status = ResidentialStatus.non_resident
        scope = TaxScope.india_sourced
        rule = "Section 6(1) — Non-Resident"

    return ResidentialStatusResponse(
        status=status,
        taxable_scope=scope,
        controlling_rule=rule,
        rnor_test_result=rnor_reason,
        is_deemed_resident=deemed,
        days_in_india_current_fy=current_days,
        days_in_india_prior_4_fys=prior_4,
        threshold_days=threshold,
        working={
            "assessment_year": request.assessment_year,
            "days_current_fy": current_days,
            "prior_4_days": prior_4,
            "prior_4_total": prior_4_total,
            "condition_182_days": condition_182,
            "second_condition_threshold": threshold,
            "condition_days_plus_365": condition_60_365,
            "is_resident": is_resident,
            "high_income_threshold": str(config["high_income_threshold"]),
            "deemed_resident_test": deemed,
            "rnor_test_result": rnor_reason,
        },
    )


# =========================================================================== #
#  2. DTAA EXPLORER
# =========================================================================== #

class IncomeType(str, Enum):
    dividends = "dividends"
    interest = "interest"
    royalty = "royalty"
    ftc = "fees_for_technical_services"
    capital_gains = "capital_gains"


@dataclass(frozen=True)
class TreatyRateEntry:
    """A single article rate row for a treaty partner."""

    income_type: str
    rate: Optional[Decimal]          # None = not yet sourced / verify
    notes: str = ""


@dataclass(frozen=True)
class DTAATreaty:
    """Treaty snapshot for one country."""

    country: str
    country_code: str
    rates: Tuple[TreatyRateEntry, ...]
    residency_tie_breaker: str
    trc_required: bool
    form_10f_required: bool
    source_citation: str
    ca_review_required: bool


@dataclass
class DTAARequest:
    country: str                     # e.g. "USA" or "United States"
    income_type: Optional[str] = None


@dataclass
class DTAAResponse:
    country: str
    country_code: str
    rates: List[Dict[str, Any]]
    residency_tie_breaker: str
    trc_required: bool
    form_10f_required: bool
    documentation: List[str]
    source_citation: str
    ca_review_required: bool
    notes: str


# Data-driven treaty table.  Rates below are INDICATIVE headline treaty
# withholding rates sourced from the CBDT chart "Tax Rates: DTAA v. Income-tax
# Act" (incometax.gov.in) cross-checked with PwC India WHT summary. They remain
# flagged ``ca_review_required=True`` because the applicable rate depends on
# shareholding bands, the "make available" test, beneficial-ownership and MLI
# modifications that require professional verification. Stored as fractions
# (0.15 == 15%). See ``backend/DTAA_TODO.md``.
_DTAA_SOURCE = (
    "Indicative — CBDT 'Tax Rates: DTAA v. Income-tax Act' (incometax.gov.in) + "
    "PwC India WHT summary; verify against the signed treaty, protocol and MLI with a CA."
)
_DTAA_TREATIES: Dict[str, DTAATreaty] = {
    "USA": DTAATreaty(
        country="United States of America",
        country_code="US",
        rates=(
            TreatyRateEntry("dividends", _d("0.15"), "Art. 10 — 15% if recipient holds >=10% voting stock (12m); 25% for portfolio holdings"),
            TreatyRateEntry("interest", _d("0.15"), "Art. 11 — 15% general; 10% if paid to a bank/financial institution"),
            TreatyRateEntry("royalty", _d("0.15"), "Art. 12 — 15% general; 10% for industrial/commercial/scientific equipment"),
            TreatyRateEntry("fees_for_technical_services", _d("0.15"), "Art. 12 — 15%, subject to the 'make available' test"),
            TreatyRateEntry("capital_gains", None, "Art. 13 — India taxes per domestic law; share gains generally taxable in residence state with exceptions"),
        ),
        residency_tie_breaker=(
            "Permanent home -> Centre of vital interests -> Habitual abode -> "
            "Nationality -> Competent authority (Article 4)"
        ),
        trc_required=True,
        form_10f_required=True,
        source_citation=_DTAA_SOURCE + " India-US DTAA (1990, as amended).",
        ca_review_required=True,
    ),
    "UAE": DTAATreaty(
        country="United Arab Emirates",
        country_code="AE",
        rates=(
            TreatyRateEntry("dividends", _d("0.10"), "Art. 10 — 10%"),
            TreatyRateEntry("interest", _d("0.05"), "Art. 11 — 5% if paid to a bank/financial institution; 12.5% otherwise"),
            TreatyRateEntry("royalty", _d("0.10"), "Art. 12 — 10%"),
            TreatyRateEntry("fees_for_technical_services", None, "No separate FTS article; taxed as business profits / domestic 20% if an Indian PE exists"),
            TreatyRateEntry("capital_gains", None, "Indian-asset gains taxable in India per post-amendment position"),
        ),
        residency_tie_breaker="Permanent home -> Personal/economic relations -> Habitual abode -> Nationality",
        trc_required=True,
        form_10f_required=True,
        source_citation=_DTAA_SOURCE + " India-UAE DTAA (1992, as amended).",
        ca_review_required=True,
    ),
    "UK": DTAATreaty(
        country="United Kingdom",
        country_code="GB",
        rates=(
            TreatyRateEntry("dividends", _d("0.15"), "Art. 10 — up to 15% (10% band may apply)"),
            TreatyRateEntry("interest", _d("0.15"), "Art. 11 — 15% general; 10% on bank interest"),
            TreatyRateEntry("royalty", _d("0.15"), "Arts. 12/13 — 10%-15% by category"),
            TreatyRateEntry("fees_for_technical_services", _d("0.15"), "Art. 13 — 10%-15% by category"),
            TreatyRateEntry("capital_gains", None, "Art. 14 — Indian-source gains taxable in India"),
        ),
        residency_tie_breaker="Permanent home -> Centre of vital interests -> Habitual abode -> Nationality",
        trc_required=True,
        form_10f_required=True,
        source_citation=_DTAA_SOURCE + " India-UK DTAA (1993, as amended 2013).",
        ca_review_required=True,
    ),
    "CANADA": DTAATreaty(
        country="Canada",
        country_code="CA",
        rates=(
            TreatyRateEntry("dividends", _d("0.15"), "Art. 10 — 15% if holding >=10%; 25% otherwise"),
            TreatyRateEntry("interest", _d("0.15"), "Art. 11 — 15%"),
            TreatyRateEntry("royalty", _d("0.15"), "Art. 12 — 10%-20% by category (commonly 15%)"),
            TreatyRateEntry("fees_for_technical_services", _d("0.15"), "Art. 12 — 10%-15% by category"),
            TreatyRateEntry("capital_gains", None, "Art. 13 — Canada taxes worldwide gains, with credit for Indian tax"),
        ),
        residency_tie_breaker="Permanent home -> Personal/economic relations -> Habitual abode -> Nationality",
        trc_required=True,
        form_10f_required=True,
        source_citation=_DTAA_SOURCE + " India-Canada DTAA (1985, as amended).",
        ca_review_required=True,
    ),
    "AUSTRALIA": DTAATreaty(
        country="Australia",
        country_code="AU",
        rates=(
            TreatyRateEntry("dividends", _d("0.15"), "Art. 10 — 15%"),
            TreatyRateEntry("interest", _d("0.15"), "Art. 11 — 15%"),
            TreatyRateEntry("royalty", _d("0.15"), "Art. 12 — 10%-15% by category"),
            TreatyRateEntry("fees_for_technical_services", None, "No separate FTS provision; domestic 20% applies"),
            TreatyRateEntry("capital_gains", None, "Art. 13 — per domestic law"),
        ),
        residency_tie_breaker="Permanent home -> Centre of vital interests -> Habitual abode -> Nationality",
        trc_required=True,
        form_10f_required=True,
        source_citation=_DTAA_SOURCE + " India-Australia DTAA (1991, as amended; MLI-modified).",
        ca_review_required=True,
    ),
    "SINGAPORE": DTAATreaty(
        country="Singapore",
        country_code="SG",
        rates=(
            TreatyRateEntry("dividends", _d("0.15"), "Art. 10 — 10% if holding >=25%; 15% otherwise"),
            TreatyRateEntry("interest", _d("0.15"), "Art. 11 — 15% general; 10% if paid to a bank/financial institution"),
            TreatyRateEntry("royalty", _d("0.10"), "Art. 12 — 10%"),
            TreatyRateEntry("fees_for_technical_services", _d("0.10"), "Art. 12 — 10%"),
            TreatyRateEntry("capital_gains", None, "Art. 13 — India may tax Indian-share gains (2017 amendment; LOB applies)"),
        ),
        residency_tie_breaker="Permanent home -> Centre of vital interests -> Habitual abode -> Nationality",
        trc_required=True,
        form_10f_required=True,
        source_citation=_DTAA_SOURCE + " India-Singapore DTAA (1994, as amended; MLI-modified).",
        ca_review_required=True,
    ),
}


def explore_dtaa(request: DTAARequest) -> DTAAResponse:
    """Return treaty article rates and documentation requirements."""
    key = request.country.strip().upper()
    treaty = _DTAA_TREATIES.get(key)

    if treaty is None:
        return DTAAResponse(
            country=request.country,
            country_code="",
            rates=[],
            residency_tie_breaker="",
            trc_required=True,
            form_10f_required=True,
            documentation=["Tax Residency Certificate (TRC)", "Form 10F"],
            source_citation="Not in current treaty table — see DTAA_TODO.md",
            ca_review_required=True,
            notes=(
                f"'{request.country}' is not yet in the top-corridor treaty table. "
                "Add it to backend/DTAA_TODO.md for CA sourcing."
            ),
        )

    rates_out: List[Dict[str, Any]] = []
    for entry in treaty.rates:
        if request.income_type is None or entry.income_type == request.income_type:
            rates_out.append({
                "income_type": entry.income_type,
                "rate": str(entry.rate) if entry.rate is not None else None,
                "rate_percent": (
                    float(entry.rate * _d(100)) if entry.rate is not None else None
                ),
                "notes": entry.notes,
            })

    documentation = ["Tax Residency Certificate (TRC)"]
    if treaty.form_10f_required:
        documentation.append("Form 10F")

    notes = (
        "Treaty rates require CA verification before use. "
        if treaty.ca_review_required
        else ""
    )
    notes += "The beneficial treaty rate is applied only when it is lower than the domestic rate and valid TRC/Form 10F documentation is on file."

    return DTAAResponse(
        country=treaty.country,
        country_code=treaty.country_code,
        rates=rates_out,
        residency_tie_breaker=treaty.residency_tie_breaker,
        trc_required=treaty.trc_required,
        form_10f_required=treaty.form_10f_required,
        documentation=documentation,
        source_citation=treaty.source_citation,
        ca_review_required=treaty.ca_review_required,
        notes=notes,
    )


# =========================================================================== #
#  3. SECTION 195 / REPATRIATION TOOLKIT
# =========================================================================== #

class Section195PaymentType(str, Enum):
    interest = "interest"
    dividend = "dividend"
    royalty = "royalty"
    fees_for_technical_services = "fees_for_technical_services"
    rent = "rent"
    property_sale = "property_sale"
    other = "other"


@dataclass
class Section195Request:
    payment_type: Section195PaymentType
    payment_amount: Decimal
    payee_is_nri: bool = True
    payee_country: str = ""
    payee_has_trc: bool = False
    payee_has_pan: bool = True
    property_sale_consideration: Optional[Decimal] = None
    property_is_long_term: bool = False
    has_form_15e_certificate: bool = False
    certificate_rate: Optional[Decimal] = None
    # Optional explicit rates (sourced by caller/CA)
    domestic_rate_override: Optional[Decimal] = None
    treaty_rate_override: Optional[Decimal] = None


@dataclass
class Section195Response:
    section: str
    payment_type: str
    applicable_rate: Optional[Decimal]
    tds_amount: Optional[Decimal]
    applicable_regime: str
    form_15ca_required: bool
    form_15cb_required: bool
    form_15e_applied: bool
    certificate_rate: Optional[Decimal]
    repatriation_note: str
    notes: str
    working: Dict[str, Any] = field(default_factory=dict)


# Placeholder domestic rates under Section 195 / First Schedule.
# These are intentionally left ``None`` until they are traced to the
# Finance Act 2025 / 2026 First Schedule and verified.  Callers may supply
# ``domestic_rate_override`` and ``treaty_rate_override`` for pure computation.
_S195_DOMESTIC_RATES: Dict[str, Optional[Decimal]] = {
    "interest": None,
    "dividend": None,
    "royalty": None,
    "fees_for_technical_services": None,
    "rent": None,
    "property_sale": None,
    "other": None,
}

# Threshold for Form 15CB (Certificate from accountant)
_FORM_15CB_THRESHOLD = _d("500_000")


def compute_section_195(request: Section195Request) -> Section195Response:
    """Compute TDS under Section 195 and the associated compliance workflow."""
    if not request.payee_is_nri:
        return Section195Response(
            section="N/A",
            payment_type=request.payment_type.value,
            applicable_rate=None,
            tds_amount=None,
            applicable_regime="not_applicable",
            form_15ca_required=False,
            form_15cb_required=False,
            form_15e_applied=False,
            certificate_rate=None,
            repatriation_note="Section 195 applies only to payments to non-residents.",
            notes="Payee is not an NRI — use the domestic TDS sections instead.",
            working={"payee_is_nri": False},
        )

    base_amount = request.payment_amount
    payment_key = request.payment_type.value
    section = "195"

    # Property sale uses Section 195 (NRI seller) and may use 194IA for residents.
    if request.payment_type == Section195PaymentType.property_sale:
        section = "195"
        base_amount = request.property_sale_consideration or request.payment_amount

    # Form 15E / lower/nil deduction certificate takes precedence.
    if request.has_form_15e_certificate and request.certificate_rate is not None:
        rate = request.certificate_rate
        regime = "Form 15E / Section 197 certificate"
        form_15e_applied = True
    else:
        form_15e_applied = False
        domestic_rate = request.domestic_rate_override or _S195_DOMESTIC_RATES.get(payment_key)
        treaty_rate = request.treaty_rate_override

        if domestic_rate is None and treaty_rate is None:
            return Section195Response(
                section=section,
                payment_type=payment_key,
                applicable_rate=None,
                tds_amount=None,
                applicable_regime="pending_sourcing",
                form_15ca_required=True,
                form_15cb_required=base_amount >= _FORM_15CB_THRESHOLD,
                form_15e_applied=False,
                certificate_rate=request.certificate_rate,
                repatriation_note=(
                    "Remittance to an NRI is generally permitted under the USD 1 million "
                    "scheme subject to Form 15CA/15CB and FEMA documentation."
                ),
                notes=(
                    "Domestic Section 195 rate is not yet sourced. "
                    "Provide domestic_rate_override / treaty_rate_override or see TARIFF_TODO.md."
                ),
                working={
                    "base_amount": str(base_amount),
                    "payment_type": payment_key,
                },
            )

        # DTAA beneficial rate applies only if TRC is available.
        if treaty_rate is not None and request.payee_has_trc:
            if domestic_rate is not None:
                rate = min(domestic_rate, treaty_rate)
                regime = "DTAA (lower of domestic / treaty)"
            else:
                rate = treaty_rate
                regime = "DTAA"
        elif domestic_rate is not None:
            rate = domestic_rate
            regime = "Finance Act"
        else:
            rate = treaty_rate  # type: ignore[assignment]
            regime = "DTAA"

    tds_amount = _q(base_amount * rate) if rate is not None else None

    form_15ca_required = True
    form_15cb_required = base_amount >= _FORM_15CB_THRESHOLD

    repatriation_note = (
        "NRI repatriation is generally permitted up to USD 1 million per financial year "
        "under the RBI Liberalised Remittance Scheme route, subject to Form 15CA/15CB "
        "and FEMA compliance."
    )

    notes = (
        f"TDS under Section {section} at {rate * _d(100)}% on ₹{base_amount:,.2f}. "
        "Surcharge, cess and any DTAA benefit must be verified by a CA before deduction."
    )

    return Section195Response(
        section=section,
        payment_type=payment_key,
        applicable_rate=rate,
        tds_amount=tds_amount,
        applicable_regime=regime,
        form_15ca_required=form_15ca_required,
        form_15cb_required=form_15cb_required,
        form_15e_applied=form_15e_applied,
        certificate_rate=request.certificate_rate,
        repatriation_note=repatriation_note,
        notes=notes,
        working={
            "base_amount": str(base_amount),
            "payment_type": payment_key,
            "has_trc": request.payee_has_trc,
            "has_pan": request.payee_has_pan,
            "form_15e_applied": form_15e_applied,
            "applicable_rate": str(rate) if rate is not None else None,
            "tds_amount": str(tds_amount) if tds_amount is not None else None,
        },
    )


# =========================================================================== #
#  4. FOREIGN TAX CREDIT (Rule 128 / Form 67)
# =========================================================================== #

@dataclass
class FTCCreditCountryInput:
    country: str
    foreign_income: Decimal
    foreign_tax_paid: Decimal
    has_dtaa: bool = False


@dataclass
class FTCCreditCountryResult:
    country: str
    foreign_income: Decimal
    foreign_tax_paid: Decimal
    indian_tax_on_foreign_income: Decimal
    allowable_credit: Decimal
    disallowance: Decimal
    method: str


@dataclass
class FTCRequest:
    assessment_year: str
    total_income: Decimal
    total_indian_tax: Decimal              # after cess/surcharge
    countries: List[FTCCreditCountryInput]
    filing_date: Optional[date] = None


@dataclass
class FTCResponse:
    assessment_year: str
    total_foreign_income: Decimal
    total_foreign_tax_paid: Decimal
    total_allowable_credit: Decimal
    total_disallowance: Decimal
    average_indian_tax_rate: Decimal
    form_67_due_date: date
    is_filed_on_time: bool
    per_country: List[FTCCreditCountryResult]
    notes: str
    working: Dict[str, Any] = field(default_factory=dict)


def compute_ftc(request: FTCRequest) -> FTCResponse:
    """Compute allowable Foreign Tax Credit under Rule 128 / Section 91.

    Uses the average-rate method: Indian tax attributable to foreign income is
    ``foreign_income * (total_indian_tax / total_income)``.  The credit is the
    lower of that amount and the foreign tax paid.
    """
    total_income = request.total_income
    total_tax = request.total_indian_tax

    if total_income > _ZERO:
        average_rate = _q(total_tax / total_income)
    else:
        average_rate = _ZERO

    per_country: List[FTCCreditCountryResult] = []
    total_foreign_income = _ZERO
    total_foreign_tax = _ZERO
    total_allowable = _ZERO

    for item in request.countries:
        indian_tax_on_income = _q(item.foreign_income * average_rate)
        allowable = min(item.foreign_tax_paid, indian_tax_on_income)
        disallowance = item.foreign_tax_paid - allowable

        per_country.append(
            FTCCreditCountryResult(
                country=item.country,
                foreign_income=item.foreign_income,
                foreign_tax_paid=item.foreign_tax_paid,
                indian_tax_on_foreign_income=indian_tax_on_income,
                allowable_credit=allowable,
                disallowance=disallowance,
                method="DTAA" if item.has_dtaa else "Section 91",
            )
        )
        total_foreign_income += item.foreign_income
        total_foreign_tax += item.foreign_tax_paid
        total_allowable += allowable

    due_date = _itr_due_date(request.assessment_year)
    filed_on_time = (
        request.filing_date is None or request.filing_date <= due_date
    )

    notes = (
        "Credit is limited to the lower of foreign tax paid and Indian tax "
        "attributable to the foreign income. Form 67 must be filed on or before "
        "the ITR due date to claim DTAA relief."
    )

    return FTCResponse(
        assessment_year=request.assessment_year,
        total_foreign_income=total_foreign_income,
        total_foreign_tax_paid=total_foreign_tax,
        total_allowable_credit=total_allowable,
        total_disallowance=total_foreign_tax - total_allowable,
        average_indian_tax_rate=average_rate,
        form_67_due_date=due_date,
        is_filed_on_time=filed_on_time,
        per_country=per_country,
        notes=notes,
        working={
            "total_income": str(total_income),
            "total_indian_tax": str(total_tax),
            "average_indian_tax_rate": str(average_rate),
            "form_67_due_date": due_date.isoformat(),
        },
    )


# =========================================================================== #
#  5. CUSTOMS & TARIFFS
# =========================================================================== #

@dataclass
class CustomsTariffRequest:
    hsn_code: str
    cif_value: Decimal                     # assessable value in INR
    country_of_origin: Optional[str] = None
    fta_code: Optional[str] = None
    # Optional explicit rate overrides (sourced by CA/CHA)
    bcd_rate_override: Optional[Decimal] = None
    sws_rate_override: Optional[Decimal] = None
    cess_rate_override: Optional[Decimal] = None
    igst_rate_override: Optional[Decimal] = None
    demo: bool = False                     # use illustrative sample rates if real ones are unsourced


@dataclass
class CustomsTariffResponse:
    hsn_code: str
    cif_value: Decimal
    bcd_rate: Optional[Decimal]
    bcd_amount: Optional[Decimal]
    sws_rate: Optional[Decimal]
    sws_amount: Optional[Decimal]
    cess_rate: Optional[Decimal]
    cess_amount: Optional[Decimal]
    igst_rate: Optional[Decimal]
    igst_amount: Optional[Decimal]
    import_duty_total: Optional[Decimal]
    total_landed_cost: Optional[Decimal]
    fta_applied: bool
    missing_rates: List[str]
    notes: str
    is_sample_data: bool = False           # True when illustrative demo rates were used
    working: Dict[str, Any] = field(default_factory=dict)


# Default SWS is 10% of BCD where applicable.
_DEFAULT_SWS_RATE = _d("0.10")

# Tariff table — deliberately empty until sourced from the Customs Tariff Act /
# Central Excise Tariff.  See ``backend/TARIFF_TODO.md``.
_CUSTOMS_TARIFF_RATES: Dict[str, Dict[str, Optional[Decimal]]] = {}

# ILLUSTRATIVE sample rates used ONLY in demo mode. These are NOT authoritative
# and are flagged ``is_sample_data=True`` in the response. Real rates must be
# sourced from the Customs Tariff (see TARIFF_TODO.md).
_CUSTOMS_TARIFF_RATES_SAMPLE: Dict[str, Dict[str, Optional[Decimal]]] = {
    "8517": {"bcd": _d("0.20"), "sws": _d("0.10"), "cess": None, "igst": _d("0.18")},  # phones / telecom
    "8471": {"bcd": _d("0.00"), "sws": _d("0.10"), "cess": None, "igst": _d("0.18")},  # computers
    "8528": {"bcd": _d("0.20"), "sws": _d("0.10"), "cess": None, "igst": _d("0.18")},  # monitors / displays
    "8703": {"bcd": _d("0.70"), "sws": _d("0.10"), "cess": None, "igst": _d("0.28")},  # motor cars
    "61":   {"bcd": _d("0.10"), "sws": _d("0.10"), "cess": None, "igst": _d("0.12")},  # apparel (knitted)
    "62":   {"bcd": _d("0.10"), "sws": _d("0.10"), "cess": None, "igst": _d("0.12")},  # apparel (woven)
    "30":   {"bcd": _d("0.10"), "sws": _d("0.10"), "cess": None, "igst": _d("0.12")},  # pharmaceuticals
}

# Recognised FTA codes for preferential-rate flags.
_RECOGNISED_FTAS = frozenset({
    "ASEAN",
    "SAFTA",
    "INDIA_UAE_CEPA",
    "INDIA_UK_EPA",
    "INDIA_AU_ECTA",
    "INDIA_CANADA_EPTA",
    "SINGAPORE_CECA",
})


def _lookup_customs_rates(
    hsn_code: str, table: Optional[Dict[str, Dict[str, Optional[Decimal]]]] = None
) -> Dict[str, Optional[Decimal]]:
    """Look up rates by exact HSN or by chapter prefix in the given table."""
    table = _CUSTOMS_TARIFF_RATES if table is None else table
    if hsn_code in table:
        return table[hsn_code]

    # Try progressively shorter prefixes (first 6, 4, 2 digits)
    for length in (6, 4, 2):
        prefix = hsn_code[:length]
        if prefix in table:
            return table[prefix]

    return {}


def compute_customs_tariff(request: CustomsTariffRequest) -> CustomsTariffResponse:
    """Compute BCD + SWS + cess + IGST on an import.

    The IGST base is assessable value plus BCD, SWS and any cess.  Rates must
    be sourced from the Customs Tariff; missing rates are surfaced in
    ``missing_rates`` rather than guessed.
    """
    hsn = request.hsn_code.strip()
    cif = request.cif_value

    lookup = _lookup_customs_rates(hsn)
    is_sample_data = False
    if not lookup and request.demo:
        lookup = _lookup_customs_rates(hsn, table=_CUSTOMS_TARIFF_RATES_SAMPLE)
        is_sample_data = bool(lookup)
    bcd_rate = request.bcd_rate_override or lookup.get("bcd")
    sws_rate = request.sws_rate_override or lookup.get("sws") or _DEFAULT_SWS_RATE
    cess_rate = request.cess_rate_override or lookup.get("cess")
    igst_rate = request.igst_rate_override or lookup.get("igst")

    missing: List[str] = []
    if bcd_rate is None:
        missing.append("bcd")
    if igst_rate is None:
        missing.append("igst")
    # SWS is defaulted to 10% of BCD; cess is optional.

    fta_applied = bool(
        request.fta_code and request.fta_code.upper() in _RECOGNISED_FTAS
    )

    if not missing:
        bcd_amount = _q(cif * bcd_rate)  # type: ignore[arg-type]
        sws_amount = _q(bcd_amount * sws_rate) if sws_rate else _ZERO
        cess_amount = _q((cif + bcd_amount + sws_amount) * cess_rate) if cess_rate else _ZERO
        igst_base = cif + bcd_amount + sws_amount + cess_amount
        igst_amount = _q(igst_base * igst_rate)  # type: ignore[arg-type]
        import_duty_total = _q(bcd_amount + sws_amount + cess_amount + igst_amount)
        landed_cost = _q(cif + import_duty_total)
        notes = (
            "Computation completed with provided/sourced rates. "
            "Verify FTA preferential claim and any exemption notifications."
        )
    else:
        bcd_amount = None
        sws_amount = None
        cess_amount = None
        igst_amount = None
        import_duty_total = None
        landed_cost = None
        notes = (
            f"Cannot compute landed cost because the following rates are not "
            f"sourced for HSN {hsn}: {', '.join(missing)}. "
            "See TARIFF_TODO.md."
        )

    if is_sample_data:
        notes = "SAMPLE DATA — illustrative rates for demo only, NOT authoritative. " + notes

    return CustomsTariffResponse(
        hsn_code=hsn,
        cif_value=cif,
        bcd_rate=bcd_rate,
        bcd_amount=bcd_amount,
        sws_rate=sws_rate,
        sws_amount=sws_amount,
        cess_rate=cess_rate,
        cess_amount=cess_amount,
        igst_rate=igst_rate,
        igst_amount=igst_amount,
        import_duty_total=import_duty_total,
        total_landed_cost=landed_cost,
        fta_applied=fta_applied,
        missing_rates=missing,
        notes=notes,
        is_sample_data=is_sample_data,
        working={
            "cif_value": str(cif),
            "country_of_origin": request.country_of_origin,
            "fta_code": request.fta_code,
            "fta_applied": fta_applied,
            "missing_rates": missing,
        },
    )


# =========================================================================== #
#  6. GST CROSS-BORDER EXTENSIONS
# =========================================================================== #

from app.services.tax_engine import compute_gst as _compute_gst
from app.services.tax_engine import GSTRequest as _GSTRequest


class CrossBorderTransactionType(str, Enum):
    import_ = "import"
    export = "export"
    oidar = "oidar"
    domestic = "domestic"


@dataclass
class CrossBorderGSTRequest:
    taxable_value: Decimal
    transaction_type: CrossBorderTransactionType
    supply_type: str = "services"            # "goods" or "services"
    hsn_sac: Optional[str] = None
    gst_rate: Optional[Decimal] = None       # total GST rate as a fraction
    has_lut: bool = False                    # export with LUT/Bond
    is_b2b: bool = False
    recipient_country: str = ""
    place_of_supply: Optional[str] = None
    import_duty_amount: Decimal = _ZERO      # duty to include in IGST base for imports


@dataclass
class CrossBorderGSTResponse:
    transaction_type: str
    supply_type: str
    taxable_value: Decimal
    igst: Decimal
    cgst: Decimal
    sgst: Decimal
    total_gst: Decimal
    invoice_total: Decimal
    export_zero_rated: bool
    reverse_charge: bool
    place_of_supply: str
    notes: str
    working: Dict[str, Any] = field(default_factory=dict)


def compute_cross_border_gst(request: CrossBorderGSTRequest) -> CrossBorderGSTResponse:
    """Compute GST for cross-border supplies.

    Handles:
      - Export with LUT -> zero-rated (IGST = 0)
      - Export without LUT -> IGST charged, eligible for refund
      - Import -> IGST on (value + import duty)
      - OIDAR -> reverse charge for B2B; supplier charge for B2C
      - Domestic -> delegates to the existing intra/inter-state engine
    """
    tx = request.transaction_type
    value = request.taxable_value
    rate = request.gst_rate or _d("0.18")

    if tx == CrossBorderTransactionType.export:
        if request.has_lut:
            return CrossBorderGSTResponse(
                transaction_type=tx.value,
                supply_type=request.supply_type,
                taxable_value=value,
                igst=_ZERO,
                cgst=_ZERO,
                sgst=_ZERO,
                total_gst=_ZERO,
                invoice_total=value,
                export_zero_rated=True,
                reverse_charge=False,
                place_of_supply=request.recipient_country or "outside India",
                notes="Export is zero-rated under LUT/Bond; no IGST payable.",
                working={"has_lut": True, "gst_rate": str(rate)},
            )
        igst = _q(value * rate)
        return CrossBorderGSTResponse(
            transaction_type=tx.value,
            supply_type=request.supply_type,
            taxable_value=value,
            igst=igst,
            cgst=_ZERO,
            sgst=_ZERO,
            total_gst=igst,
            invoice_total=value + igst,
            export_zero_rated=False,
            reverse_charge=False,
            place_of_supply=request.recipient_country or "outside India",
            notes="IGST is payable on export without LUT; refund can be claimed.",
            working={"has_lut": False, "gst_rate": str(rate)},
        )

    if tx == CrossBorderTransactionType.import_:
        igst_base = value + request.import_duty_amount
        igst = _q(igst_base * rate)
        return CrossBorderGSTResponse(
            transaction_type=tx.value,
            supply_type=request.supply_type,
            taxable_value=value,
            igst=igst,
            cgst=_ZERO,
            sgst=_ZERO,
            total_gst=igst,
            invoice_total=igst_base + igst,
            export_zero_rated=False,
            reverse_charge=False,  # importer pays IGST directly
            place_of_supply=request.place_of_supply or "India",
            notes="IGST on imports is payable on assessable value plus BCD/SWS/cess.",
            working={
                "import_duty_amount": str(request.import_duty_amount),
                "igst_base": str(igst_base),
                "gst_rate": str(rate),
            },
        )

    if tx == CrossBorderTransactionType.oidar:
        # Place of supply for OIDAR services: location of the service recipient.
        igst = _q(value * rate)
        if request.is_b2b:
            return CrossBorderGSTResponse(
                transaction_type=tx.value,
                supply_type=request.supply_type,
                taxable_value=value,
                igst=igst,
                cgst=_ZERO,
                sgst=_ZERO,
                total_gst=igst,
                invoice_total=value,
                export_zero_rated=False,
                reverse_charge=True,
                place_of_supply=request.recipient_country or "location of recipient",
                notes="OIDAR B2B: IGST payable by the registered recipient under reverse charge.",
                working={"is_b2b": True, "gst_rate": str(rate)},
            )
        return CrossBorderGSTResponse(
            transaction_type=tx.value,
            supply_type=request.supply_type,
            taxable_value=value,
            igst=igst,
            cgst=_ZERO,
            sgst=_ZERO,
            total_gst=igst,
            invoice_total=value + igst,
            export_zero_rated=False,
            reverse_charge=False,
            place_of_supply=request.recipient_country or "location of supplier",
            notes="OIDAR B2C: IGST payable by the overseas supplier.",
            working={"is_b2b": False, "gst_rate": str(rate)},
        )

    # Domestic cross-border service (e.g., client in another Indian state)
    origin = "place_of_origin"
    supply = request.place_of_supply or request.recipient_country or ""
    engine_result = _compute_gst(
        _GSTRequest(
            taxable_value=value,
            hsn_sac=request.hsn_sac,
            gst_rate=rate,
            place_of_supply_state=supply,
            place_of_origin_state=origin,
        )
    )
    return CrossBorderGSTResponse(
        transaction_type=tx.value,
        supply_type=request.supply_type,
        taxable_value=value,
        igst=engine_result.igst,
        cgst=engine_result.cgst,
        sgst=engine_result.sgst,
        total_gst=engine_result.total_gst,
        invoice_total=engine_result.invoice_total,
        export_zero_rated=False,
        reverse_charge=False,
        place_of_supply=supply,
        notes="Domestic supply: CGST/SGST or IGST based on place of supply.",
        working=engine_result.working,
    )
