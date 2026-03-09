"""Tax computation schemas — income tax, TDS, GST, interest, capital gains."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================
# Shared helpers
# ============================================================

def _non_negative_decimal(v: Optional[Decimal]) -> Optional[Decimal]:
    if v is not None and v < 0:
        raise ValueError("Value must be non-negative")
    return v


# ============================================================
# Income Tax
# ============================================================

class AgeCategory(str, Enum):
    below_60 = "below_60"
    between_60_and_80 = "60_to_80"
    above_80 = "above_80"


class Deductions(BaseModel):
    section_80c: Decimal = Field(Decimal("0"), ge=0, description="Max 1.5L under 80C")
    section_80d: Decimal = Field(Decimal("0"), ge=0, description="Medical insurance")
    section_80g: Decimal = Field(Decimal("0"), ge=0, description="Donations")
    section_80e: Decimal = Field(Decimal("0"), ge=0, description="Education loan interest")
    section_80ccd_1b: Decimal = Field(Decimal("0"), ge=0, description="NPS extra 50k")
    section_80tta: Decimal = Field(Decimal("0"), ge=0, description="Savings interest 10k")
    hra_exempt: Decimal = Field(Decimal("0"), ge=0)
    lta_exempt: Decimal = Field(Decimal("0"), ge=0)
    standard_deduction: Decimal = Field(Decimal("50000"), ge=0)
    nps_employer: Decimal = Field(Decimal("0"), ge=0)


class IncomeTaxRequest(BaseModel):
    assessment_year: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}$",
        description="e.g. 2025-26",
    )
    gross_salary: Decimal = Field(Decimal("0"), ge=0)
    income_hp: Decimal = Field(Decimal("0"), description="Income from house property")
    business_income: Decimal = Field(Decimal("0"), ge=0)
    capital_gains_lt: Decimal = Field(Decimal("0"), ge=0)
    capital_gains_st: Decimal = Field(Decimal("0"), ge=0)
    other_income: Decimal = Field(Decimal("0"), ge=0)
    deductions: Deductions = Field(default_factory=Deductions)
    age_category: AgeCategory = AgeCategory.below_60


class RegimeBreakdown(BaseModel):
    gross_total_income: Decimal
    total_deductions: Decimal
    taxable_income: Decimal
    tax_on_income: Decimal
    surcharge: Decimal = Decimal("0")
    education_cess: Decimal
    total_tax_liability: Decimal


class IncomeTaxResponse(BaseModel):
    old_regime: RegimeBreakdown
    new_regime: RegimeBreakdown
    recommended_regime: str = Field(
        ..., description="'old_regime' or 'new_regime'"
    )
    savings_amount: Decimal = Field(
        ..., description="Tax saved by choosing recommended regime"
    )


# ============================================================
# TDS
# ============================================================

class PaymentType(str, Enum):
    salary = "salary"
    professional_fees = "professional_fees"
    rent_land = "rent_land"
    rent_plant = "rent_plant"
    contract = "contract"
    commission = "commission"
    interest = "interest"
    dividend = "dividend"
    lottery = "lottery"
    transfer_of_property = "transfer_of_property"


class RecipientType(str, Enum):
    individual = "individual"
    huf = "huf"
    company = "company"
    firm = "firm"
    aop = "aop"
    trust = "trust"


class TDSRequest(BaseModel):
    payment_type: PaymentType
    amount: Decimal = Field(..., gt=0)
    pan_available: bool = True
    recipient_type: RecipientType = RecipientType.individual


class TDSResponse(BaseModel):
    section: str = Field(..., description="e.g. 194J, 194I(a)")
    rate: Decimal = Field(..., ge=0, le=100, description="TDS rate percentage")
    tds_amount: Decimal
    surcharge_applicable: bool = False
    threshold: Decimal = Field(
        ..., description="Threshold below which TDS is not deducted"
    )
    notes: str = ""


# ============================================================
# GST
# ============================================================

class SupplyType(str, Enum):
    goods = "goods"
    services = "services"


class GSTRequest(BaseModel):
    supply_type: SupplyType
    hsn_sac: Optional[str] = Field(None, max_length=10, description="HSN/SAC code")
    place_of_supply: str = Field(..., max_length=64, description="State or UT name")
    place_of_origin: str = Field(..., max_length=64, description="State or UT name")
    taxable_value: Decimal = Field(..., gt=0)
    gst_rate: Optional[Decimal] = Field(
        None, ge=0, le=28, description="Override GST rate %; auto-determined if null"
    )


class SupplyTypeDetermined(str, Enum):
    intra_state = "intra_state"
    inter_state = "inter_state"


class GSTResponse(BaseModel):
    cgst: Decimal = Field(..., ge=0)
    sgst: Decimal = Field(..., ge=0)
    igst: Decimal = Field(..., ge=0)
    total_tax: Decimal = Field(..., ge=0)
    total_with_tax: Decimal = Field(..., ge=0)
    supply_type_determined: SupplyTypeDetermined


# ============================================================
# Interest under sections 234A / 234B / 234C
# ============================================================

class InterestSection(str, Enum):
    s234a = "234a"
    s234b = "234b"
    s234c = "234c"


class MonthWiseDetail(BaseModel):
    month: str = Field(..., description="e.g. Apr-2025")
    days: int = Field(..., ge=0)
    interest: Decimal = Field(..., ge=0)


class InterestRequest(BaseModel):
    section: InterestSection
    tax_liability: Decimal = Field(..., ge=0)
    tax_paid: Decimal = Field(..., ge=0)
    due_date: date
    payment_date: date
    assessment_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")

    @field_validator("payment_date")
    @classmethod
    def payment_after_or_on_due(cls, v: date, info) -> date:
        due = info.data.get("due_date")
        if due and v < due:
            # Interest only applies when payment is after due date
            pass  # we still accept it — the engine may return 0 interest
        return v


class InterestResponse(BaseModel):
    interest_amount: Decimal = Field(..., ge=0)
    calculation_details: list[MonthWiseDetail] = Field(default_factory=list)
    section: InterestSection
    rate: Decimal = Field(
        ..., ge=0, le=100, description="Interest rate per month (%)"
    )


# ============================================================
# Capital Gains
# ============================================================

class AssetType(str, Enum):
    property = "property"
    equity_listed = "equity_listed"
    equity_unlisted = "equity_unlisted"
    debt_mf = "debt_mf"
    gold = "gold"
    other = "other"


class GainType(str, Enum):
    ltcg = "LTCG"
    stcg = "STCG"


class CapitalGainsRequest(BaseModel):
    asset_type: AssetType
    purchase_date: date
    sale_date: date
    purchase_price: Decimal = Field(..., gt=0)
    sale_price: Decimal = Field(..., gt=0)
    improvement_cost: Decimal = Field(Decimal("0"), ge=0)
    transfer_expenses: Decimal = Field(Decimal("0"), ge=0)

    @field_validator("sale_date")
    @classmethod
    def sale_after_purchase(cls, v: date, info) -> date:
        purchase = info.data.get("purchase_date")
        if purchase and v <= purchase:
            raise ValueError("sale_date must be after purchase_date")
        return v


class CapitalGainsResponse(BaseModel):
    gain_type: GainType
    indexed_cost: Optional[Decimal] = Field(
        None, description="Cost after CII indexation (LTCG on property/gold/unlisted)"
    )
    capital_gain: Decimal
    tax_rate: Decimal = Field(..., ge=0, le=100)
    tax_amount: Decimal = Field(..., ge=0)
    exemptions_available: list[str] = Field(
        default_factory=list,
        description="Applicable sections like 54, 54EC, 54F, 111A, 112A",
    )
    holding_period_days: int = Field(..., ge=1)
