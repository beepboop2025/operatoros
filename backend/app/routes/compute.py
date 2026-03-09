"""Tax computation routes — income tax, TDS, GST, capital gains, interest, HRA, depreciation."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.middleware.audit import get_client_ip, log_action
from app.models.client import Client
from app.models.computation import TaxComputation, TaxRegime
from app.models.user import User
from app.schemas.computation import (
    CapitalGainsRequest,
    CapitalGainsResponse,
    GainType,
    GSTRequest,
    GSTResponse,
    IncomeTaxRequest,
    IncomeTaxResponse,
    InterestRequest,
    InterestResponse,
    InterestSection,
    MonthWiseDetail,
    RegimeBreakdown,
    SupplyTypeDetermined,
    TDSRequest,
    TDSResponse,
)
from app.services import tax_engine as engine_mod
from app.services.tax_engine import (
    compute_capital_gains,
    compute_depreciation,
    compute_gst,
    compute_hra_exemption,
    compute_income_tax,
    compute_interest_234,
    compute_tds,
)

router = APIRouter(tags=["compute"])

_ZERO = Decimal("0")


# --------------------------------------------------------------------------- #
#  Adapters: Pydantic schema <-> Engine dataclass
# --------------------------------------------------------------------------- #
# The tax_engine defines its own dataclasses with different field names than
# the Pydantic API schemas.  These adapter functions bridge the two worlds
# so neither layer needs to know about the other's naming conventions.


# -- Payment type -> TDS section mapping ------------------------------------

_PAYMENT_TYPE_TO_SECTION = {
    "salary": "192",
    "professional_fees": "194J(b)",
    "rent_land": "194I(b)",
    "rent_plant": "194I(a)",
    "contract": "194C",
    "commission": "194H",
    "interest": "194A",
    "dividend": "194K",
    "lottery": "194B",
    "transfer_of_property": "194IA",
}

# -- Asset type mapping (Pydantic enum value -> Engine enum value) ----------

_ASSET_TYPE_MAP = {
    "property": "immovable_property",
    "equity_listed": "listed_equity",
    "equity_unlisted": "unlisted_shares",
    "debt_mf": "debt_mutual_fund",
    "gold": "gold",
    "other": "other",
}


def _adapt_income_tax_request(schema: IncomeTaxRequest) -> engine_mod.IncomeTaxRequest:
    """Convert Pydantic IncomeTaxRequest to engine dataclass."""
    d = schema.deductions

    # Map Pydantic deduction fields -> engine Deductions fields.
    # Pydantic has a simpler set; engine has fine-grained fields.
    engine_deductions = engine_mod.Deductions(
        sec_80c=d.section_80c,
        sec_80ccd_1b=d.section_80ccd_1b,
        sec_80ccd_2=d.nps_employer,
        sec_80d_self=d.section_80d,       # Pydantic lumps 80D into one field
        sec_80e=d.section_80e,
        sec_80g=d.section_80g,
        sec_80tta=d.section_80tta,
        sec_24b=_ZERO,                    # not exposed in Pydantic schema
    )

    # Map Pydantic age_category enum to engine enum.
    # Both use the same underlying string values ("below_60", "60_to_80").
    # Pydantic: above_80 = "above_80", Engine: super_senior_80_plus = "80_plus"
    age_str = schema.age_category.value
    if age_str == "above_80":
        age_str = "80_plus"
    engine_age = engine_mod.AgeCategory(age_str)

    return engine_mod.IncomeTaxRequest(
        assessment_year=schema.assessment_year,
        age_category=engine_age,
        gross_salary=schema.gross_salary,
        income_from_house_property=schema.income_hp,
        income_from_business=schema.business_income,
        long_term_capital_gains=schema.capital_gains_lt,
        short_term_capital_gains=schema.capital_gains_st,
        income_from_other_sources=schema.other_income,
        deductions=engine_deductions,
    )


def _adapt_income_tax_response(result: engine_mod.IncomeTaxResponse) -> IncomeTaxResponse:
    """Convert engine IncomeTaxResponse to Pydantic schema."""

    def _regime(r: engine_mod.RegimeResult) -> RegimeBreakdown:
        return RegimeBreakdown(
            gross_total_income=r.gross_total_income,
            total_deductions=r.chapter_via_deductions + r.standard_deduction,
            taxable_income=r.total_income,
            tax_on_income=r.tax_on_normal_income + r.tax_on_stcg_equity + r.tax_on_ltcg,
            surcharge=r.surcharge,
            education_cess=r.cess,
            total_tax_liability=r.total_tax_liability,
        )

    return IncomeTaxResponse(
        old_regime=_regime(result.old_regime),
        new_regime=_regime(result.new_regime),
        recommended_regime=result.recommended_regime,
        savings_amount=result.tax_saving,
    )


def _adapt_tds_request(schema: TDSRequest) -> engine_mod.TDSRequest:
    """Convert Pydantic TDSRequest to engine dataclass."""
    section = _PAYMENT_TYPE_TO_SECTION.get(schema.payment_type.value, "194J(b)")
    return engine_mod.TDSRequest(
        section=section,
        payment_amount=schema.amount,
        has_pan=schema.pan_available,
        recipient_type=schema.recipient_type.value,
    )


def _adapt_tds_response(result: engine_mod.TDSResponse) -> TDSResponse:
    """Convert engine TDSResponse to Pydantic schema."""
    return TDSResponse(
        section=result.section,
        rate=result.applicable_rate * Decimal("100") if result.applicable_rate else _ZERO,
        tds_amount=result.tds_amount,
        surcharge_applicable=False,
        threshold=result.threshold or _ZERO,
        notes=result.notes,
    )


def _adapt_gst_request(schema: GSTRequest) -> engine_mod.GSTRequest:
    """Convert Pydantic GSTRequest to engine dataclass.

    The Pydantic schema accepts gst_rate as a percentage (e.g. 18 for 18%)
    while the engine expects a fraction (0.18).  Convert here.
    """
    engine_rate = schema.gst_rate / Decimal("100") if schema.gst_rate is not None else None
    return engine_mod.GSTRequest(
        taxable_value=schema.taxable_value,
        hsn_sac=schema.hsn_sac,
        gst_rate=engine_rate,
        place_of_supply_state=schema.place_of_supply,
        place_of_origin_state=schema.place_of_origin,
    )


def _adapt_gst_response(result: engine_mod.GSTResponse) -> GSTResponse:
    """Convert engine GSTResponse to Pydantic schema."""
    return GSTResponse(
        cgst=result.cgst,
        sgst=result.sgst,
        igst=result.igst,
        total_tax=result.total_gst,
        total_with_tax=result.invoice_total,
        supply_type_determined=(
            SupplyTypeDetermined.inter_state
            if result.is_inter_state
            else SupplyTypeDetermined.intra_state
        ),
    )


def _adapt_capital_gains_request(
    schema: CapitalGainsRequest,
) -> engine_mod.CapitalGainsRequest:
    """Convert Pydantic CapitalGainsRequest to engine dataclass."""
    engine_asset_str = _ASSET_TYPE_MAP.get(schema.asset_type.value, "other")
    engine_asset = engine_mod.AssetType(engine_asset_str)

    return engine_mod.CapitalGainsRequest(
        asset_type=engine_asset,
        purchase_date=schema.purchase_date,
        sale_date=schema.sale_date,
        purchase_cost=schema.purchase_price,
        sale_consideration=schema.sale_price,
        improvement_cost=schema.improvement_cost,
        expenses_on_transfer=schema.transfer_expenses,
    )


def _adapt_capital_gains_response(
    result: engine_mod.CapitalGainsResponse,
) -> CapitalGainsResponse:
    """Convert engine CapitalGainsResponse to Pydantic schema.

    The engine returns tax_rate as a fraction (e.g. 0.125 for 12.5%);
    the Pydantic schema expects a percentage (12.5).
    """
    rate_pct = (result.tax_rate * Decimal("100")) if result.tax_rate else _ZERO
    return CapitalGainsResponse(
        gain_type=GainType.ltcg if result.is_long_term else GainType.stcg,
        indexed_cost=result.indexed_cost,
        capital_gain=result.capital_gain,
        tax_rate=rate_pct,
        tax_amount=result.tax_amount,
        exemptions_available=result.available_exemptions,
        holding_period_days=result.holding_period_days,
    )


def _adapt_interest_request(schema: InterestRequest) -> engine_mod.InterestRequest:
    """Convert Pydantic InterestRequest to engine dataclass."""
    return engine_mod.InterestRequest(
        total_tax_liability=schema.tax_liability,
        tds_paid=schema.tax_paid,
        due_date_of_filing=schema.due_date,
        actual_date_of_filing=schema.payment_date,
        assessment_year=schema.assessment_year,
    )


def _adapt_interest_response(
    result: engine_mod.InterestResponse,
    section: InterestSection,
) -> InterestResponse:
    """Convert engine InterestResponse to Pydantic schema.

    The engine computes all three sections (234A/B/C) at once; we pick the
    relevant one based on the requested section.
    """
    section_map = {
        InterestSection.s234a: (result.interest_234a, result.working_234a),
        InterestSection.s234b: (result.interest_234b, result.working_234b),
        InterestSection.s234c: (result.interest_234c, result.working_234c),
    }
    amount, working = section_map.get(section, (result.total_interest, {}))
    rate = Decimal("1")  # 1% per month for all 234 sections

    return InterestResponse(
        interest_amount=amount,
        calculation_details=[],
        section=section,
        rate=rate,
    )


# --------------------------------------------------------------------------- #
#  Request wrappers (add client_id + assessment_year for audit trail)
# --------------------------------------------------------------------------- #


class ComputeIncomeTaxRequest(BaseModel):
    client_id: uuid.UUID
    data: IncomeTaxRequest


class ComputeTDSRequest(BaseModel):
    client_id: uuid.UUID
    data: TDSRequest


class ComputeGSTRequest(BaseModel):
    client_id: uuid.UUID
    data: GSTRequest


class ComputeCapitalGainsRequest(BaseModel):
    client_id: uuid.UUID
    data: CapitalGainsRequest


class ComputeInterestRequest(BaseModel):
    client_id: uuid.UUID
    data: InterestRequest


class ComputeHRARequest(BaseModel):
    client_id: uuid.UUID
    basic_salary: Decimal = Field(..., ge=0)
    da: Decimal = Field(Decimal("0"), ge=0)
    hra_received: Decimal = Field(..., ge=0)
    rent_paid: Decimal = Field(..., ge=0)
    is_metro: bool = False


class ComputeDepreciationRequest(BaseModel):
    client_id: uuid.UUID
    asset_cost: Decimal = Field(..., gt=0)
    asset_type: str
    wdv_rate: Optional[Decimal] = None
    years: int = Field(5, ge=1, le=40)
    additional_dep_eligible: bool = False
    purchased_in_second_half: bool = False


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #


async def _validate_client(db: AsyncSession, client_id: uuid.UUID) -> Client:
    """Ensure the client exists and return it."""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    return client


async def _save_computation(
    db: AsyncSession,
    *,
    client_id: uuid.UUID,
    assessment_year: str,
    regime: str,
    gross_income: Decimal | None,
    tax_liability: Decimal | None,
    computation_json: dict,
    computed_by: uuid.UUID,
) -> TaxComputation:
    """Persist a tax computation to the database for audit trail."""
    record = TaxComputation(
        client_id=client_id,
        assessment_year=assessment_year,
        regime=TaxRegime(regime) if regime in ("old", "new") else TaxRegime.new,
        gross_income=gross_income,
        tax_liability=tax_liability,
        computation_json=computation_json,
        computed_by=computed_by,
    )
    db.add(record)
    await db.flush()
    return record


# --------------------------------------------------------------------------- #
#  POST /tax — Income tax computation
# --------------------------------------------------------------------------- #


@router.post(
    "/tax",
    response_model=IncomeTaxResponse,
    summary="Compute income tax (old vs new regime)",
)
async def compute_tax_endpoint(
    body: ComputeIncomeTaxRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IncomeTaxResponse:
    """Compute income tax liability under both old and new regimes,
    recommending the optimal choice.
    """
    await _validate_client(db, body.client_id)

    engine_req = _adapt_income_tax_request(body.data)
    engine_result = compute_income_tax(engine_req)
    result = _adapt_income_tax_response(engine_result)

    # Save to DB
    record = await _save_computation(
        db,
        client_id=body.client_id,
        assessment_year=body.data.assessment_year,
        regime=engine_result.recommended_regime.replace("_regime", ""),
        gross_income=engine_result.old_regime.gross_total_income,
        tax_liability=min(
            engine_result.old_regime.total_tax_liability,
            engine_result.new_regime.total_tax_liability,
        ),
        computation_json={
            "type": "income_tax",
            "old_regime": result.old_regime.model_dump(mode="json"),
            "new_regime": result.new_regime.model_dump(mode="json"),
            "recommended": result.recommended_regime,
            "savings": str(result.savings_amount),
        },
        computed_by=current_user.id,
    )

    await log_action(
        db,
        user_id=current_user.id,
        action="compute.income_tax",
        entity_type="computation",
        entity_id=record.id,
        details={
            "client_id": str(body.client_id),
            "assessment_year": body.data.assessment_year,
        },
        ip_address=get_client_ip(request),
    )

    return result


# --------------------------------------------------------------------------- #
#  POST /tds — TDS calculation
# --------------------------------------------------------------------------- #


@router.post(
    "/tds",
    response_model=TDSResponse,
    summary="Calculate TDS deduction",
)
async def compute_tds_endpoint(
    body: ComputeTDSRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TDSResponse:
    """Calculate TDS rate and amount for a given payment type and amount."""
    await _validate_client(db, body.client_id)

    engine_req = _adapt_tds_request(body.data)
    engine_result = compute_tds(engine_req)
    result = _adapt_tds_response(engine_result)

    record = await _save_computation(
        db,
        client_id=body.client_id,
        assessment_year="N/A",
        regime="new",
        gross_income=body.data.amount,
        tax_liability=result.tds_amount,
        computation_json={
            "type": "tds",
            "section": result.section,
            "rate": str(result.rate),
            "tds_amount": str(result.tds_amount),
            "payment_type": body.data.payment_type.value,
        },
        computed_by=current_user.id,
    )

    await log_action(
        db,
        user_id=current_user.id,
        action="compute.tds",
        entity_type="computation",
        entity_id=record.id,
        details={"client_id": str(body.client_id)},
        ip_address=get_client_ip(request),
    )

    return result


# --------------------------------------------------------------------------- #
#  POST /gst — GST computation
# --------------------------------------------------------------------------- #


@router.post(
    "/gst",
    response_model=GSTResponse,
    summary="Compute GST breakdown",
)
async def compute_gst_endpoint(
    body: ComputeGSTRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GSTResponse:
    """Compute CGST/SGST/IGST split based on supply type and place of supply."""
    await _validate_client(db, body.client_id)

    engine_req = _adapt_gst_request(body.data)
    engine_result = compute_gst(engine_req)
    result = _adapt_gst_response(engine_result)

    record = await _save_computation(
        db,
        client_id=body.client_id,
        assessment_year="N/A",
        regime="new",
        gross_income=body.data.taxable_value,
        tax_liability=result.total_tax,
        computation_json={
            "type": "gst",
            "cgst": str(result.cgst),
            "sgst": str(result.sgst),
            "igst": str(result.igst),
            "total_tax": str(result.total_tax),
            "supply_type": result.supply_type_determined.value,
        },
        computed_by=current_user.id,
    )

    await log_action(
        db,
        user_id=current_user.id,
        action="compute.gst",
        entity_type="computation",
        entity_id=record.id,
        details={"client_id": str(body.client_id)},
        ip_address=get_client_ip(request),
    )

    return result


# --------------------------------------------------------------------------- #
#  POST /capital-gains — Capital gains computation
# --------------------------------------------------------------------------- #


@router.post(
    "/capital-gains",
    response_model=CapitalGainsResponse,
    summary="Compute capital gains tax",
)
async def compute_capital_gains_endpoint(
    body: ComputeCapitalGainsRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CapitalGainsResponse:
    """Compute LTCG or STCG based on asset type, holding period, and cost indexation."""
    await _validate_client(db, body.client_id)

    engine_req = _adapt_capital_gains_request(body.data)
    engine_result = compute_capital_gains(engine_req)
    result = _adapt_capital_gains_response(engine_result)

    record = await _save_computation(
        db,
        client_id=body.client_id,
        assessment_year="N/A",
        regime="new",
        gross_income=result.capital_gain,
        tax_liability=result.tax_amount,
        computation_json={
            "type": "capital_gains",
            "gain_type": result.gain_type.value,
            "capital_gain": str(result.capital_gain),
            "tax_rate": str(result.tax_rate),
            "tax_amount": str(result.tax_amount),
            "holding_period_days": result.holding_period_days,
            "exemptions": result.exemptions_available,
        },
        computed_by=current_user.id,
    )

    await log_action(
        db,
        user_id=current_user.id,
        action="compute.capital_gains",
        entity_type="computation",
        entity_id=record.id,
        details={"client_id": str(body.client_id)},
        ip_address=get_client_ip(request),
    )

    return result


# --------------------------------------------------------------------------- #
#  POST /interest — Interest u/s 234A/B/C
# --------------------------------------------------------------------------- #


@router.post(
    "/interest",
    response_model=InterestResponse,
    summary="Compute interest under sections 234A/B/C",
)
async def compute_interest_endpoint(
    body: ComputeInterestRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InterestResponse:
    """Calculate penal interest for late filing (234A), shortfall in advance tax
    (234B), or deferred advance tax installments (234C).
    """
    await _validate_client(db, body.client_id)

    engine_req = _adapt_interest_request(body.data)
    engine_result = compute_interest_234(engine_req)
    result = _adapt_interest_response(engine_result, body.data.section)

    record = await _save_computation(
        db,
        client_id=body.client_id,
        assessment_year=body.data.assessment_year,
        regime="new",
        gross_income=body.data.tax_liability,
        tax_liability=result.interest_amount,
        computation_json={
            "type": "interest_234",
            "section": result.section.value,
            "interest_amount": str(result.interest_amount),
            "rate": str(result.rate),
        },
        computed_by=current_user.id,
    )

    await log_action(
        db,
        user_id=current_user.id,
        action="compute.interest_234",
        entity_type="computation",
        entity_id=record.id,
        details={
            "client_id": str(body.client_id),
            "section": body.data.section.value,
        },
        ip_address=get_client_ip(request),
    )

    return result


# --------------------------------------------------------------------------- #
#  POST /hra — HRA exemption
# --------------------------------------------------------------------------- #


@router.post(
    "/hra",
    summary="Compute HRA exemption under section 10(13A)",
)
async def compute_hra_endpoint(
    body: ComputeHRARequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Calculate HRA exemption under section 10(13A) based on actual rent paid,
    basic salary, and metro/non-metro status.
    """
    await _validate_client(db, body.client_id)

    result = compute_hra_exemption(
        basic_salary=body.basic_salary,
        da=body.da,
        hra_received=body.hra_received,
        rent_paid=body.rent_paid,
        is_metro=body.is_metro,
    )

    record = await _save_computation(
        db,
        client_id=body.client_id,
        assessment_year="N/A",
        regime="old",
        gross_income=body.hra_received,
        tax_liability=None,
        computation_json={
            "type": "hra_exemption",
            **{k: str(v) if isinstance(v, Decimal) else v for k, v in result.items()},
        },
        computed_by=current_user.id,
    )

    await log_action(
        db,
        user_id=current_user.id,
        action="compute.hra",
        entity_type="computation",
        entity_id=record.id,
        details={"client_id": str(body.client_id)},
        ip_address=get_client_ip(request),
    )

    # Convert Decimal values to strings for JSON serialization
    serializable = {}
    for k, v in result.items():
        if isinstance(v, Decimal):
            serializable[k] = str(v)
        elif isinstance(v, dict):
            serializable[k] = {
                dk: str(dv) if isinstance(dv, Decimal) else dv
                for dk, dv in v.items()
            }
        else:
            serializable[k] = v

    return serializable


