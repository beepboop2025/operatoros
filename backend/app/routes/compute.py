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
    GSTRequest,
    GSTResponse,
    IncomeTaxRequest,
    IncomeTaxResponse,
    InterestRequest,
    InterestResponse,
    TDSRequest,
    TDSResponse,
)
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

    result = compute_income_tax(body.data)

    # Save to DB
    record = await _save_computation(
        db,
        client_id=body.client_id,
        assessment_year=body.data.assessment_year,
        regime=result.recommended_regime.replace("_regime", ""),
        gross_income=result.old_regime.gross_total_income,
        tax_liability=min(
            result.old_regime.total_tax_liability,
            result.new_regime.total_tax_liability,
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

    result = compute_tds(body.data)

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

    result = compute_gst(body.data)

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

    result = compute_capital_gains(body.data)

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

    result = compute_interest_234(body.data)

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
