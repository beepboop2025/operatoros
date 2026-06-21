"""
Pydantic schemas for Phase 7 NRI cross-border taxation modules.

These schemas define the API contract for:
  - Residential status determination
  - DTAA explorer
  - Section 195 / Form 15CA/15CB toolkit
  - Foreign Tax Credit (Rule 128 / Form 67)
  - Customs & tariffs
  - GST cross-border extensions
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# =========================================================================== #
#  Shared helpers
# =========================================================================== #

def _validate_ay_pair(v: str) -> str:
    """Ensure assessment year follows 'YYYY-YY' convention."""
    start_str, end_str = v.split("-")
    start = int(start_str)
    expected_end = (start + 1) % 100
    if int(end_str) != expected_end:
        raise ValueError(f"Invalid assessment year: expected '{start_str}-{expected_end:02d}'")
    return v


# =========================================================================== #
#  1. Residential Status
# =========================================================================== #

class ResidentialStatus(str, Enum):
    resident = "Resident"
    rnor = "RNOR"
    nri = "NRI"
    deemed_resident = "Deemed Resident"


class TaxScope(str, Enum):
    global_income = "global"
    india_sourced_plus_controlled = "india_sourced_plus_foreign_controlled"
    india_sourced = "india_sourced"


class ResidentialStatusRequest(BaseModel):
    assessment_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    days_in_india_current_fy: int = Field(..., ge=0, le=366)
    days_in_india_prior_4_fys: List[int] = Field(..., min_length=4, max_length=4)
    days_in_india_prior_7_fys: Optional[List[int]] = Field(None, min_length=7, max_length=7)
    prior_10_fys_resident: Optional[List[bool]] = Field(None, min_length=9, max_length=10)
    is_indian_citizen: bool = False
    is_person_of_indian_origin: bool = False
    leaving_for_employment: bool = False
    is_crew_of_indian_ship: bool = False
    indian_source_income: Decimal = Field(Decimal("0"), ge=0)
    tax_resident_elsewhere: bool = False

    @field_validator("assessment_year")
    @classmethod
    def validate_ay(cls, v: str) -> str:
        return _validate_ay_pair(v)


class ResidentialStatusResponse(BaseModel):
    status: ResidentialStatus
    taxable_scope: TaxScope
    controlling_rule: str
    rnor_test_result: Optional[str]
    is_deemed_resident: bool
    days_in_india_current_fy: int
    days_in_india_prior_4_fys: List[int]
    threshold_days: int
    working: Dict[str, Any] = Field(default_factory=dict)


# =========================================================================== #
#  2. DTAA Explorer
# =========================================================================== #

class DTAAIncomeType(str, Enum):
    dividends = "dividends"
    interest = "interest"
    royalty = "royalty"
    fees_for_technical_services = "fees_for_technical_services"
    capital_gains = "capital_gains"


class DTAARequest(BaseModel):
    country: str = Field(..., min_length=2, max_length=64)
    income_type: Optional[DTAAIncomeType] = None


class DTAARateEntry(BaseModel):
    income_type: str
    rate: Optional[Decimal]
    rate_percent: Optional[float]
    notes: str


class DTAAResponse(BaseModel):
    country: str
    country_code: str
    rates: List[DTAARateEntry]
    residency_tie_breaker: str
    trc_required: bool
    form_10f_required: bool
    documentation: List[str]
    source_citation: str
    ca_review_required: bool
    notes: str


# =========================================================================== #
#  3. Section 195 / Repatriation
# =========================================================================== #

class Section195PaymentType(str, Enum):
    interest = "interest"
    dividend = "dividend"
    royalty = "royalty"
    fees_for_technical_services = "fees_for_technical_services"
    rent = "rent"
    property_sale = "property_sale"
    other = "other"


class Section195Request(BaseModel):
    payment_type: Section195PaymentType
    payment_amount: Decimal = Field(..., gt=0)
    payee_is_nri: bool = True
    payee_country: str = ""
    payee_has_trc: bool = False
    payee_has_pan: bool = True
    property_sale_consideration: Optional[Decimal] = Field(None, ge=0)
    property_is_long_term: bool = False
    has_form_15e_certificate: bool = False
    certificate_rate: Optional[Decimal] = Field(None, ge=0, le=1)
    domestic_rate_override: Optional[Decimal] = Field(None, ge=0, le=1)
    treaty_rate_override: Optional[Decimal] = Field(None, ge=0, le=1)


class Section195Response(BaseModel):
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
    working: Dict[str, Any] = Field(default_factory=dict)


# =========================================================================== #
#  4. Foreign Tax Credit
# =========================================================================== #

class FTCCreditCountryInput(BaseModel):
    country: str
    foreign_income: Decimal = Field(..., ge=0)
    foreign_tax_paid: Decimal = Field(..., ge=0)
    has_dtaa: bool = False


class FTCCreditCountryResult(BaseModel):
    country: str
    foreign_income: Decimal
    foreign_tax_paid: Decimal
    indian_tax_on_foreign_income: Decimal
    allowable_credit: Decimal
    disallowance: Decimal
    method: str


class FTCRequest(BaseModel):
    assessment_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    total_income: Decimal = Field(..., ge=0)
    total_indian_tax: Decimal = Field(..., ge=0)
    countries: List[FTCCreditCountryInput] = Field(..., min_length=1)
    filing_date: Optional[date] = None

    @field_validator("assessment_year")
    @classmethod
    def validate_ay(cls, v: str) -> str:
        return _validate_ay_pair(v)


class FTCResponse(BaseModel):
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
    working: Dict[str, Any] = Field(default_factory=dict)


# =========================================================================== #
#  5. Customs & Tariffs
# =========================================================================== #

class CustomsTariffRequest(BaseModel):
    hsn_code: str = Field(..., min_length=2, max_length=20)
    cif_value: Decimal = Field(..., gt=0)
    country_of_origin: Optional[str] = None
    fta_code: Optional[str] = None
    bcd_rate_override: Optional[Decimal] = Field(None, ge=0, le=1)
    sws_rate_override: Optional[Decimal] = Field(None, ge=0, le=1)
    cess_rate_override: Optional[Decimal] = Field(None, ge=0, le=1)
    igst_rate_override: Optional[Decimal] = Field(None, ge=0, le=1)
    demo: bool = Field(False, description="Use illustrative sample rates when real ones are unsourced")


class CustomsTariffResponse(BaseModel):
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
    is_sample_data: bool = False
    working: Dict[str, Any] = Field(default_factory=dict)


# =========================================================================== #
#  6. GST Cross-Border
# =========================================================================== #

class CrossBorderTransactionType(str, Enum):
    import_ = "import"
    export = "export"
    oidar = "oidar"
    domestic = "domestic"


class CrossBorderGSTRequest(BaseModel):
    taxable_value: Decimal = Field(..., ge=0)
    transaction_type: CrossBorderTransactionType
    supply_type: str = Field("services", pattern=r"^(goods|services)$")
    hsn_sac: Optional[str] = None
    gst_rate: Optional[Decimal] = Field(None, ge=0, le=1)
    has_lut: bool = False
    is_b2b: bool = False
    recipient_country: str = ""
    place_of_supply: Optional[str] = None
    import_duty_amount: Decimal = Field(Decimal("0"), ge=0)


class CrossBorderGSTResponse(BaseModel):
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
    working: Dict[str, Any] = Field(default_factory=dict)
