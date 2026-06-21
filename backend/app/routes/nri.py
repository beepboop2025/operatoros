"""
NRI cross-border taxation routes — Phase 7 backend.

All routes are protected by the standard JWT dependency and emit audit logs.
They are thin adapters over the pure ``app.services.nri_engine`` dataclasses.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.middleware.audit import get_client_ip, log_action
from app.models.user import User
from app.schemas import nri as schemas
from app.services import nri_engine as engine_mod

router = APIRouter(prefix="/nri", tags=["nri"])

_ZERO = Decimal("0")


# --------------------------------------------------------------------------- #
#  Adapters: engine dataclass <-> Pydantic schema
# --------------------------------------------------------------------------- #


def _adapt_residential_status_request(
    schema: schemas.ResidentialStatusRequest,
) -> engine_mod.ResidentialStatusRequest:
    return engine_mod.ResidentialStatusRequest(
        assessment_year=schema.assessment_year,
        days_in_india_current_fy=schema.days_in_india_current_fy,
        days_in_india_prior_4_fys=list(schema.days_in_india_prior_4_fys),
        days_in_india_prior_7_fys=list(schema.days_in_india_prior_7_fys)
        if schema.days_in_india_prior_7_fys
        else None,
        prior_10_fys_resident=list(schema.prior_10_fys_resident)
        if schema.prior_10_fys_resident
        else None,
        is_indian_citizen=schema.is_indian_citizen,
        is_person_of_indian_origin=schema.is_person_of_indian_origin,
        leaving_for_employment=schema.leaving_for_employment,
        is_crew_of_indian_ship=schema.is_crew_of_indian_ship,
        indian_source_income=schema.indian_source_income,
        tax_resident_elsewhere=schema.tax_resident_elsewhere,
    )


def _adapt_residential_status_response(
    result: engine_mod.ResidentialStatusResponse,
) -> schemas.ResidentialStatusResponse:
    return schemas.ResidentialStatusResponse(
        status=schemas.ResidentialStatus(result.status.value),
        taxable_scope=schemas.TaxScope(result.taxable_scope.value),
        controlling_rule=result.controlling_rule,
        rnor_test_result=result.rnor_test_result,
        is_deemed_resident=result.is_deemed_resident,
        days_in_india_current_fy=result.days_in_india_current_fy,
        days_in_india_prior_4_fys=result.days_in_india_prior_4_fys,
        threshold_days=result.threshold_days,
        working=result.working,
    )


def _adapt_dtaa_request(schema: schemas.DTAARequest) -> engine_mod.DTAARequest:
    return engine_mod.DTAARequest(
        country=schema.country,
        income_type=schema.income_type.value if schema.income_type else None,
    )


def _adapt_dtaa_response(result: engine_mod.DTAAResponse) -> schemas.DTAAResponse:
    rates = [
        schemas.DTAARateEntry(
            income_type=r["income_type"],
            rate=r["rate"],
            rate_percent=r["rate_percent"],
            notes=r["notes"],
        )
        for r in result.rates
    ]
    return schemas.DTAAResponse(
        country=result.country,
        country_code=result.country_code,
        rates=rates,
        residency_tie_breaker=result.residency_tie_breaker,
        trc_required=result.trc_required,
        form_10f_required=result.form_10f_required,
        documentation=result.documentation,
        source_citation=result.source_citation,
        ca_review_required=result.ca_review_required,
        notes=result.notes,
    )


def _adapt_section195_request(
    schema: schemas.Section195Request,
) -> engine_mod.Section195Request:
    return engine_mod.Section195Request(
        payment_type=engine_mod.Section195PaymentType(schema.payment_type.value),
        payment_amount=schema.payment_amount,
        payee_is_nri=schema.payee_is_nri,
        payee_country=schema.payee_country,
        payee_has_trc=schema.payee_has_trc,
        payee_has_pan=schema.payee_has_pan,
        property_sale_consideration=schema.property_sale_consideration,
        property_is_long_term=schema.property_is_long_term,
        has_form_15e_certificate=schema.has_form_15e_certificate,
        certificate_rate=schema.certificate_rate,
        domestic_rate_override=schema.domestic_rate_override,
        treaty_rate_override=schema.treaty_rate_override,
    )


def _adapt_section195_response(
    result: engine_mod.Section195Response,
) -> schemas.Section195Response:
    return schemas.Section195Response(
        section=result.section,
        payment_type=result.payment_type,
        applicable_rate=result.applicable_rate,
        tds_amount=result.tds_amount,
        applicable_regime=result.applicable_regime,
        form_15ca_required=result.form_15ca_required,
        form_15cb_required=result.form_15cb_required,
        form_15e_applied=result.form_15e_applied,
        certificate_rate=result.certificate_rate,
        repatriation_note=result.repatriation_note,
        notes=result.notes,
        working=result.working,
    )


def _adapt_ftc_country_input(
    item: schemas.FTCCreditCountryInput,
) -> engine_mod.FTCCreditCountryInput:
    return engine_mod.FTCCreditCountryInput(
        country=item.country,
        foreign_income=item.foreign_income,
        foreign_tax_paid=item.foreign_tax_paid,
        has_dtaa=item.has_dtaa,
    )


def _adapt_ftc_request(schema: schemas.FTCRequest) -> engine_mod.FTCRequest:
    return engine_mod.FTCRequest(
        assessment_year=schema.assessment_year,
        total_income=schema.total_income,
        total_indian_tax=schema.total_indian_tax,
        countries=[_adapt_ftc_country_input(c) for c in schema.countries],
        filing_date=schema.filing_date,
    )


def _adapt_ftc_country_result(
    item: engine_mod.FTCCreditCountryResult,
) -> schemas.FTCCreditCountryResult:
    return schemas.FTCCreditCountryResult(
        country=item.country,
        foreign_income=item.foreign_income,
        foreign_tax_paid=item.foreign_tax_paid,
        indian_tax_on_foreign_income=item.indian_tax_on_foreign_income,
        allowable_credit=item.allowable_credit,
        disallowance=item.disallowance,
        method=item.method,
    )


def _adapt_ftc_response(result: engine_mod.FTCResponse) -> schemas.FTCResponse:
    return schemas.FTCResponse(
        assessment_year=result.assessment_year,
        total_foreign_income=result.total_foreign_income,
        total_foreign_tax_paid=result.total_foreign_tax_paid,
        total_allowable_credit=result.total_allowable_credit,
        total_disallowance=result.total_disallowance,
        average_indian_tax_rate=result.average_indian_tax_rate,
        form_67_due_date=result.form_67_due_date,
        is_filed_on_time=result.is_filed_on_time,
        per_country=[_adapt_ftc_country_result(c) for c in result.per_country],
        notes=result.notes,
        working=result.working,
    )


def _adapt_customs_request(
    schema: schemas.CustomsTariffRequest,
) -> engine_mod.CustomsTariffRequest:
    return engine_mod.CustomsTariffRequest(
        hsn_code=schema.hsn_code,
        cif_value=schema.cif_value,
        country_of_origin=schema.country_of_origin,
        fta_code=schema.fta_code,
        bcd_rate_override=schema.bcd_rate_override,
        sws_rate_override=schema.sws_rate_override,
        cess_rate_override=schema.cess_rate_override,
        igst_rate_override=schema.igst_rate_override,
    )


def _adapt_customs_response(
    result: engine_mod.CustomsTariffResponse,
) -> schemas.CustomsTariffResponse:
    return schemas.CustomsTariffResponse(
        hsn_code=result.hsn_code,
        cif_value=result.cif_value,
        bcd_rate=result.bcd_rate,
        bcd_amount=result.bcd_amount,
        sws_rate=result.sws_rate,
        sws_amount=result.sws_amount,
        cess_rate=result.cess_rate,
        cess_amount=result.cess_amount,
        igst_rate=result.igst_rate,
        igst_amount=result.igst_amount,
        import_duty_total=result.import_duty_total,
        total_landed_cost=result.total_landed_cost,
        fta_applied=result.fta_applied,
        missing_rates=result.missing_rates,
        notes=result.notes,
        working=result.working,
    )


def _adapt_cross_border_gst_request(
    schema: schemas.CrossBorderGSTRequest,
) -> engine_mod.CrossBorderGSTRequest:
    return engine_mod.CrossBorderGSTRequest(
        taxable_value=schema.taxable_value,
        transaction_type=engine_mod.CrossBorderTransactionType(schema.transaction_type.value),
        supply_type=schema.supply_type,
        hsn_sac=schema.hsn_sac,
        gst_rate=schema.gst_rate,
        has_lut=schema.has_lut,
        is_b2b=schema.is_b2b,
        recipient_country=schema.recipient_country,
        place_of_supply=schema.place_of_supply,
        import_duty_amount=schema.import_duty_amount,
    )


def _adapt_cross_border_gst_response(
    result: engine_mod.CrossBorderGSTResponse,
) -> schemas.CrossBorderGSTResponse:
    return schemas.CrossBorderGSTResponse(
        transaction_type=result.transaction_type,
        supply_type=result.supply_type,
        taxable_value=result.taxable_value,
        igst=result.igst,
        cgst=result.cgst,
        sgst=result.sgst,
        total_gst=result.total_gst,
        invoice_total=result.invoice_total,
        export_zero_rated=result.export_zero_rated,
        reverse_charge=result.reverse_charge,
        place_of_supply=result.place_of_supply,
        notes=result.notes,
        working=result.working,
    )


# --------------------------------------------------------------------------- #
#  Routes
# --------------------------------------------------------------------------- #


@router.post(
    "/residential-status",
    response_model=schemas.ResidentialStatusResponse,
    summary="Determine NRI residential status",
)
async def residential_status(
    body: schemas.ResidentialStatusRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.ResidentialStatusResponse:
    """Determine Resident / RNOR / NRI / Deemed Resident for a given FY."""
    engine_req = _adapt_residential_status_request(body)
    result = engine_mod.determine_residential_status(engine_req)
    await log_action(
        db,
        user_id=current_user.id,
        action="nri.residential_status",
        entity_type="computation",
        details={"assessment_year": body.assessment_year, "status": result.status.value},
        ip_address=get_client_ip(request),
    )
    return _adapt_residential_status_response(result)


@router.post(
    "/dtaa",
    response_model=schemas.DTAAResponse,
    summary="Explore DTAA treaty rates and documentation",
)
async def dtaa_explore(
    body: schemas.DTAARequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.DTAAResponse:
    """Return DTAA article rates, tie-breaker, and TRC/Form 10F requirements."""
    engine_req = _adapt_dtaa_request(body)
    result = engine_mod.explore_dtaa(engine_req)
    await log_action(
        db,
        user_id=current_user.id,
        action="nri.dtaa_explore",
        entity_type="computation",
        details={"country": body.country},
        ip_address=get_client_ip(request),
    )
    return _adapt_dtaa_response(result)


@router.post(
    "/section195",
    response_model=schemas.Section195Response,
    summary="Section 195 TDS and Form 15CA/15CB workflow",
)
async def section_195(
    body: schemas.Section195Request,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.Section195Response:
    """Compute TDS on payments to NRIs and the 15CA/15CB/15E workflow."""
    engine_req = _adapt_section195_request(body)
    result = engine_mod.compute_section_195(engine_req)
    await log_action(
        db,
        user_id=current_user.id,
        action="nri.section195",
        entity_type="computation",
        details={"payment_type": body.payment_type.value, "regime": result.applicable_regime},
        ip_address=get_client_ip(request),
    )
    return _adapt_section195_response(result)


@router.post(
    "/ftc",
    response_model=schemas.FTCResponse,
    summary="Foreign Tax Credit calculator (Rule 128 / Form 67)",
)
async def foreign_tax_credit(
    body: schemas.FTCRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.FTCResponse:
    """Compute allowable FTC per country using the average-rate method."""
    engine_req = _adapt_ftc_request(body)
    result = engine_mod.compute_ftc(engine_req)
    await log_action(
        db,
        user_id=current_user.id,
        action="nri.ftc",
        entity_type="computation",
        details={"assessment_year": body.assessment_year},
        ip_address=get_client_ip(request),
    )
    return _adapt_ftc_response(result)


@router.post(
    "/customs-tariff",
    response_model=schemas.CustomsTariffResponse,
    summary="Customs import duty calculator",
)
async def customs_tariff(
    body: schemas.CustomsTariffRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.CustomsTariffResponse:
    """Compute BCD + SWS + cess + IGST on an import."""
    engine_req = _adapt_customs_request(body)
    result = engine_mod.compute_customs_tariff(engine_req)
    await log_action(
        db,
        user_id=current_user.id,
        action="nri.customs_tariff",
        entity_type="computation",
        details={"hsn_code": body.hsn_code},
        ip_address=get_client_ip(request),
    )
    return _adapt_customs_response(result)


@router.post(
    "/gst-cross-border",
    response_model=schemas.CrossBorderGSTResponse,
    summary="GST cross-border computation",
)
async def gst_cross_border(
    body: schemas.CrossBorderGSTRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.CrossBorderGSTResponse:
    """Compute import IGST, export LUT zero-rating, or OIDAR GST."""
    engine_req = _adapt_cross_border_gst_request(body)
    result = engine_mod.compute_cross_border_gst(engine_req)
    await log_action(
        db,
        user_id=current_user.id,
        action="nri.gst_cross_border",
        entity_type="computation",
        details={"transaction_type": body.transaction_type.value},
        ip_address=get_client_ip(request),
    )
    return _adapt_cross_border_gst_response(result)