# --------------------------------------------------------------------------- #
#  POST /depreciation — Depreciation schedule
# --------------------------------------------------------------------------- #


@router.post(
    "/depreciation",
    summary="Compute depreciation schedule (WDV method)",
)
async def compute_depreciation_endpoint(
    body: ComputeDepreciationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Compute a year-by-year depreciation schedule using the Written Down Value method.

    Supports additional depreciation and half-year rule.
    """
    await _validate_client(db, body.client_id)

    try:
        result = compute_depreciation(
            asset_cost=body.asset_cost,
            asset_type=body.asset_type,
            wdv_rate=body.wdv_rate,
            years=body.years,
            additional_dep_eligible=body.additional_dep_eligible,
            purchased_in_second_half=body.purchased_in_second_half,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    record = await _save_computation(
        db,
        client_id=body.client_id,
        assessment_year="N/A",
        regime="new",
        gross_income=body.asset_cost,
        tax_liability=None,
        computation_json={
            "type": "depreciation",
            "asset_type": body.asset_type,
            "asset_cost": str(body.asset_cost),
            "years": body.years,
            "schedule": result,
        },
        computed_by=current_user.id,
    )

    await log_action(
        db,
        user_id=current_user.id,
        action="compute.depreciation",
        entity_type="computation",
        entity_id=record.id,
        details={
            "client_id": str(body.client_id),
            "asset_type": body.asset_type,
        },
        ip_address=get_client_ip(request),
    )

    return result
