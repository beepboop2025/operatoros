"""Shared fixtures for backend tests."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.tax_engine import (
    AgeCategory,
    AssetType,
    CapitalGainsRequest,
    Deductions,
    GSTRequest,
    IncomeTaxRequest,
    InterestRequest,
    TDSRequest,
)


def D(value: str | int | float) -> Decimal:
    """Decimal constructor helper."""
    return Decimal(str(value))


@pytest.fixture
def deductions_factory():
    """Return a callable that builds Deductions dataclasses."""

    def _make(**kwargs):
        defaults = {
            "sec_80c": D(0),
            "sec_80ccc": D(0),
            "sec_80ccd_1": D(0),
            "sec_80ccd_1b": D(0),
            "sec_80ccd_2": D(0),
            "sec_80d_self": D(0),
            "sec_80d_parents": D(0),
            "sec_80dd": D(0),
            "sec_80e": D(0),
            "sec_80eea": D(0),
            "sec_80g": D(0),
            "sec_80gg": D(0),
            "sec_80tta": D(0),
            "sec_80ttb": D(0),
            "sec_80u": D(0),
            "sec_24b": D(0),
            "other_deductions": D(0),
        }
        defaults.update(kwargs)
        return Deductions(**defaults)

    return _make


@pytest.fixture
def income_request_factory(deductions_factory):
    """Return a callable that builds IncomeTaxRequest dataclasses."""

    def _make(
        assessment_year: str = "2025-26",
        age_category: AgeCategory = AgeCategory.below_60,
        gross_salary: Decimal = D(0),
        income_from_house_property: Decimal = D(0),
        income_from_business: Decimal = D(0),
        short_term_capital_gains: Decimal = D(0),
        short_term_capital_gains_equity: Decimal = D(0),
        long_term_capital_gains: Decimal = D(0),
        income_from_other_sources: Decimal = D(0),
        agricultural_income: Decimal = D(0),
        deductions: Deductions | None = None,
        tds_already_paid: Decimal = D(0),
        advance_tax_paid: Decimal = D(0),
        self_assessment_tax_paid: Decimal = D(0),
    ) -> IncomeTaxRequest:
        return IncomeTaxRequest(
            assessment_year=assessment_year,
            age_category=age_category,
            gross_salary=D(gross_salary),
            income_from_house_property=D(income_from_house_property),
            income_from_business=D(income_from_business),
            short_term_capital_gains=D(short_term_capital_gains),
            short_term_capital_gains_equity=D(short_term_capital_gains_equity),
            long_term_capital_gains=D(long_term_capital_gains),
            income_from_other_sources=D(income_from_other_sources),
            agricultural_income=D(agricultural_income),
            deductions=deductions if deductions is not None else deductions_factory(),
            tds_already_paid=D(tds_already_paid),
            advance_tax_paid=D(advance_tax_paid),
            self_assessment_tax_paid=D(self_assessment_tax_paid),
        )

    return _make


@pytest.fixture
def tds_request_factory():
    """Return a callable that builds TDSRequest dataclasses."""

    def _make(
        section: str,
        payment_amount: Decimal,
        has_pan: bool = True,
        recipient_type: str = "individual",
        is_senior_citizen: bool = False,
    ) -> TDSRequest:
        return TDSRequest(
            section=section,
            payment_amount=D(payment_amount),
            has_pan=has_pan,
            recipient_type=recipient_type,
            is_senior_citizen=is_senior_citizen,
        )

    return _make


@pytest.fixture
def gst_request_factory():
    """Return a callable that builds GSTRequest dataclasses."""

    def _make(
        taxable_value: Decimal,
        hsn_sac: str | None = None,
        gst_rate: Decimal | None = None,
        place_of_supply_state: str = "",
        place_of_origin_state: str = "",
        description: str | None = None,
    ) -> GSTRequest:
        return GSTRequest(
            taxable_value=D(taxable_value),
            hsn_sac=hsn_sac,
            gst_rate=D(gst_rate) if gst_rate is not None else None,
            place_of_supply_state=place_of_supply_state,
            place_of_origin_state=place_of_origin_state,
            description=description,
        )

    return _make


@pytest.fixture
def capital_gains_request_factory():
    """Return a callable that builds CapitalGainsRequest dataclasses."""

    def _make(
        asset_type: AssetType,
        purchase_date: date,
        sale_date: date,
        purchase_cost: Decimal,
        sale_consideration: Decimal,
        improvement_cost: Decimal = D(0),
        purchase_fy: str | None = None,
        sale_fy: str | None = None,
        expenses_on_transfer: Decimal = D(0),
    ) -> CapitalGainsRequest:
        return CapitalGainsRequest(
            asset_type=asset_type,
            purchase_date=purchase_date,
            sale_date=sale_date,
            purchase_cost=D(purchase_cost),
            sale_consideration=D(sale_consideration),
            improvement_cost=D(improvement_cost),
            purchase_fy=purchase_fy,
            sale_fy=sale_fy,
            expenses_on_transfer=D(expenses_on_transfer),
        )

    return _make


@pytest.fixture
def interest_request_factory():
    """Return a callable that builds InterestRequest dataclasses."""

    def _make(
        total_tax_liability: Decimal,
        tds_paid: Decimal = D(0),
        advance_tax_paid: Decimal = D(0),
        advance_tax_dates: list[dict] | None = None,
        due_date_of_filing: date = date(2026, 7, 31),
        actual_date_of_filing: date | None = None,
        assessment_year: str = "2026-27",
    ) -> InterestRequest:
        return InterestRequest(
            total_tax_liability=D(total_tax_liability),
            tds_paid=D(tds_paid),
            advance_tax_paid=D(advance_tax_paid),
            advance_tax_dates=advance_tax_dates or [],
            due_date_of_filing=due_date_of_filing,
            actual_date_of_filing=actual_date_of_filing,
            assessment_year=assessment_year,
        )

    return _make
